#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------
# @File    : leeMCPServer.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/20 21:29
# @Desc    : AI大模型应用开发理论基础
# ========================================================

import os
import dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

dotenv.load_dotenv()
llm=ChatOpenAI(
    model_name=os.getenv("MODEL_NAME"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

# 创建提示词模板，提示词模板中包含系统指令、消息占位符、当前用户带输入问题变量
prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessage("你是一个乐于助人的旅行助手，用中文回答用户问题").content,
        MessagesPlaceholder(variable_name="chat_history"),
        HumanMessage("{user_input}").content
    ]
)

chat_history = [
    HumanMessage(content="我想去北京旅游"),  # 用户第一条消息
    AIMessage(content="北京是个很棒的选择！您对什么景点感兴趣？"),  # AI回复
    HumanMessage(content="我想参观故宫和长城")  # 用户第二条消息
]

current_question = HumanMessage("这两个景点需要提前多久预订门票？").content

chain = prompt | llm
response = chain.invoke({"chat_history": chat_history,"user_input": current_question})

print(f"大模型回复：\n{response.content}")

chat_history.extend([
    HumanMessage(content=current_question),
    AIMessage(content=response.content)
])

next_question = HumanMessage("故宫附近有什么推荐的酒店？").content

# 用户每次提问，均会执行该方法
next_response = chain.invoke({
    "chat_history": chat_history,
    "user_input": next_question
})

print(f"大模型下一次回复：\n{next_response.content}")


