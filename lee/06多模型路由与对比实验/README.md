# 06 多模型路由与对比实验

> **目标**：在 `lee/05用例生成agent` 之外，独立验证 **DeepSeek-V4-Pro** 与 **MiniMax-M3** 在"用例生成 + 评审 + 覆盖率"工作流中的真实表现，给出数据化的选型依据。

---

## 0. 与原项目的关系

| 原项目文件 | 本实验对应文件 | 差异 |
|---|---|---|
| `lee/05用例生成agent/02用例生成&评审的代码rag_agent/workflow/case_generator.py` | `case_generator_multi.py` | 节点结构、状态、prompt 全部照搬，**只把全局 `llm_model` 替换成 `model_router.get_llm_for_task()`** |
| `lee/05用例生成agent/02用例生成&评审的代码rag_agent/models.py` | `model_router.py` | 原来只有一个模型；现在按"任务类型"做路由 |
| （无） | `compare_models.py` | 新增；让两个模型在同一份需求集上 PK |
| （无） | `eval_dataset/` | 新增；评测需求 + 报告输出 |

**本实验完全独立**，不修改原项目任何代码。

---

## 1. 目录结构

```
lee/06多模型路由与对比实验/
├── README.md                     # 本文件
├── model_router.py               # ★ 模型路由：任务类型 → 模型
├── case_generator_multi.py       # ★ 多模型版用例生成工作流（LangGraph）
├── compare_models.py             # ★ 双模型对比评测脚本
├── outputs/                      # 跑工作流产出的用例 JSON
└── eval_dataset/
    ├── requirements_samples.json # 评测需求集（首跑自动生成）
    └── results/                  # 评测报告（JSON + Markdown）
```

---

## 2. 路由策略一览

默认（`model_router.py` 中的 `DEFAULT_ROUTING`）：

| 任务类型 | 主选模型 | 备选/理由 |
|---|---|---|
| `CASE_GENERATION`（用例生成） | **deepseek-v4-pro** | 推理强、JSON 长输出稳 |
| `CASE_SUPPLEMENT`（补充生成） | **deepseek-v4-pro** | 同上 |
| `CASE_REVIEW`（用例评审） | **deepseek-v4-pro** | 严格判等/规则 |
| `COVERAGE_CHECK`（覆盖率检查） | **deepseek-v4-pro** | 逻辑判断密集 |
| `STRUCTURED_EXTRACT`（结构化抽取） | **deepseek-v4-pro** | 长 JSON 抽取稳 |
| `CODE_GEN`（代码生成） | **deepseek-v4-pro** | 代码/推理双强 |
| `RAG_QUERY`（RAG 问答） | **MiniMax-M3** | 中文语义细腻 |
| `RAG_RERANK`（检索重排） | **MiniMax-M3** | 中文文档阅读细腻 |
| `REQUIREMENT_PARSE`（需求拆解） | **MiniMax-M3** | 中文理解优势 |
| `SIMPLE_CHAT`（兜底闲聊） | **MiniMax-M3** | 风格自然 |

> 想换模型？只改 `DEFAULT_ROUTING` 这一张表，全局生效。

---

## 3. 快速上手

### 3.1 查看路由表 / 模型清单

```bash
cd lee/06多模型路由与对比实验
python model_router.py --list
```

### 3.2 跑一次最小连通性测试（每个任务调一次）

```bash
python model_router.py --test
```

会打印形如：
```
[CASE_GENERATION] -> deepseek-v4-pro :: '好'
[RAG_QUERY]        -> MiniMax-M3     :: '好'
...
```

### 3.3 跑多模型版用例生成工作流

```bash
# 默认：DeepSeek 主，RAG 走 M3
python case_generator_multi.py

# 临时强制把全节点切到 M3，验证 M3 也能跑
python case_generator_multi.py --model MiniMax-M3

# 只把"用例生成"切到 M3，其它保持默认
python case_generator_multi.py --model MiniMax-M3 --task CASE_GENERATION

# 跑完导出本次用量
python case_generator_multi.py --export-usage outputs/usage_demo.json
```

工作流产物：`outputs/cases_multi.json`

### 3.4 跑双模型对比评测

```bash
# 默认：用 3 份内置需求，各跑 1 轮
python compare_models.py

# 自定义需求集
python compare_models.py --dataset eval_dataset/requirements_samples.json

# 每份需求跑 3 轮，看稳定性
python compare_models.py --rounds 3

# 只生成 Markdown 报告
python compare_models.py --report md
```

