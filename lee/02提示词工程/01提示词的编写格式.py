# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\02提示词工程\01提示词的编写格式.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================

import os
import dotenv

dotenv.load_dotenv()

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI


llm = ChatOpenAI(
    model_name = os.getenv("OPENAI_MODEL"),
    base_url = os.getenv("OPENAI_BASE_URL"),
    api_key = os.getenv("OPENAI_API_KEY")
)


# 提示词1：字符串类型
input_prompt1 = "你好"
response = llm.invoke(input_prompt1)
print(response.content)

# 提示词2：列表类型，langchain为了兼容openai的api格式
input_prompt2 = [
    {"role":"system","content":"你是一名儿童医院专家"},
    {"role":"user","content":"2岁女宝22点30睡觉对身高影响大吗？"},
    {"role":"assistant","content":"2岁女宝22点30睡觉对身高影响大"}
]
response = llm.invoke(input_prompt2)
print(response.content)


input_prompt3 = [
    SystemMessage(content="你是一名儿童医院专家"),
    HumanMessage(content="晚睡对身高影响大吗？"),
    AIMessage(content="晚睡对身高影响大")
]
response = llm.stream(input_prompt3)
for item in response:
    print(item.content, end="")




