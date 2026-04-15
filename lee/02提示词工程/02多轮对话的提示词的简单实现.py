# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\02提示词工程\02多轮对话的提示词的简单实现.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/14 01:05
# @UpdateTime  : 2026/04/15 22:44
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================

import os
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# 加载环境变量
dotenv.load_dotenv()

# 创建模型实例
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)

messages = [
    SystemMessage(content="你是一名资深的保险经纪人")
]

print("==============================第一轮对话中……=============================\n")

messages.append(HumanMessage(content="你好"))

AI_MESSAGE = ''
response = llm.stream(messages)
for item in response:
    print(f"第一轮对话内容：\n{item.content}", end="")
    AI_MESSAGE += item.content + "\n"

messages.append(AIMessage(content=AI_MESSAGE))

print("==============================第二轮对话中……=============================\n")

messages.append(HumanMessage(content="我家2岁女宝经常经常生病，近半年得了两次急性气管炎，帮我推荐一个保险方案"))

response = llm.stream(messages)
print("第二轮对话内容：")
for item in response:
    print(f"{item.content}", end="")
    AI_MESSAGE += item.content + "\n"

messages.append(AIMessage(content=AI_MESSAGE))

print("==============================第三轮对话中……=============================\n")

messages.append(HumanMessage(content="我们家小孩之前就得了两次急性气管炎，其他疾病没有"))

response = llm.stream(messages)
print("第三轮对话内容：")
for item in response:
    print(f"{item.content}", end="")
    AI_MESSAGE += item.content + "\n"

messages.append(AIMessage(content=AI_MESSAGE))

print("==============================第四轮对话中……=============================\n")
messages.append(HumanMessage(content="宝有办理城乡居民医保（少儿医保），预算在1000元左右"))
response = llm.stream(messages)
print("第四轮对话内容：")
for item in response:
    print(f"{item.content}", end="")
    AI_MESSAGE += item.content + "\n"


"""
AI大模型：
    用户的问题，去回答内容：
    给大模型的提示词可以是很多条内容
    最后一条是用户本次需要解决的问题，最后一条之前的可以把它叫做上下文(回答这个问题的前提背景)
    
保存所有对话记录的messages，就是我们所说的大模型上下文窗口(目前国内的顶尖模型上下文窗口都在200k以上)
200k = 200*1024 个token


如果持续对话，把所有的消息全部放在message中，时间一长就会导致message中的内容，超出了大模型能处理的最大上下文窗口限制。

    当上下文超过了大模型的最大处理值，需要去把一些不那么重要的记录给清除，才能够继续调用大模型完成后续的任务
    
    上下文管理工程(记忆处理)：
        1、做摘要提取（从对话记录中把重要的信息提取出来保存到永久记忆中--文件或者数据库做持久化存储）

"""

