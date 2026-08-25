"""
桥梁检测分析 API  v0.9.0
新增：LLM意图分类 + 动态重排序/置信度/检索内容展示
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import asyncio
import time
import threading
from pathlib import Path
from openai import OpenAI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from prompts import (
    build_system_prompt,
    build_user_section,
    build_extract_prompt,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 配置
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEEPSEEK_API_KEY  = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL    = "deepseek-v4-flash"
EXTRACT_MODEL     = "deepseek-v4-flash"
MAX_TOKENS        = 393216
EXTRACT_MAX_TOKENS = 393216

app = FastAPI(title="桥梁检测分析API", version="0.9.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 心跳看门狗：网页关闭后自动退出进程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 前端每隔几秒 POST /heartbeat 一次；若超过 HEARTBEAT_TIMEOUT 秒未收到心跳，
# 视为网页已被关闭，watchdog 线程直接结束进程（无需用户手动杀 exe）。
# HEARTBEAT_GRACE 是启动后的宽限期：给浏览器打开页面、加载脚本留出时间，
# 避免服务刚启动、浏览器还没打开时就被误杀。
HEARTBEAT_TIMEOUT = 30
HEARTBEAT_GRACE = 30

_last_heartbeat = time.time()
_heartbeat_lock = threading.Lock()

# 正在进行的推理请求计数：推理期间看门狗不检查心跳，
# 避免长推理（可达数分钟）时页面在后台、心跳被浏览器节流而误杀服务。
_active_requests = 0
_active_lock = threading.Lock()


def _req_inc():
    global _active_requests
    with _active_lock:
        _active_requests += 1


def _req_dec():
    global _active_requests
    with _active_lock:
        _active_requests = max(0, _active_requests - 1)


def _has_active_request():
    with _active_lock:
        return _active_requests > 0


@app.post("/heartbeat")
async def heartbeat():
    global _last_heartbeat
    with _heartbeat_lock:
        _last_heartbeat = time.time()
    return {"ok": True}


def _watchdog():
    start = time.time()
    while True:
        time.sleep(2)
        with _heartbeat_lock:
            last = _last_heartbeat
        if time.time() - start < HEARTBEAT_GRACE:
            continue
        if _has_active_request():
            # 推理进行中：页面即使切到后台、心跳被节流，也不退出
            continue
        if time.time() - last > HEARTBEAT_TIMEOUT:
            print("[watchdog] No heartbeat detected; page appears closed, exiting.")
            os._exit(0)


threading.Thread(target=_watchdog, daemon=True).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 首页
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = Path(__file__).parent / "index.html"
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 输入数据结构
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class BridgeInput(BaseModel):
    bridge_id:         str
    bridge_name:       str
    report_no:         str
    inspect_date:      str
    bridge_params:     Optional[dict] = None
    last_inspect:      Optional[dict] = None
    defects:           dict = {}
    debug:             bool = False
    reasoning_model:   str = "deepseek-v4-flash"
    reasoning_thinking: str = "enabled"
    reasoning_effort:  str = "high"
    api_key:           Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工具函数
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"




# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 核心流式生成器（用于 /analyze）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _stream_generator(system_prompt: str, user_content: str, data: dict):
    api_key = data.get("api_key") or DEEPSEEK_API_KEY
    if not api_key:
        yield _sse({"type": "error", "message": "DeepSeek API Key not configured: please enter it on the page, or set the DEEPSEEK_API_KEY environment variable"})
        return
    _client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)

    yield _sse({"type": "status", "text": "Model reasoning in progress, please wait..."})
    import time
    for attempt in range(1, 3):
        full_think = ""
        full_output = ""
        try:
            if attempt > 1:
                yield _sse({"type": "status", "text": f"Retrying reasoning (attempt {attempt})..."})
                time.sleep(3)

            model_name = data.get("reasoning_model", DEEPSEEK_MODEL)
            kwargs = {}
            if model_name.startswith("deepseek-v4"):
                thinking_mode = data.get("reasoning_thinking", "enabled")
                kwargs["extra_body"] = {"thinking": {"type": thinking_mode}}
                if thinking_mode == "enabled":
                    kwargs["reasoning_effort"] = data.get("reasoning_effort", "high")
            stream = _client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                max_tokens=MAX_TOKENS,
                stream=True,
                **kwargs,
            )
            for chunk in stream:
                thinking = getattr(chunk.choices[0].delta, "reasoning_content", None)
                content = chunk.choices[0].delta.content
                if thinking:
                    full_think += thinking
                    if data.get("debug", False):
                        yield _sse({"type": "thinking", "text": thinking})
                if content:
                    full_output += content
                    if data.get("debug", False):
                        yield _sse({"type": "reasoning", "text": content})
            if not full_think and not full_output:
                print("[DEBUG] ⚠️ 正文为空")

            break
        except Exception as e:
            if attempt == 2:
                if full_think or full_output:
                    yield _sse({"type": "result", "reasoning": full_think + full_output})
                    yield _sse({"type": "done"})
                else:
                    yield _sse({"type": "error", "message": f"Reasoning failed: {str(e)}"})
                return

    yield _sse({"type": "result", "reasoning": full_think + full_output})
    yield _sse({"type": "done"})


async def _async_stream(system_prompt, user_content, data):
    _req_inc()
    try:
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        _DONE = object()
        def _run():
            try:
                for chunk in _stream_generator(system_prompt, user_content, data):
                    loop.call_soon_threadsafe(queue.put_nowait, chunk)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, _sse({"type": "error", "message": str(e)}))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _DONE)
        loop.run_in_executor(None, _run)
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=3.0)
            except asyncio.TimeoutError:
                yield _sse({"type": "ping"})
                continue
            if item is _DONE:
                break
            yield item
    finally:
        _req_dec()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 原有 API 端点
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/analyze")
async def analyze_bridge(data: BridgeInput):
    system_prompt = build_system_prompt()
    user_content  = build_user_section(data.model_dump())
    return StreamingResponse(
        _async_stream(system_prompt, user_content, data.model_dump()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ━━━━ 独立提取 ━━━━
class ExtractInput(BaseModel):
    reasoning_text: str
    reasoning_think: str = ""
    reasoning_output: str = ""
    bridge_data: dict
    api_key: Optional[str] = None


@app.post("/extract")
async def extract_json(data: ExtractInput):
    ext_system, ext_user = build_extract_prompt(data.reasoning_text, data.bridge_data)
    ext_content = ""

    async def _e():
        nonlocal ext_content
        _req_inc()
        try:
            api_key = data.api_key or DEEPSEEK_API_KEY
            if not api_key:
                yield _sse({"type": "error", "message": "DeepSeek API Key not configured: please enter it on the page, or set the DEEPSEEK_API_KEY environment variable"})
                return
            _client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
            for attempt in range(1, 3):
                try:
                    ext_content = ""
                    ext_stream = _client.chat.completions.create(
                        model=EXTRACT_MODEL,
                        messages=[
                            {"role": "system", "content": ext_system},
                            {"role": "user", "content": ext_user},
                        ],
                        max_tokens=EXTRACT_MAX_TOKENS,
                        stream=True,
                        reasoning_effort="low",
                        extra_body={"thinking": {"type": "enabled"}},
                    )
                    for chunk in ext_stream:
                        delta = chunk.choices[0].delta
                        ext_thinking = getattr(delta, "reasoning_content", None)
                        if ext_thinking:
                            yield _sse({"type": "thinking", "text": ext_thinking})
                        if delta.content:
                            ext_content += delta.content
                            yield _sse({"type": "extraction", "text": delta.content})

                    raw = ext_content.strip()
                    start = raw.find("{"); end = raw.rfind("}") + 1
                    if start != -1 and end > start:
                        raw = raw[start:end]
                    structured = json.loads(raw)

                    yield _sse({"type": "result", "data": structured})
                    yield _sse({"type": "done"})
                    return
                except json.JSONDecodeError:
                    if attempt == 2:
                        yield _sse({"type": "error", "message": "JSON parsing failed (2 retries exhausted)"})
                except Exception as e:
                    if attempt == 2:
                        yield _sse({"type": "error", "message": str(e)})
        finally:
            _req_dec()

    return StreamingResponse(_e(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/health")
async def health():
    return {"status": "ok", "model": DEEPSEEK_MODEL}