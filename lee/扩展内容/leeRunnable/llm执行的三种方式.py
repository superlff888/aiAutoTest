#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeMCPServer.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/24 21:21
# @Desc    : 三种执行方式
# ========================================================

import dotenv
import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

prompt = PromptTemplate(
    input_variables=["name"],
    template="""
    我的名字叫{name}，年龄是18，性别是男
    请帮我把个人信息转换为json格式输出，
    """,
)
print("================1=======================")

chain = prompt | llm
# res = chain.invoke({"name": "木森"})
# print(res.content)
# print("================2=======================")
#
# res = chain.stream({"name": "木森2"})
# for item in res:
#     print(item.content, end="", flush=True)

print("================3=====================批量执行==")
res = chain.batch([{"name": "木森3"}, {"name": "木森4"}])  # 入参为列表
print(res)

# 所以的Runnable对象都支持上面的三种执行方式
