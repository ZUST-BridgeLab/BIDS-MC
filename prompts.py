"""
提示词构建模块
────────────────────────────────────────
system_prompts/    推理提示词来源（启动时读入并拼接）：
  - reasoning_pipeline_prompt.md   推理链逻辑
  - knowledge_base_JTG_T_H21.md    规范知识库
_EXTRACT_SYSTEM    第二次调用的提取提示词
"""

import json
from pathlib import Path

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 启动时读取提示词文件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_SYSTEM_PROMPTS_DIR = Path(__file__).parent / "system_prompts"
_PROMPT_FILES = ["reasoning_pipeline_prompt.md", "knowledge_base_JTG_T_H21.md"]

def _load() -> str:
    parts = []
    for name in _PROMPT_FILES:
        f = _SYSTEM_PROMPTS_DIR / name
        if not f.exists():
            raise FileNotFoundError(
                f"\n❌ 找不到提示词文件：{f}\n"
                "请将完整提示词拆分为 reasoning_pipeline_prompt.md 与 "
                "knowledge_base_JTG_T_H21.md，置于 system_prompts/ 目录。\n"
            )
        parts.append(f.read_text(encoding="utf-8").strip())
    text = "\n\n".join(parts)
    print(f"[OK] 提示词加载成功，共 {len(text)} 字符（{len(_PROMPT_FILES)} 个文件拼接）")
    return text

