# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\01rag知识库搭建基础\models.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from llama_index.core import Settings, SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

dotenv.load_dotenv()

"""初始化嵌入模型（向量化处理文档）和对话模型（检索增强 ）"""


# ============第一步===========全局的配置=========================

# 配置llama-index全局的嵌入模型：OpenAILikeEmbedding 表示用的是兼容 OpenAI 接口格式的嵌入模型
Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)
# 配置llama-index全局的llm：负责"思考和回答"的那个模型
Settings.llm = OpenAILike(
    model=os.getenv("MODEL1"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.3,  # 建议调小点：温度越高，模型的回答就越随机；温度越低，模型的回答就越确定
    context_window=1024 * 100,
    max_tokens=4096,
)
 
 # ======================文档加载=======================

documents = SimpleDirectoryReader(input_dir='../docs2').load_data()

"""
两段配置都通过 Settings 设成全局的,后面任何地方都能直接用，不用重复传参，但是需要将其导入到后续的代码文件中
"""