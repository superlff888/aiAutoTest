# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\01rag知识库搭建基础\rag\rag_quey.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
有开箱即用的LightRAG等，谁还自己写RAG啊，哈哈哈！！！

"""


from models import *
from llama_index.core import StorageContext, load_index_from_storage

# 加载向量数据库中的内容
storage_context = StorageContext.from_defaults(persist_dir="../chroma_db")
index = load_index_from_storage(storage_context=storage_context)

# 构建问答引擎
query_engine = index.as_query_engine(
    # 树形结构的方式来组织检索到的内容，并对这些内容进行总结和归纳，最后生成一个简洁的回答返回给用户
    response_mode="tree_summarize", 
    similarity_top_k=3,  # 返回最相似的3条内容
)

response = query_engine.query(
    "用户模块一共有哪些接口？"
)
print(response)




"""
一定要记得导入全局配置文件models.py，这样才能保证在rag_create.py中构建的向量库和知识图谱能够被正确地加载和使用，否则就会出现找不到模型的错误。
"""
