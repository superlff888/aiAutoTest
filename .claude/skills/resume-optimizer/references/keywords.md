# 高频关键词清单 · AI 测试 / LLM 应用工程师

> **铁律**：JD 里出现的词，简历里必须有；ATS 系统按关键词匹配率筛简历。
> 关键词均来自 2025 年国内一线大厂大模型岗位面试题库交叉验证。

## 1. 必备核心词（≥80% JD 出现）

| 类别 | 关键词 | 说明 |
|------|--------|------|
| **基础栈** | Python、Pytest、Linux、Git、Docker、MySQL/PostgreSQL | 测试基本功 |
| **大模型框架** | **LangChain、LangGraph、LlamaIndex** | LLM 应用层标配 |
| **RAG** | **向量数据库（FAISS / Chroma / Milvus）、Embedding、检索增强、重排（Rerank）、分块（Chunking）** | RAG 技能栈 |
| **Agent** | **Agent、Tool Use、Function Call、ReAct、MCP** | Agent 开发标配 |
| **评估** | **LLM Evaluation、Prompt 测试、幻觉评估、Benchmark** | AI 测试硬通货 |
| **模型 API** | OpenAI、Anthropic、Qwen、DeepSeek、SiliconFlow | 写过哪个就列哪个 |

## 2. 加分高级词（写进去会被高看）

| 方向 | 关键词 |
|------|--------|
| **AI 测试专项** | **promptfoo、Giskard、Evidently、LangWatch、RAGAS、TruLens** |
| **RAG 高级** | HyDE、MultiQuery、Self-RAG、Hybrid Search、BGE-Reranker |
| **Agent 高级** | LangGraph StateGraph、Multi-Agent、Send API、CheckPointer |
| **训练相关** | LoRA、QLoRA、PEFT、SFT、DPO、PPO（即使没训过，了解概念也是加分） |
| **可观测性** | LangSmith、LangFuse、Phoenix、OpenLLMetry |
| **部署** | vLLM、TGI、Ollama、SGLang |

## 3. 测试工程师转 AI 测试的差异化词

| 传统测试 | AI 测试（升级版） |
|----------|----------------|
| 接口自动化 | **LLM 接口契约测试、Function Call 调用链验证** |
| UI 自动化 | **Agent 决策路径验证、Tool 调用准确率测试** |
| 性能测试 | **LLM 吞吐 / 延迟 / Token 成本压测** |
| 数据驱动 | **Prompt 数据集驱动评估、用例生成 Agent** |
| 覆盖率 | **Prompt 覆盖率、Agent 决策分支覆盖率、知识库召回覆盖率** |
| Mock | **LLM Mock、流式 Mock、Tool Mock** |
| 缺陷管理 | **幻觉检测、安全红队、Jailbreak 测试** |

## 4. ⚠️ 避坑：这些词写了反而扣分

- ❌ "**精通** XX"（除非你是该领域作者，否则永远写"熟练"或"具备实战经验"）
- ❌ "**深入理解** Transformer / 大模型原理"（被追问会很尴尬）
- ❌ "**全栈**"（在 AI 岗里这词不值钱）
- ❌ "**人工智能** / **机器学习**"（太泛，要具体到 LLM/RAG/Agent）
- ❌ "**AIGC**"（已经是 2023 年的词，2026 年用显得过时）

## 5. 使用建议

- **关键词三处覆盖**：求职意向 + 技能列表 + 项目经验 都要出现核心关键词
- **数量控制**：核心技能列出 6-10 个分类，单类不超过 5 个具体名词
- **避免简称**：写 LangChain 不写 LC，写 Function Call 不写 FC
- **匹配 JD**：投递前对照 JD 把出现 ≥2 次的词都补到简历里

## 6. 数据来源

- [Awesome-LLM-Interview-Questions](sources/02-awesome-llm-interview-cn.md) - 2025 国内大厂面试题库
- [LLM-Resume-Template](sources/01-llm-resume-template.md) - 大模型工程师 LaTeX 简历模板
- [promptfoo](sources/04-promptfoo.md) - LLM 评估标杆工具
