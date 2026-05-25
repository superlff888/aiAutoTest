# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\demo.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


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


