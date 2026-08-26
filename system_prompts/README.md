# system_prompts/

> **For non-Chinese-speaking readers**: this folder's content is primarily in Chinese, consistent with the JTG/T H21-2011 standard it implements. See the root [`README.md`](../README.md) for an English overview, cross-references to the paper's section numbers, and a Quick Start guide.

本目录是 BIDS-MC 论文方法论对应的核心材料，完整说明（四层框架对应表、许可与引用信息）见仓库根目录 [`README.md`](../README.md)。这里只补充"脱离本应用、单独使用这些文件"时需要知道的信息。

## 文件说明

| 文件 | 内容 |
|---|---|
| `reasoning_pipeline_prompt.md` | 推理链：S0–S7 逻辑步骤 + 附录A核心定义速查表 + 附录B报告输出模板。`[MUST]` / `[HARD STOP]` / `[IF]` / `[WARN]` 等标记表示不同强制级别的约束条件。 |
| `knowledge_base_JTG_T_H21.md` | 知识库：规范条文、评定标度表、DP扣分表、权重表、典型病害图解案例。 |
| `case_jiangdongao_bridge.md` | 脱敏后的示例检测数据（已去除路线名/桩号/检测单位），格式对应"输入格式"一节，也是本应用内置"加载示例"按钮所用的同一份数据。 |

针对这份示例输入的实际运行结果（推理文本、结构化 JSON、界面截图）见仓库根目录的 [`example_output/`](../example_output)。

## 如果想脱离本应用、单独调用大模型 API

本应用（`prompts.py`）在启动时会自动读取拼接这两个文件；如果你想脱离这套 FastAPI 应用，直接用别的方式（比如自己写脚本调用 Claude / GPT / DeepSeek API）测试提示词本身，可以手动按以下顺序拼接：

1. `reasoning_pipeline_prompt.md` 开头的"任务说明"部分
2. `knowledge_base_JTG_T_H21.md` 全文（规范正文）
3. `reasoning_pipeline_prompt.md` 剩余的 S0–S7 推理链部分

拼接结果作为 system prompt 传入模型 API，再把《全桥构件台账》格式的桥梁检测数据（参考 `case_jiangdongao_bridge.md`）作为 user 输入即可，无需运行本应用的前后端。
