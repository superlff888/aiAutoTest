# CLAUDE.md

> **重要**：所有交流、注释、输出必须使用中文，包括思考过程（thinking）也必须使用中文。

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**aiAutoTest** 是一个 AI 驱动的自动化测试学习/实验项目，基于 Python 3.12。主要方向包括：

- LangChain/LangGraph Agent 开发
- RAG 知识库构建（向量检索 + 图检索）
- 自动化用例生成、评审、覆盖率检查与数据库存储
- MCP 服务集成

## 常用命令

### 环境设置

```bash
uv sync          # 安装/同步依赖（从 uv.lock）
```

### 运行模块

```bash
# 直接运行任意 Python 脚本
python lee/01helloWorld/01大模型交互的第一个程序.py
python lee/05用例生成agent/03用例生成+数据存储集成Agent/rag_agent/agent.py

# 独立运行用例生成工作流（含 __main__ 示例）
python lee/05用例生成agent/03用例生成+数据存储集成Agent/rag_agent/workflow/case_generator.py
```

### LightRAG 服务

- 配置见 `rag/.env`，默认端口 9621
- 输入文档放在 `rag/light-rag/inputs/Rag1000/__enqueued__/`
- 持久化数据在 `rag/light-rag/rag_storage/Rag1000/`

### 测试

项目未配置测试框架。通过直接运行脚本验证功能。

## 代码架构

### 目录结构

```
lee/                              # 主源码区，按编号组织学习模块
├── 01helloWorld/                 # 基础 LLM 交互
├── 02提示词工程/                  # 提示词模板、多轮对话、few-shot
├── 03langchain框架/               # LangChain 核心组件
│   ├── 01~09/                    # Agent 组件、记忆、中间件、MCP、LangGraph 编排
│   └── utils/                    # 共享工具：数据库连接、输出格式化
├── 04项目RAG知识库构建/            # RAG 知识库（向量+图+多模态）
│   ├── 01~03/                    # 基础 RAG -> 多模态 -> 完整 RAG Agent
│   └── docs/, docs2/             # 需求说明书与 API 文档（被 RAG 索引）
├── 05用例生成agent/               # 用例生成 Agent（最成熟模块）
│   ├── 01~03/                    # 基础生成 -> 带评审 -> 带存储集成
│   └── pormpts/                  # 系统提示词模板
└── 扩展内容/                      # 异步编程、Pydantic、输出解析器、Runnable

rag/                              # LightRAG 服务部署
├── .env                          # 服务配置（LLM、Embedding、Redis 等）
├── light-rag/inputs/             # 待索引文档
└── light-rag/rag_storage/        # 图存储 + 向量存储持久化
```

### 核心架构模式

**Agent-Tool 模式**: 所有模块遵循 `Agent + Tools + System Prompts + LLM` 结构。

- Agent 使用 `deepagents/create_deep_agent` 或 LangGraph `StateGraph` 创建
- Tool 通过 `@tool` 装饰器定义（RAG 查询、用例生成、数据库操作等）
- LLM 通过 SiliconFlow API 调用 OpenAI 兼容接口

**LangGraph 用例生成工作流** (`lee/05用例生成agent/03用例生成+数据存储集成Agent/rag_agent/workflow/case_generator.py`):

```
START -> 用例生成 -> 用例评审 (并行 Send) -> 覆盖率检查
  -> 100%: 保存用例 -> END
  -> <100%: 补充生成 -> 回到用例评审 (循环)
```

状态通过 `TypedDict` + `Annotated[List, operator.add]` 管理。

**RAG 管线**:

```
文档 -> SimpleDirectoryReader -> Embedding (Qwen3-Embedding-8B)
  -> ChromaDB -> Query Engine (tree_summarize, top_k=3)
```

**结构化输出**: 全程使用 Pydantic 模型定义用例结构（`GenerateCase`, `CaseList`）。

### 环境配置

所有模块通过 `.env` 文件配置（已被 git 忽略）：

- LLM API Key / Endpoint（SiliconFlow）
- MySQL 连接参数
- RAG 知识库 URL
- 模型名称和温度参数

### 测试

项目未配置自动化测试框架。验证方式为直接运行脚本并观察控制台输出。

## aiAutoTester 技能规范

### 目录约定

```
.claude/
├── skills/aiAutoTester/                    # 技能代码（SKILL.md + scripts/）
│   ├── 01requirement-splitter/SKILL.md     # 需求拆分（纯 AI Agent，无脚本）
│   ├── 02testpoint-extractor/SKILL.md      # 测试点提取（纯 AI Agent，无脚本）
│   ├── 03testpoint-reviewer/SKILL.md       # 测试点评审（纯 AI Agent，无脚本）
│   └── 04testcase-exporter/
│       ├── SKILL.md                        # 用例设计 + Excel 导出
│       └── scripts/_pipeline.py            # 唯一需要脚本的技能（阶段3→4→5）
└── output/aiAutoTester/                    # 统一产物输出目录
    └── {项目名}/
        └── 06_testcase_export/             # 最终 Excel 交付物
```

### 关键规则

1. **统一输出目录**：所有技能产物输出到 `.claude/output/{技能名}/{项目名}/`，禁止输出到项目根目录或其他位置
2. **代码与产物分离**：`skills/` 下只放 SKILL.md 和 `scripts/`，不放生成的 JSON/Excel 等数据文件
3. **脚本存放规范**：技能的可执行脚本统一放在对应子技能的 `scripts/` 目录下
4. **流水线自动清理**：`_pipeline.py` 执行完成后自动清理中间产物（`03_requirements/`、`04_testpoints/`、`05_testpoint_review/`），仅保留 `06_testcase_export/` 下的最终 Excel

### 执行流程

```
需求文档 (PDF/Word/PPT/md)
    ↓ 阶段1: requirement-splitter (AI Agent)
    ↓   输出: 03_requirements/{章节}/requirements.json
    ↓ 阶段2: testpoint-extractor (AI Agent)
    ↓   输出: 04_testpoints/{章节}/testpoints.json
    ↓ 阶段3-5: _pipeline.py (脚本)
    ↓   测试点提取 → 覆盖率评审 → 用例设计 + Excel 导出
    ↓   输出: 06_testcase_export/{项目名}_测试用例_{日期}.xlsx
    ↓   自动清理: 03/ 04/ 05/ 中间目录
```

### 项目类型识别

支持自动识别以下项目类型，激活对应检查清单：

| 项目类型 | 识别关键词 | 检查清单 |
|----------|-----------|---------|
| API/协议类 | OCPI、HTTP、接口、REST、API | 接口覆盖度检查 |
| 跨境/跨区域 | 跨境、香港、澳门、海外、多语言 | 跨境场景检查 |
| 支付/金融 | 支付、结算、对账、发票、税务 | 金融合规检查 |
| 电力交易 | 电力交易、售电、购电、电价、负荷、出清 | 电力交易场景检查（12项） |
