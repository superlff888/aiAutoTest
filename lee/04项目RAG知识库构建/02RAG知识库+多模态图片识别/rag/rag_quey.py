# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\02RAG知识库+多模态图片识别\rag\rag_quey.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


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
