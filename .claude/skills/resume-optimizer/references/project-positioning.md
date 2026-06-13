# aiAutoTest 项目卖点提炼 · 你的专属简历素材库

> 基于项目 [CLAUDE.md](../../../../CLAUDE.md) 已知信息，以下卖点可直接搬到简历中。
> ⚠️ **数字示例供参考，最终请用你能站住脚的真实数据替换**。

## 1. 项目一行话定位

```
AI 驱动的自动化测试工程实践：基于 LangChain + LangGraph 构建用例生成 Agent 工作流，
集成 LightRAG 知识库（向量+图双引擎）与 MCP 服务，覆盖需求理解→用例生成→评审→
覆盖率检查→存储全链路。
```

## 2. 拆分为 3 个独立简历项目

> **铁律**：拆开写比合成一个项目分量重 3 倍。

### 项目 A：AI 用例生成 Agent 工作流

| 字段 | 内容 |
|------|------|
| **定位** | LangGraph StateGraph + 并行 Send 评审 + 覆盖率反馈循环 |
| **技术栈** | LangChain, LangGraph, deepagents, Pydantic, MySQL, SiliconFlow API |
| **关键词** | StateGraph、Send API、TypedDict、operator.add、结构化输出、闭环优化 |
| **量化卖点** | 用例编写 30min → 2min（-93%）/ 覆盖率 95%+ / 沉淀 200+ Prompt 模板 |
| **对应代码** | `lee/05用例生成agent/03用例生成+数据存储集成Agent/` |

### 项目 B：企业 RAG 知识库构建

| 字段 | 内容 |
|------|------|
| **定位** | LightRAG 双引擎（向量+图）+ Qwen3-Embedding + ChromaDB |
| **技术栈** | LightRAG, ChromaDB, Qwen3-Embedding-8B, Redis, FastAPI |
| **关键词** | 向量检索、图检索、tree_summarize、top_k、Embedding |
| **量化卖点** | 召回率 65%→88%（+23pp）/ P95 延迟 1.2s / 月调用 12 万次 |
| **对应代码** | `rag/light-rag/` + `lee/04项目RAG知识库构建/` |

### 项目 C：AI 测试评估体系

| 字段 | 内容 |
|------|------|
| **定位** | 集成 promptfoo + Giskard 构建 LLM 评估流水线（CI/CD 集成） |
| **技术栈** | promptfoo, Giskard, RAGAS, LangFuse, GitLab CI |
| **关键词** | LLM Eval、Red Teaming、幻觉检测、Prompt 测试、对抗测试 |
| **量化卖点** | 评估周期 2 天 → 15min（-99%）/ 拦截 2 起 Prompt 注入 / 发现 23 个潜在幻觉 |
| **状态** | ⚠️ 项目中暂未实现，是 **可补强的卖点方向** |

## 3. 技能栈包装（直接复制到简历）

```
LLM 应用框架: LangChain、LangGraph、LlamaIndex、DeepAgents
RAG 技术栈:   LightRAG、ChromaDB、BGE-Embedding、Qwen3-Embedding
Agent 开发:   StateGraph、Send API、MCP、Function Call、Pydantic 结构化输出
AI 测试:      promptfoo、RAGAS、Giskard、Prompt 测试、幻觉检测
模型 API:     OpenAI、Anthropic Claude、Qwen、DeepSeek、SiliconFlow
工程基础:     Python 3.12、MySQL、Redis、Docker、Git、uv
```

## 4. 你的差异化优势（vs 其他候选人）

| 优势点 | 别人难复制的原因 | 怎么写进简历 |
|--------|----------------|-------------|
| **测试背景 + AI 实战** | 大部分 AI 工程师不懂测试方法论 | "测试方法论 + LLM 实战的双重视角" |
| **完整工程链路** | 多数人只做 demo，没做用例生成→存储全链路 | "覆盖 X→Y→Z 全链路的工程实战经验" |
| **MCP 早期实践者** | MCP 2024 年底才火，早期玩家稀缺 | "2025 年起跟进 MCP 协议，完成 N 个 MCP 服务集成" |
| **多模态 RAG** | 多模态 RAG 仍是难题 | "图文混合检索、PDF/Office 文档结构化处理" |

## 5. 还可以补强的方向（性价比高）

按价值密度排序，建议补 1-2 个就能大幅加分：

1. **AI 测试评估平台**（项目 C）—— 补全后简历竞争力 +50%
2. **开源贡献**：给 LangChain / LangGraph / promptfoo 提一个 PR
3. **技术分享**：在掘金/知乎写 3 篇 RAG / Agent 实战文章
4. **认证**：考一个 NVIDIA / DeepLearning.AI 的 LLM 工程师证书
5. **Benchmark**：在公开数据集上跑一遍你的 RAG 系统，发布到 GitHub

## 6. 项目命名优化建议

| 原始（土味） | 升级后（高级） |
|------------|--------------|
| 用例生成 Agent | **基于 LangGraph 的自适应测试用例生成系统** |
| RAG 知识库 | **多模态混合检索的企业级知识引擎** |
| AI 测试 | **LLM 应用全链路质量保障平台** |
| 自动化测试 | **AI 增强的智能化测试框架** |

> ⚠️ 别太浮夸，技术内核必须撑得起这个名字。
