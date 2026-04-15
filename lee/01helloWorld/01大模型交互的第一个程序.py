# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\01helloWorld\01大模型交互的第一个程序.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 21:44
# @UpdateTime  : 2026/04/15 22:05
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================



import os
import dotenv
from langchain_openai import ChatOpenAI


# 加载环境变量文件
dotenv.load_dotenv()


llm = ChatOpenAI(
    model = os.getenv("OPENAI_MODEL"),
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_BASE_URL")
    )

response = llm.invoke("你好")
print(response.content)

for chunk in llm.stream("你好，你能在测试领域做什么？"):
    print(chunk.content, end="")
