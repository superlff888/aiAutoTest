# 接口测试智能体项目开发规范

## 项目概述
- **项目名称**: API Testing Agent
- **项目类型**: AI 智能体应用
- **核心功能**: 基于大语言模型的接口自动化测试智能体，能够理解测试需求、生成测试用例、执行接口调用、验证响应结果

## 技术栈
- **编程语言**: Python 3.10+
- **AI框架**: LangChain
- **大模型**: OpenAI GPT / Claude / 国内模型（可配置）
- **HTTP客户端**: httpx / requests
- **测试框架**: pytest
- **配置管理**: pydantic + yaml
- **日志**: loguru

## 目录结构
```
api_testing_agent/
├── core/                    # 核心模块
│   ├── agent.py            # Agent 主逻辑
│   ├── chains/             # LangChain chains
│   ├── prompts/            # prompt 模板
│   └── tools/              # 工具函数
├── services/               # 服务层
│   ├── api_executor.py     # API 执行器
│   ├── case_generator.py   # 用例生成器
│   └── report_generator.py # 报告生成
├── models/                 # 数据模型
│   ├── api_schema.py       # API 数据结构
│   ├── test_case.py        # 测试用例模型
│   └── test_result.py      # 测试结果模型
├── config/                 # 配置文件
│   ├── settings.py         # 应用配置
│   └── prompts.yaml         # prompt 配置
├── utils/                  # 工具类
│   ├── logger.py           # 日志工具
│   └── validators.py       # 验证器
├── tests/                  # 单元测试
├── requirements.txt
└── README.md
```

## 编码规范

### 命名规范
- **类名**: PascalCase (如 `ApiExecutor`, `TestCaseGenerator`)
- **函数/方法名**: snake_case (如 `execute_api`, `generate_test_cases`)
- **变量名**: snake_case (如 `test_result`, `api_endpoint`)
- **常量**: UPPER_SNAKE_CASE (如 `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **私有成员**: 前缀 `_` (如 `_internal_method`)

### 文件命名
- Python 模块: snake_case (如 `api_executor.py`)
- 测试文件: `test_<模块名>.py`
- 配置类: `<模块名>_config.py`

### 代码风格
- 遵循 PEP 8
- 使用类型注解 (Type Hints)
- Docstring 使用 Google 风格
- 单行不超过 120 字符

### LangChain 规范
- 工具类必须继承 `BaseTool` 并实现 `Tool` 接口
- Chain 使用 LCEL (LangChain Expression Language) 语法
- Prompt 模板统一管理在 `config/prompts.yaml`
- 保持 memory 和 chain 分离

### AI 模型调用规范
- 所有 LLM 调用必须配置 temperature 和 max_tokens
- 支持多模型切换 (如 OpenAI / Claude / 通义)
- 使用结构化输出 (JSON mode) 获取可解析结果
- 合理使用缓存减少 token 消耗

## 开发流程

### 1. 需求分析
- 使用 AI 理解测试需求描述
- 提取关键信息：接口地址、方法、参数、预期结果

### 2. 用例生成
- 调用 LLM 生成测试用例
- 用例包含：请求方法、URL、Headers、Body、断言规则

### 3. 用例执行
- 使用 httpx 异步执行 HTTP 请求
- 支持参数化执行和数据驱动

### 4. 结果验证
- 自动比对实际响应与预期结果
- 支持 JSON Path / 正则 / 精确匹配

### 5. 报告输出
- 生成结构化测试报告
- 记录成功/失败详情和错误信息

## API 设计规范

### 数据模型
```python
# 所有数据模型使用 Pydantic BaseModel
class ApiRequest(BaseModel):
    method: HttpMethod
    url: HttpUrl
    headers: Optional[Dict[str, str]] = {}
    params: Optional[Dict[str, Any]] = None
    body: Optional[Any] = None
    timeout: int = 30
```

### 错误处理
- 自定义异常类 (如 `ApiTestingError`, `ValidationError`)
- 统一异常处理和日志记录
- 保留原始错误信息便于调试

## 测试规范
- 所有核心模块必须有单元测试
- 使用 pytest + pytest-asyncio
- Mock 外部依赖 (HTTP 请求、LLM 调用)
- 测试覆盖率目标 > 80%

## 配置管理
- 开发/测试/生产环境配置分离
- 敏感信息使用环境变量
- 支持 `.env` 文件加载

## 日志规范
- 使用 loguru
- 分级: DEBUG / INFO / WARNING / ERROR
- 日志文件按日期切割
- 敏感信息脱敏处理