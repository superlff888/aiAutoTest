# @Author  : 木森
# @weixin: python771
import os
import dotenv
from llama_index.core import Settings
from llama_index.embeddings import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from llama_index.core import SimpleDirectoryReader  

Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),    
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

Settings.llm = OpenAILike(
    model_name=os.getenv("LLM_MODEL"),    
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.1,
    max_tokens=2048,    
)


"""
[RAGFlow简介]

RAGFlow是一个基于LlamaIndex构建的RAG（Retrieval-Augmented Generation）知识库构建和查询框架，提供了从文档加载、向量化处理、知识图谱抽取到查询接口的一站式解决方案。通过RAGFlow，用户可以轻松地将各种类型的文档（如文本、PDF、图片等）转换为可检索的知识库，并通过自然语言查询接口进行高效的信息检索和生成。RAGFlow的核心功能包括：
1. 文档加载：支持从本地文件系统加载各种格式的文档，并进行预处理。
2. 向量化处理：利用预训练的嵌入模型将文档内容转换为向量表示，便于后续的相似度检索。
3. 知识图谱抽取：从文档中抽取实体和关系，构建知识图谱索引，支持复杂的关系查询。
4. 查询接口：提供自然语言查询接口，支持基于向量检索和知识图谱的混合查询，提升查询的准确性和丰富性。

RAGFlow部署对服务器的要求比较高！！！


LightRAG简介
LightRAG是一个轻量级的RAG（Retrieval-Augmented Generation）知识库构建和查询框架，旨在提供一个简化版本的RAGFlow，适用于资源有限的环境或对性能要求较高的应用场景。LightRAG保留了RAGFlow的核心功能，如文档加载、向量化处理和查询接口，但在实现上进行了优化，以减少对服务器资源的占用。LightRAG的特点包括：
1. 轻量级设计：采用更高效的数据结构和算法，减少内存占用和计算开销，适合在资源受限的环境中运行。
2. 模块化架构：提供灵活的模块化设计，用户可以根据需求选择性地使用不同的功能模块，进一步优化性能。
3. 简化的知识图谱抽取：提供一个简化版本的知识图谱抽取功能，适用于对关系抽取要求不高的应用场景，进一步降低资源消耗。
4. 高效的查询接口：优化查询算法，提升查询效率，适合对性能要求较高的应用场景。   

"""