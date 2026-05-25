# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\扩展内容\leeRunnable\leeRunnableBranch.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda, RunnableBranch, RunnableMap
from langchain_core.prompts import PromptTemplate

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# dpv3大模型
llm_V3 = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V3",
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)
# dpR1大模型
llm_R1 = ChatOpenAI(
    model="deepseek-ai/DeepSeek-R1",
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)
# QWen3大模型
llm_Qwen3 = ChatOpenAI(
    model="Qwen/Qwen3-30B-A3B",
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

# 对于用户不同的输出使用不同的大模型去进行处理
prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""{user_input}"""
)

llm = RunnableBranch(
    (
        lambda x: str(x).startswith("Qwen"),
        llm_Qwen3,
    ),
    (
        RunnableLambda(lambda x: x.text.startswith("dpR1")),
        llm_R1,
    ),
    (
        RunnableLambda(lambda x: x.text.startswith("dpv3")),
        llm_V3,
    ),
    llm_V3,
)

chain = prompt | llm
response = chain.invoke({"user_input": "Qwen分析今天上海的天气"})
print(response.content)
