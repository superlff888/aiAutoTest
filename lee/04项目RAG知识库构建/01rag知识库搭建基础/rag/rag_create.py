
from models import *
from llama_index.core import SimpleDirectoryReader


# =============第一步=========初始化嵌入模型（向量化处理文档）和对话模型（检索增强 ）=======================

# 初始化嵌入模型（向量化处理文档）和对话模型（检索增强 ），即from models import *


# =============第二步=========文档加载=======================
documents = SimpleDirectoryReader(input_dir='../docs').load_data()
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
index = VectorStoreIndex.from_documents(documents, vector_store=vector_store)
print("向量库构建完成！")
# print(index)

# 对向量数据库中的内容进行持久化存储
index.storage_context.persist(persist_dir="../chroma_db")
