# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\扩展内容\leeRunnable\leeRunnableMap.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import dotenv
import os

from langchain_core.output_parsers import StrOutputParser
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
    model="Tongyi-Zhiwen/QwenLong-L1-32B",
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

# 对于用户不同的输出使用不同的大模型去进行处理
prompt = PromptTemplate(
    input_variables=["user_input"],
    template="""{user_input}"""
)

parser = StrOutputParser()
# 构建多个调用链
chain1 = prompt | llm_V3 | parser
chain2 = prompt | llm_R1 | parser
chain3 = prompt | llm_Qwen3 | parser


# 使用并行执行的模式,返回一个字典
parallel_chain = RunnableMap({
    "V3": chain1,
    "R1": chain2,
    "Qwen3": chain3
})

# 执行调用链
response = parallel_chain.invoke({"user_input": "今天上海的天气如何？"})
print("模型1：\n", response.get("V3"))
print("模型2:\n", response.get("R1"))
print("模型3：\n", response.get("Qwen3"))

