# @Author  : 木森
# @weixin: python771
from models import *
from llama_index.core import StorageContext, load_index_from_storage

# 加载向量数据库中的内容
storage_context = StorageContext.from_defaults(persist_dir="../chroma_db")
index = load_index_from_storage(storage_context=storage_context)

# 构建问答引擎
query_engine = index.as_query_engine(
    response_mode="tree_summarize",
    similarity_top_k=3,
)

response = query_engine.query(
    "用户模块一共有哪些接口？"
)
print(response)
