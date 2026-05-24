# @Author  : 木森
# @weixin: python771
from models import *
from llama_index.core import SimpleDirectoryReader


# =============第一步=========初始化嵌入模型（向量化处理文档）和对话模型（检索增强 ）=======================

# 初始化嵌入模型（向量化处理文档）和对话模型（检索增强 ），即from models import *

# =============第二步=========文档加载=======================
documents = SimpleDirectoryReader(input_dir='../docs2').load_data()
# print(documents)
print("文档加载完成！")
# ============第三步=========构建向量库=======================
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, Document, Settings
import chromadb


# 初始化向量客户端
client = chromadb.Client(
    settings=chromadb.Settings(
        persist_directory="../chroma_db",  # 向量数据保存在指定的文件夹下面
    )
)

# 初始化连接器
connect = client.get_or_create_collection(name="lee_001") # 连接到名为 "lee_001" 的集合，如果没有该集合就自动创建一个新的集合
# 初始化向量存储器
vector_store = ChromaVectorStore(chroma_collection=connect)

# 对文档进行向量化处理
# index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
# print("向量库构建完成！")
# # 对向量数据库中的内容进行持久化存储
# index.storage_context.persist(persist_dir="../chroma_db")
# print(index)


# ============第四步=========构建知识图谱=======================

from llama_index.core import PropertyGraphIndex

# 抽取文档中的知识图谱的关系和节点，并构建成知识图谱索引
print("抽取文档中的知识图谱的关系和节点...")
graph_index = PropertyGraphIndex.from_documents(
    documents, # 这里传入原始文档，知识图谱的构建过程会自动调用向量存储器对文档进行向量化处理
    vector_store=vector_store
    )
print("知识图谱构建完成！")
print(graph_index)

# 将知识图谱的索引数据持久化保存到磁盘上，这样在后续的查询过程中就可以直接加载这个索引数据，而不需要重新构建知识图谱了。
graph_index.storage_context.persist(persist_dir="../chroma_db")


"""
如果不执行 persist()，所有索引数据只存在于内存中，脚本运行结束后就会丢失。持久化后，下次可以直接从磁盘加载，无需重新对文档进行向量化和图谱抽取，大幅提升加载速度和查询效率。
"""