_SYSTEM_PROMPT = _load()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 第二次调用：提取系统提示词
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_EXTRACT_SYSTEM = """你是一个结构化数据提取助手。

任务：从两份输入中提取数据，生成桥梁检测报告所需的完整JSON：
1. 桥梁原始病害数据（含构件编号、病害位置、病害描述）
2. 推理分析报告（含标度评定、评分、原因分析、养护建议）

规则：
- span（跨径/墩台编号）、component（构件编号）、location（病害位置）、desc（病害描述）必须从原始数据表格中原样复制，不得翻译、改写、推断或修改任何一个字
- 标度、评分、等级、原因分析、养护建议从推理报告中提取
- chapter6 每个部件根据推理报告判断：
  a) 有病害 → 填入 rows 数组。defects 数组的每一项是一个病害组（对应推理报告步骤2表格中一个"非空标度行及其后续空标度行"），每组有 scale（共用标度）和 items（该组内各病害的 location/desc）
  b) 构件存在但未见明显病害 → 填 {"no_defect": true, "component_type": "构件类型"}
  c) 无此构件（权重重分配标注"无此构件"或该桥型不含）→ 填空对象 {}
- 输出时去掉 JSON 块内的所有注释
- 只输出JSON，不加markdown代码块，不加任何解释"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 完整JSON模板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_JSON_TEMPLATE = """{
  "bridge_name": "桥梁名称",
  "bridge_info": {
    "route": "路线编号及名称",
    "stake": "桩号",
    "structure_type": "结构类型（如：普通钢筋混凝土空心板简支梁桥）",
    "span": "跨径布置（如：5×14.0m）",
    "length": "桥梁全长",
    "width": "桥面宽度",
    "built_year": "建成时间",
    "design_load": "设计荷载"
  },
  "dimension_inference": [
    {
      "item": "推理项名称（如：单板底面可视面积 / 铺装磨光露骨面积占比）",
      "calc": "计算公式与结果（如：1.12m × 14.0m = 15.68m² / 350m² ÷ 360m² = 97.2%）",
      "note": "说明（如：推算值，待核实；面积占比>20% → S_init=4）"
    }
  ],

  "chapter6": {
    "上部承重构件": {},
    "上部一般构件": {},
    "支座": {},
    "翼墙、耳墙": {},
    "锥坡、护坡": {},
    "桥墩": {
      "component_type": "桥墩",
      "rows": [
        {
          "span": "全桥",
          "component": "构件编号",
          "score": 0.0,
          "defects": [
            {
              "scale": 0,
              "dp": 0,
              "s_init": 0,
              "items": [
                {"location": "病害位置", "desc": "病害描述"}
              ]
            }
          ]
        }
      ]
    },
    "桥台": {},
    "墩台基础": {"no_defect": true, "component_type": "墩台基础"},
    "河床": {},
    "调治构造物": {},
    "桥面铺装": {},
    "伸缩缝装置": {},
    "人行道": {},
    "栏杆、护栏": {},
    "排水系统": {},
    "照明、标志": {}
  },

  "chapter7": {
    "upper_structure_score": 0.0,
    "upper_structure_grade": "X类",
    "lower_structure_score": 0.0,
    "lower_structure_grade": "X类",
    "deck_score": 0.0,
    "deck_grade": "X类",
    "full_bridge_score": 0.0,
    "full_bridge_grade": "X类",
    "upper_parts_detail": [
      {
        "part": "部件名称",
        "part_score": 0.0,
        "grade": "X类",
        "counts": [{"score": 0.0, "count": 0}]
      }
    ],
    "lower_parts_detail": [],
    "deck_parts_detail": [],
    "class5_checks": [
      {
        "seq": 1,
        "item": "5类桥梁单项控制指标条款内容（依据规范第4.3节）",
        "triggered": false
      }
    ],
    "special_checks": [
      {
        "seq": 1,
        "item": "特殊规定核查条款（第4.1.8条/第4.1.7条）",
        "result": "核查结论",
        "triggered": false
      }
    ]
  },

  "weight_redistribution": [
    {
      "seq": 1,
      "structure": "上部结构/下部结构/桥面系",
      "part": "部件名称",
      "original": 0.0,
      "redistributed": 0.0,
      "note": "/"
    }
  ],

  "chapter8": {
    "conclusion": {
      "score": 0.0,
      "grade": "X类",
      "disease_summary": ["主要病害描述"]
    },
    "trends": [
      {
        "seq": 1,
        "disease": "病害名称",
        "last": "上次检查结果",
        "current": "本次检查结果",
        "trend": "快速发展/缓慢发展/稳定/改善恢复"
      }
    ],
    "cause_analysis": {
      "upper": ["上部结构原因分析"],
      "lower": ["下部结构原因分析"],
      "deck": ["桥面系原因分析"]
    },
    "mechanism_diagnosis": {
      "summary": "综合机理诊断结论（从推理报告步骤2.2.1的B部分原文提取，不得编造或修改）",
      "models_overview": [
        {
          "model_id": "M1",
          "name": "铰缝失效—单板受力",
          "hit_evidence_count": 0,
          "total_evidence_count": 4,
          "match_rate": 0.0,
          "max_match_score": 0.0,
          "triggered": false
        }
      ],
      "primary_mechanism": "M4（或 null，若机理不明确则填 null）",
      "primary_confidence": "明确 / 较明确 / 不明确",
      "watch_items": ["需持续关注的迹象或指标"],
      "further_inspection": ["建议的进一步检测项目（如无可填空数组）"]
    },
    "maintenance": {
      "emergency": "紧急处置建议",
      "special_inspection": "专项检查建议",
      "routine": ["常规养护建议"]
    },
    "missing_info": {
      "items": [
        {"param": "缺失的关键检测参数（如构件尺寸/裂缝深度/碳化深度/锈蚀电位等）", "handling": "处理方式（定性评定/单处面积评定/默认保守值）", "note": "补充说明"}
      ]
    },
    "data_collection_suggestions": ["推理中提出的数据进一步采集建议（如无可填空数组）"],
    "key_defects_analysis": {
      "summary": "文字说明：关键病害如何形成高标度→低构件分→低部件分→触发特殊条款→低等级的连锁反应，及养护最优先关注方向",
      "items": [
        {
          "seq": 1,
          "disease": "关键病害名称",
          "part": "所属部件",
          "indicator": "关键指标与得分（标度/DP/构件得分）",
          "path": "评分影响路径与原因"
        }
      ]
    }
  }
}"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 对外接口
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_user_section(data: dict) -> str:
    return f"""请对以下桥梁病害数据进行完整的技术状况评定分析：

## 基本信息
- 桥梁编号：{data.get('bridge_id',    '未提供')}
- 桥梁名称：{data.get('bridge_name',  '未提供')}
- 报告编号：{data.get('report_no',    '未提供')}
- 检测日期：{data.get('inspect_date', '未提供')}

## 桥梁基本参数
{json.dumps(data.get('bridge_params') or {}, ensure_ascii=False, indent=2)}

## 上次检测情况
{json.dumps(data.get('last_inspect') or {}, ensure_ascii=False, indent=2)}

## 本次病害数据
{json.dumps(data.get('defects') or {}, ensure_ascii=False, indent=2)}
"""


