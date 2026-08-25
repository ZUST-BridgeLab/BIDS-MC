# BIDS-MC 提示词工程材料（Prompt Engineering Artifacts）

本仓库/目录公开 **BIDS-MC（Bridge Intelligent Diagnosis System with Mechanism Constraints）** 论文中所使用的完整系统提示词，供审稿人与同行复现实验结果、验证方法细节。

BIDS-MC 是一套基于大语言模型（LLM）的桥梁技术状况智能评定与病害诊断框架，遵循《公路桥梁技术状况评定标准》（JTG/T H21-2011）及配套规程，将资深桥梁检测专家的判断逻辑形式化为可执行的四层推理链：

| 层级 | 对应文件章节 | 作用 |
|---|---|---|
| 规范层 Specification | S0 – S1 | 数据清洗、构件台账建立、病害归属校验、依规范表格确定初步标度 |
| 机理层 Mechanism | S2.1 – S2.2 | 发展趋势判断、病害机理模式匹配（M1–M8）、结构安全风险定级 |
| 优化层 Optimization | S2.3 – S2.4 | 基于风险等级与发展趋势对标度进行有约束的校准（趋势修正） |
| 判断层 Judgment | S3 – S7 | 构件/部件/结构部位递归评分、全桥定级、关键病害影响分析与养护决策 |

## 文件结构

```
.
├── README.md                          本说明文件
├── knowledge_base_JTG_T_H21.md        知识库：规范条文、评定标度表、DP扣分表、权重表、典型病害图解案例
└── reasoning_pipeline_prompt.md       推理链：S0–S7 逻辑步骤 + 附录A核心定义速查表 + 附录B报告输出模板
```

两个文件在实际调用大模型时**拼接注入同一个 system prompt**：`knowledge_base_JTG_T_H21.md` 提供推理所依据的规范原文与病害判据数据，`reasoning_pipeline_prompt.md` 提供强制性的分步推理逻辑与格式约束（`[MUST]` / `[HARD STOP]` / `[IF]` / `[WARN]` 等标记表示不同强制级别的约束条件）。原始拼接顺序为：`reasoning_pipeline_prompt.md` 任务说明 → `knowledge_base_JTG_T_H21.md` 规范正文 → `reasoning_pipeline_prompt.md` 剩余推理链部分。为便于阅读，本仓库将二者拆分为独立文件维护，实际调用时可用脚本按上述顺序拼接。

## 使用方式

1. 将两个 Markdown 文件的正文按上文顺序拼接为完整 system prompt（去除本 README 中的说明性文字）。
2. 将拼接结果作为 system prompt 传入所使用的大模型 API（论文中验证过 Claude、GPT、DeepSeek 系列模型）。
3. 按照《全桥构件台账》所需字段格式，将桥梁基本信息与检测记录作为 user 输入。
4. 模型将严格按 S0→S7 顺序输出完整报告，最终报告章节顺序见 `reasoning_pipeline_prompt.md` 附录B。

## 版本与适用范围

- 提示词版本对应论文投稿版本，推理链结构（S0–S7）与论文 Section 2.4 Analysis Stage 的四层框架一一对应，具体映射见 `reasoning_pipeline_prompt.md` 各章节标题下的标注。
- 适用桥型：简支梁桥（含空心板、T梁等常见构造）。其他桥型（拱桥、悬索桥、斜拉桥）的部件划分与权重已收录于知识库，但典型病害图解手册部分目前仅覆盖简支梁桥上部结构，扩展至其他桥型是后续工作方向之一。
- 版本迭代记录随论文修改轮次同步更新，重大逻辑变更（如标度校准公式、风险判定规则的调整）将在提交历史中注明。

## 引用

使用本提示词材料开展研究时，请引用对应论文；引用格式将在论文正式发表后补充于此。

## 许可与版权说明

推理链逻辑（`reasoning_pipeline_prompt.md`）与知识库整理格式（`knowledge_base_JTG_T_H21.md` 的结构化排版）由作者原创，许可条款将随论文录用状态确定后一并公布。

知识库中摘录的规范条文（JTG/T H21-2011《公路桥梁技术状况评定标准》及配套的《公路桥梁承载能力检测评定规程》《公路桥梁典型病害诊断与处治图解手册》）版权归其发布/编制机构所有，本仓库仅摘录用于学术复现与同行评审目的，不代表对原规范内容的再授权。
