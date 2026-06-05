# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\02用例生成+评审的代码rag_agent\models.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from langchain_openai.chat_models import ChatOpenAI


dotenv.load_dotenv(dotenv.find_dotenv())  # 从当前文件所在目录逐级向上搜索 .env 文件


# ============第一步===========全局的配置=========================

# 配置llama-index全局的嵌入模型
Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)
# 配置llama-index全局的llm
Settings.llm = OpenAILike(
    model=os.getenv("MODEL1"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.5,
    context_window=1024 * 100,
    max_tokens=4096,
)


# ===================定义langchian的模型对象===========
# 如果配置的API_KEY 和BASE_URL 使用的使用变量名 OPENAI_API_KEY 和 OPENAI_BASE_URL 在通过ChatOpenAI去初始化模型对象的时候，可以不传参数base_url和api_key
llm_model2 = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL_QWEN37"),
    temperature=0.5,
)

llm_model = ChatOpenAI(
    # base_url=os.getenv("MINIMAX_BASE_URL"),
    # api_key=os.getenv("MINIMAX_API_KEY"),
    model=os.getenv("OPENAI_MODEL_QWEN36"),
    temperature=0.5
)