def build_extract_prompt(reasoning_text: str, data: dict) -> tuple[str, str]:
    """构建第二次调用的 system/user 消息。原始数据和推理报告一起给提取模型。"""
    system = _EXTRACT_SYSTEM

    user = f"""以下是对"{data.get('bridge_name', '该桥梁')}"的完整推理分析报告：

{reasoning_text}

═══════════════════════════════════

以下是该桥梁的原始输入数据（用于填充 chapter6 的位置和描述）：

## 桥梁基本参数
{json.dumps(data.get('bridge_params') or {}, ensure_ascii=False, indent=2)}

## 上次检测情况
{json.dumps(data.get('last_inspect') or {}, ensure_ascii=False, indent=2)}

## 本次病害数据
{json.dumps(data.get('defects') or {}, ensure_ascii=False, indent=2)}

═══════════════════════════════════

请从上述推理报告和原始数据中提取所有信息，严格按以下JSON模板填写。

要求：
1. chapter6：LLM只做三件事——①判断病害是否合并标度 ②确定scale值 ③给出score评分。其余字段必须从原始输入表格中原样复制，不得翻译、改写、推断或补充：
| 字段                     | 来源                      | 规则                             |
|--------------------------|---------------------------|----------------------------------|
| span                     | 原始表"跨径编号"/"桥墩编号"/"桥台编号" | 原样复制，不得改写              |
| component                | 原始表"构件编号"            | 原样复制，不得改写              |
| defects[].items[].location | 原始表"病害位置"          | 原样复制，不得修改              |
| defects[].items[].desc   | 原始表"病害描述"            | 原样复制，不得修改              |
| defects[].scale          | 推理报告                   | 该病害组的共用标度，组内所有items共用此值 |
| defects[].dp             | 推理报告步骤3              | 该病害组的扣分值（查表4.1.1），如推理报告未给出则根据M_opt和标度推算 |
| score                    | 推理报告                   | 从推理报告直接提取构件得分                          |
   禁止行为：禁止将"0#台身"改写为"第1跨"之类的翻译；禁止根据上下文推测缺失的编号；禁止修改原始文本的任何一个字。
   模板中列出全部16个标准部件，每个都必须填入，不可省略。根据推理报告判断每个部件状态，分三种情况：
       a) 有病害 → span/component/location/desc 原样复制原始表，scale/score 取自推理报告，填 rows 数组。
       b) 构件存在但未见明显病害 → 填 {{"no_defect": true, "component_type": "构件类型"}}。判断依据：推理报告中出现该部件的评分且无病害描述。
       c) 无此构件（推理报告中标注"无此构件"或构件数量=0）→ 填空对象 {{}}。

⚠️ 病害组规则（核心！）：推理报告步骤2通过"最终标度"列的非空/空来表达病害分组合并关系。一个"病害组" = 一段以非空标度行打头、后续空标度行跟随的连续行。同组病害共用一个标度（计算时只贡献1个DP）。不同组各有独立标度和DP。

chapter6 JSON中，defects数组的每一项 = 一个病害组：
- defects[].s_init = 该病害组的初步标度（从推理报告步骤1《病害标度初步评定表》该病害的 S_init 提取；若推理报告未单独给出，取与最终标度 scale 相同值）
- defects[].scale = 该组的共用标度值（从推理报告步骤2该组"最终标度"列提取）
- defects[].dp = 该组的扣分值（从推理报告步骤3"DP值确定"段落提取，即查表4.1.1得到的DP值）。若推理报告未明确给出，根据M_opt和标度查表4.1.1填写。例如M_opt=3且标度=2 → DP=20。
- defects[].items = 该组内全部病害，每个病害含 location 和 desc（从原始表原样复制）。同组有多个病害时 items 有多条；单病害组 items 仅1条。每个病害必须独立为 items 的一项，禁止拼接合并。
- 验证方法：推理报告步骤3中，若构件得分 = 100 - DP₁ → 该构件只有1个病害组（defects仅1项）。若构件得分明显小于 100-DP₁ → 必有≥2个病害组。
2. chapter7：从推理报告中提取各部件的得分和等级，并按相同得分分组填入 counts。parts_detail 中每个部件出现一次，其 counts 数组列出所有不同的得分及数量（含未出病害的构件，得分100，数量=总构件数-有病害构件数）。总构件数从原始输入中的"桥梁部件划分及构件数量表"（可能带表号如"表4.3-1"，以表名关键词为准）中读取，该表列出了每个部件的构件数量。
3. weight_redistribution：从推理报告步骤5的结构部位评分表中提取。每个部件的原始权重（original）和分配后权重（redistributed）直接从推理报告的步骤5《结构部位评分表》中读取。部件的 seq 按推理报告中出现的顺序从1开始编号。缺失部件的 redistributed 填 0.00，note 填"无此构件"。
4. chapter8：从推理报告中提取结论、趋势（含seq序号）、原因分析（按 upper/lower/deck 分组）、养护建议。其中 trends[].trend 必须从以下四个标准值中选一个："快速发展/缓慢发展/稳定/改善恢复"，由你根据推理报告中该病害的发展趋势语义判断归入（例如"稍有发展"归入"快速发展"或"缓慢发展"，"无明显发展/稳定"归入"稳定"，"好转/修复"归入"改善恢复"），禁止输出其它自由文本。
5. chapter8.missing_info：从推理报告中"检测信息不完整的处理原则"部分提取信息缺失推定。每条含 param（缺失的关键检测参数，如构件尺寸/裂缝宽度深度/材料强度/碳化深度/锈蚀电位等）、handling（该缺失参数的处理方式，如"构件尺寸缺失，按定性/单处面积评定"或"采用默认保守值"）、note（补充说明）。若推理报告未识别任何信息缺失，填 items 为空数组。
6. chapter8.data_collection_suggestions：从推理报告的机理诊断总结或养护建议中提取推理提出的"数据进一步采集建议"（需补充检测的关键指标/项目），如无可填空数组。
7. chapter7.class5_checks 和 chapter7.special_checks：从推理报告步骤6《全桥等级评定表》及其核查段落提取。
   - class5_checks 每条含 seq、item（5类桥梁单项控制指标的条款内容，依据规范第4.3节）、triggered（该条款是否触发，布尔值）。推理报告"5类桥梁单项控制指标强制核查"逐条核对的内容全部提取，不遗漏。
   - special_checks 每条含 seq、item（特殊规定核查条款，如第4.1.8条/第4.1.7条）、result（核查结论文字）、triggered（是否触发，布尔值）。
   - 若推理报告未输出核查内容，填空数组 []。
8. chapter8.key_defects_analysis：从推理报告末尾"3 影响评分的关键病害分析"章节提取。
   - items 对应"表3-1 关键病害影响分析表"的每一行：seq、disease（关键病害名称，如"2#台帽竖向裂缝"）、part（所属部件）、indicator（关键指标与得分，如"标度3，DP=45，构件得分47.2"）、path（评分影响路径与原因，即该表第5列的传导分析文字）。
   - summary 为该章节表格后的文字说明段落（总结"高标度→低构件分→低部件分→触发特殊条款→低等级"的连锁反应及养护最优先关注方向）。
   - 若推理报告未输出该章节，items 填空数组、summary 填空字符串。
9. dimension_inference：从推理报告步骤1《构件尺寸推算》及其他步骤中出现的尺寸推算、面积占比计算中提取，作为标度评定等判定的依据。每条含 item（推算项名称，如"单板底面可视面积""铺装磨光露骨面积占比"）、calc（计算公式与结果，如"1.12m × 14.0m = 15.68m²"或"350m² ÷ 360m² = 97.2%"）、note（说明，如"推算值，待核实"或"面积占比>20% → S_init=4"）。仅提取推理中实际进行的尺寸/面积推算，若推理报告未做任何推算，填空数组 []。
10. bridge_info：从推理报告步骤0《桥梁基本信息》前置输出中提取桥梁结构档案信息，含 route（路线编号及名称）、stake（桩号）、structure_type（结构类型）、span（跨径布置）、length（桥梁全长）、width（桥面宽度）、built_year（建成时间）、design_load（设计荷载）。逐项从推理报告步骤0的桥梁基本信息中提取，某项缺失则填空字符串。

只输出JSON，不加markdown代码块，不加任何解释：

{_JSON_TEMPLATE}"""

    return system, user