报告输出：
- `eval_dataset/results/comparison_<时间戳>.json`
- `eval_dataset/results/comparison_<时间戳>.md`
- `eval_dataset/results/usage_<时间戳>.json`（每次调用的 token 原始数据）

---

## 4. 对比维度说明

`compare_models.py` 评测每个模型在每份需求上的：

| 维度 | 指标 | 意义 |
|---|---|---|
| **质量 - 数量** | `case_count` | 生成用例总数 |
| **质量 - 完整** | `field_completeness` | 必备字段都不缺的比例（7 个核心字段） |
| **质量 - 分布** | `priority_dist` | P0/P1/P2 数量分布 |
| **质量 - 自评** | `self_review_rate` | 同一模型评审自己前 5 条用例的通过率 |
| **质量 - 覆盖** | `coverage_pct` | 模型自评覆盖率（0~100） |
| **性能 - 耗时** | `elapsed_sec` | 生成 + 自评 + 自检 总耗时 |
| **性能 - 成本** | token 用量 / 估算成本 | input + output tokens；按 `.env` 中的参考价估算 |
| **稳定性** | 异常次数 | 调用失败 / 解析失败的次数 |

---

## 5. 评测集设计

默认 3 份需求（`DEFAULT_REQUIREMENTS`），覆盖三种典型复杂度：

| ID | 名称 | 复杂度 | 重点考察 |
|---|---|---|---|
| `req_001` | 用户注册 | 简单 | 基础流程 + 字段约束 |
| `req_002` | 商品加入购物车 | 中等 | 状态/上限/库存 等多规则 |
| `req_003` | 订单取消 | 复杂 | 多状态流转 + 退款 + 防误操作 |

**首跑时脚本会自动把它们写入 `eval_dataset/requirements_samples.json`**，下次可以直接读。

要追加需求？往这个 JSON 里加 `{"id":..., "name":..., "text":"..."}` 即可。

---

## 6. 切模型 / 改路由 的姿势

### 6.1 代码里改（推荐：写一次就够）

编辑 `model_router.py` 的 `DEFAULT_ROUTING` 字典：

```python
DEFAULT_ROUTING: Dict[TaskType, str] = {
    TaskType.CASE_GENERATION: "MiniMax-M3",   # ← 改这里
    TaskType.RAG_QUERY:       "deepseek-v4-pro",
    ...
}
```

### 6.2 运行时改（适合 A/B / 评测）

```python
from model_router import set_routing, TaskType
set_routing(TaskType.CASE_GENERATION, "MiniMax-M3")
```

CLI：
```bash
python case_generator_multi.py --model MiniMax-M3 --task CASE_GENERATION
```

### 6.3 加新模型

在 `model_router.py` 的 `_build_profiles()` 里追加一段，`.env` 加对应变量即可。

---

## 7. 期望结论（基于通用经验）

> ⚠️ 以下为通用经验推断，**真实数据以 `compare_models.py` 跑出的报告为准**。

- **用例生成/评审/覆盖**：DeepSeek 推理强 + JSON 稳，胜率更高；token 成本也更低。
- **RAG/中文需求拆解**：M3 中文细腻度高，更适合。
- **混合路由**：主流程用 DeepSeek（省钱+快），需要中文细腻度的子任务用 M3——这是本实验的**核心论点**。

跑完 `compare_models.py` 后，把 `eval_dataset/results/comparison_*.md` 的结论贴到这里，对比真实数据 vs 经验。

---

## 8. FAQ

**Q1：跑 `case_generator_multi.py` 报 `ModuleNotFoundError: No module named 'pormpts'` 怎么办？**

A：脚本默认从 `lee/05用例生成agent/02用例生成&评审的代码rag_agent/` 复用 prompt。如果路径拼不上，会自动 fallback 到本地极简 prompt（脚本里 try/except 兜底）。Fallback 不影响跑通，但 prompt 质量会下降。建议检查 `PROJECT_ROOT` 路径。

**Q2：DeepSeek / M3 的 API 超时怎么办？**

A：在 `model_router.py` 里把 `timeout=120` 调大；或者改 `_build_profiles()` 里对应模型的 `timeout` 字段。

**Q3：评测报告里 cost=0 是 bug 吗？**

A：不是。`_build_profiles()` 里的 `price_input / price_output` 是**参考价**，按你们实际签的合同改一下就有数了。

**Q4：能不能跑 5 个模型对比？**

A：能。`python compare_models.py --models deepseek-v4-pro MiniMax-M3 qwen3.6-plus kimi-k2.6 MiniMax-M2.5`，但要先在 `model_router.py` 注册这些模型。
