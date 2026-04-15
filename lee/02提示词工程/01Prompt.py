# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\basicPromptTemplate\01Prompt.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/14 01:05
# @UpdateTime  : 2026/04/14 01:25
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================
# !/usr/bin/env python3,
# # -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\basicPromptTemplate\01Prompt.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/12 15:30
# @UpdateTime  : 2026/04/13 13:35
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import dotenv
import os
from langchain_openai import ChatOpenAI


dotenv.load_dotenv()
llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME_QWEN3"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

messages = [
    {"role": "system", "content": "你是一名儿童医院专家"},
    {"role": "user", "content": "2岁女宝22点30睡觉对身高影响大吗？"},
]

response = llm.stream(messages)

for item in response:
    print(item.content, end="")
