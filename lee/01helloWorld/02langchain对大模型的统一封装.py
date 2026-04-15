# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\01helloWorld\02langchain对大模型的统一封装.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:03
# @UpdateTime  : 2026/04/15 22:05
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from langchain.chat_models import init_chat_model

# 加载环境变量文件
dotenv.load_dotenv()


llm = init_chat_model(
    model = os.getenv("OPENAI_MODEL"),
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_BASE_URL"),
    model_provider = "openai"
    )

for chunk in llm.stream("你好"):
    print(chunk.content, end="")




