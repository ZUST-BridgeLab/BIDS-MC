# -*- coding: utf-8 -*-
"""
桥梁技术状况评定系统 —— 本地启动器
双击运行：启动本地 Web 服务并自动打开浏览器（功能与 v0.8 完全一致）。
"""
import os
import socket
import threading
import time
import webbrowser

PORT = int(os.environ.get("BRIDGE_PORT", "8010"))


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def _open_browser(url: str):
    time.sleep(2.0)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main():
    import sys
    import uvicorn
    import main  # noqa: F401  (后端，含 /analyze /extract 等)

    # 窗口模式(console=False)下 sys.stdout/stderr 为 None，uvicorn 的日志
    # 格式化器会调用 .isatty() 而崩溃，这里用无效流兜底。
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

    # 目标端口被占用时自动换空闲端口
    port = PORT
    for p in range(port, port + 20):
        if not _port_in_use(p):
            port = p
            break
    else:
        print(f"端口 {port}~{port+19} 均被占用，请先释放端口或设置 BRIDGE_PORT 后重试。")
        return

    url = f"http://127.0.0.1:{port}"
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    print(f"桥梁技术状况评定系统已启动：{url}")
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
