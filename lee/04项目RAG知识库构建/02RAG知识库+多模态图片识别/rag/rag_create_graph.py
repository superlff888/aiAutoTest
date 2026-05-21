# @Author  : 木森
# @weixin: python771
from models import *
from llama_index.core import SimpleDirectoryReader

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
        persist_directory="../chroma_db",
    )
)

# 初始化连接器
connect = client.get_or_create_collection(name="musen_001")
# 初始向量存储器
vector_store = ChromaVectorStore(chroma_collection=connect)

# 对文档进行向量化处理
# index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
# print("向量库构建完成！")
# # 对向量数据库中的内容进行持久化存储
# index.storage_context.persist(persist_dir="../chroma_db")
# print(index)

# 抽取文档中的知识图谱的关系和节点
from llama_index.core import PropertyGraphIndex

print("抽取文档中的知识图谱的关系和节点...")
graph_index = PropertyGraphIndex.from_documents(documents, vector_store=vector_store)
print("知识图谱构建完成！")
print(graph_index)

graph_index.storage_context.persist(persist_dir="../chroma_db")
