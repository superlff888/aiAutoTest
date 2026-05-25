# 开箱即用的 RAG 知识库

## LightRAG 简介

LightRAG 是一个轻量级的 RAG（Retrieval-Augmented Generation）知识库构建和查询框架，旨在提供一个简化版本的 RAGFlow，适用于资源有限的环境或对性能要求较高的应用场景。LightRAG 保留了 RAGFlow 的核心功能，如文档加载、向量化处理和查询接口，但在实现上进行了优化，以减少对服务器资源的占用。

**LightRAG 的特点：**

1. **轻量级设计**：采用更高效的数据结构和算法，减少内存占用和计算开销，适合在资源受限的环境中运行。
2. **模块化架构**：提供灵活的模块化设计，用户可以根据需求选择性地使用不同的功能模块，进一步优化性能。
3. **简化的知识图谱抽取**：提供一个简化版本的知识图谱抽取功能，适用于对关系抽取要求不高的应用场景，进一步降低资源消耗。
4. **高效的查询接口**：优化查询算法，提升查询效率，适合对性能要求较高的应用场景。

**配置LightRAG**

```
###########################
### 服务端配置
###########################
HOST=0.0.0.0
PORT=9621
WEBUI_TITLE='项目知识库'
WEBUI_DESCRIPTION="项目知识库"
# WORKERS=2
### gunicorn worker 超时时间（如果未设置 LLM_TIMEOUT，则作为默认 LLM 请求超时）
# TIMEOUT=150
# CORS_ORIGINS=http://localhost:3000,http://localhost:8080

### 可选 SSL 配置
# SSL=true
# SSL_CERTFILE=/path/to/cert.pem
# SSL_KEYFILE=/path/to/key.pem

### 目录配置（默认使用当前工作目录）
### 默认值为 ./inputs 和 ./rag_storage
# INPUT_DIR=<文档输入目录的绝对路径>
# WORKING_DIR=<工作目录的绝对路径>

### Tiktoken 缓存目录（用于离线部署时缓存 tokenizer 文件）
# TIKTOKEN_CACHE_DIR=/app/data/tiktoken

### 图检索最大节点数（需同步修改 WebUI 本地限制）
# MAX_GRAPH_NODES=1000

### 日志级别
# LOG_LEVEL=INFO
# VERBOSE=False
# LOG_MAX_BYTES=10485760
# LOG_BACKUP_COUNT=5

### 日志文件存放目录（默认当前工作目录）
# LOG_DIR=/path/to/log/directory

#####################################
### 登录与 API-Key 配置
#####################################
# AUTH_ACCOUNTS='admin:admin123,user1:pass456'
# TOKEN_SECRET=用于 LightRAG API Server 的密钥
# TOKEN_EXPIRE_HOURS=48
# GUEST_TOKEN_EXPIRE_HOURS=24
# JWT_ALGORITHM=HS256

### 访问 LightRAG Server API 的密钥
### 在 HTTP 请求中通过 X-API-Key 头使用
### 示例：curl -H "X-API-Key: your-secure-api-key-here" http://localhost:9621/query
LIGHTRAG_API_KEY= sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# WHITELIST_PATHS=/health,/api/*

######################################################################################
### 查询配置
###
### 控制发送给 LLM 的上下文长度：
###    MAX_ENTITY_TOKENS + MAX_RELATION_TOKENS < MAX_TOTAL_TOKENS
###    Chunk_Tokens = MAX_TOTAL_TOKENS - 实际实体 tokens - 实际关系 tokens
######################################################################################
# 查询阶段 LLM 响应缓存（不适用于流式响应）
ENABLE_LLM_CACHE=true
# COSINE_THRESHOLD=0.2
### 从知识图谱中检索的实体 / 关系数量
# TOP_K=40
### 向量搜索中最多返回的 chunk 数
# CHUNK_TOP_K=20
### 控制发送给 LLM 的实体 tokens 上限
# MAX_ENTITY_TOKENS=6000
### 控制发送给 LLM 的关系 tokens 上限
# MAX_RELATION_TOKENS=8000
### 控制发送给 LLM 的最大 tokens（实体 + 关系 + chunk）
# MAX_TOTAL_TOKENS=30000

### Chunk 选择策略
###     VECTOR：基于向量相似度选取 chunk，更接近传统向量检索
###     WEIGHT：基于实体和 chunk 权重，更偏向 KG 相关 chunk
###     若开启 rerank，该策略影响会被削弱
# KG_CHUNK_PICK_METHOD=VECTOR

#########################################################
### 重排序（Rerank）配置
### RERANK_BINDING 类型：null, cohere, jina, aliyun
### 若使用 vLLM 部署的 rerank 模型，请使用 cohere 绑定
#########################################################
RERANK_BINDING=null
### 当 RERANK_BINDING 非 null 时，查询参数中默认启用 rerank
# RERANK_BY_DEFAULT=True
### rerank 分数过滤阈值（设为 0.0 表示保留全部；LLM 能力较弱建议 ≥0.6）
# MIN_RERANK_SCORE=0.0

### 本地 vLLM rerank 示例
# RERANK_MODEL=Qwen/Qwen3-Reranker-8B
# RERANK_BINDING_HOST=http://localhost:8000/v1/rerank
# RERANK_BINDING_API_KEY=your_rerank_api_key_here



### Cohere rerank 分块配置（适用于 ColBERT 等 token 限制模型）
# RERANK_ENABLE_CHUNKING=true
# RERANK_MAX_TOKENS_PER_DOC=480

### Jina AI rerank
# RERANK_MODEL=Qwen/Qwen3-Reranker-8B
# RERANK_BINDING_HOST=https://api.jina.ai/v1/rerank
# RERANK_BINDING_API_KEY=your_rerank_api_key_here


########################################
### 文档处理配置
########################################
ENABLE_LLM_CACHE_FOR_EXTRACT=true

### 文档处理输出语言：English、Chinese、French、German 等
SUMMARY_LANGUAGE=Chinese

### 加密 PDF 文件的解密密码
# PDF_DECRYPT_PASSWORD=your_pdf_password_here

### LLM 识别的实体类型
# ENTITY_TYPES='["Person","Creature","Organization","Location","Event","Concept","Method","Content","Data","Artifact","NaturalObject"]'

### 文档切分 chunk 大小（建议 500~1500）
CHUNK_SIZE=1200
CHUNK_OVERLAP_SIZE=100

### 触发实体/关系合并时 LLM 总结的最小段数或 tokens（建议 ≥3）
# FORCE_LLM_SUMMARY_ON_MERGE=8
### 触发总结的最大描述 tokens
# SUMMARY_MAX_TOKENS=1200
### 推荐的总结输出 tokens 数
# SUMMARY_LENGTH_RECOMMENDED_=600
### 用于描述总结的最大上下文长度
# SUMMARY_CONTEXT_SIZE=12000

### 控制实体 / 关系中存储的最大 chunk_id 数量
# MAX_SOURCE_IDS_PER_ENTITY=300
# MAX_SOURCE_IDS_PER_RELATION=300
### chunk_id 限制策略：FIFO 或 KEEP
###    FIFO：先进先出
###    KEEP：保留最早的（合并更少，性能更快）
# SOURCE_IDS_LIMIT_METHOD=FIFO

# 实体 / 关系中显示的最大文件路径数量（仅用于展示）
# MAX_FILE_PATHS=100

### 每个实体/关系最多关联的 chunk 数
### 值越大 rerank 时间越长
# RELATED_CHUNK_NUMBER=5

###############################
### 并发配置
###############################
### LLM 最大并发请求数（查询 + 文档处理）
MAX_ASYNC=10
### 文档并行处理数（建议 2~10，约 MAX_ASYNC/3）
MAX_PARALLEL_INSERT=4
### Embedding 最大并发
EMBEDDING_FUNC_MAX_ASYNC=10
### 单次 embedding 请求包含的 chunk 数
EMBEDDING_BATCH_NUM=10

###########################################################################
### LLM 配置
### LLM_BINDING 类型：openai, ollama, lollms, azure_openai, aws_bedrock, gemini
### LLM_BINDING_HOST：Ollama 填 host，其它填 API endpoint
###########################################################################
# LLM_TIMEOUT=180
LLM_BINDING=openai
LLM_MODEL=deepseek-ai/DeepSeek-V3.2
LLM_BINDING_HOST=https://api.siliconflow.cn/v1
LLM_BINDING_API_KEY=sk-jrmhbqgzglnfxyrxxxxxxxxxxxxxxxxxxxx


#######################################################################################
### Embedding 配置（首次处理文件后不应再修改）
#######################################################################################

EMBEDDING_BINDING=openai
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIM=4096
EMBEDDING_SEND_DIM=false
EMBEDDING_TOKEN_LIMIT=8192
EMBEDDING_BINDING_HOST=https://api.siliconflow.cn/v1
EMBEDDING_BINDING_API_KEY=sk-jrmhbqgzglnfxyrtyhxxxxxxxxxxxxxxxxxxxxx

####################################################################
### WORKSPACE：用于隔离不同 LightRAG 实例的数据
### 允许字符：a-z A-Z 0-9 _
####################################################################
WORKSPACE=Rag1000

############################
### 数据存储配置
############################
### Redis 配置
REDIS_URI=redis://localhost:6379
REDIS_SOCKET_TIMEOUT=30
REDIS_CONNECT_TIMEOUT=10
REDIS_MAX_CONNECTIONS=100
REDIS_RETRY_ATTEMPTS=3

```

---

## RAGFlow 简介

RAGFlow 是一个基于 LlamaIndex 构建的 RAG（Retrieval-Augmented Generation）知识库构建和查询框架，提供了从文档加载、向量化处理、知识图谱抽取到查询接口的一站式解决方案。通过 RAGFlow，用户可以轻松地将各种类型的文档（如文本、PDF、图片等）转换为可检索的知识库，并通过自然语言查询接口进行高效的信息检索和生成。

**RAGFlow 的核心功能：**

1. **文档加载**：支持从本地文件系统加载各种格式的文档，并进行预处理。
2. **向量化处理**：利用预训练的嵌入模型将文档内容转换为向量表示，便于后续的相似度检索。
3. **知识图谱抽取**：从文档中抽取实体和关系，构建知识图谱索引，支持复杂的关系查询。
4. **查询接口**：提供自然语言查询接口，支持基于向量检索和知识图谱的混合查询，提升查询的准确性和丰富性。

> **注意**：RAGFlow 部署对服务器的要求比较高！
