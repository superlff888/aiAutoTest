#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : AIBasic.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/20 09:42
# @Desc    : AI大模型应用开发理论基础
# ========================================================

from langgraph.store.memory import InMemoryStore
import dotenv
import os
from langchain_openai import ChatOpenAI

# 加载.env文件中的环境变量
dotenv.load_dotenv()
# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)
# 长期记忆(内存存储)
memory = InMemoryStore()

# ======================基于记忆实现一个聊天机器人======================

"""
先把历史对话内容存储起来，然后在新的对话内容中加入历史对话内容(大模型本身是没有记忆功能)
"""
prompt = "请记住我是的名字是木森，今年18岁"
memory.put(namespace=("musen01", "1234uuid"),
           key="musen01",
           value={"role": "user", "content": prompt}
           )

response = llm.invoke(prompt)
print(response.content)

# 把AI的回复存到记忆中
memory.put(namespace=("musen01", "1234uuid"),
           key="musen01",
           value={"role": "ai", "content": response.content}  # 把AI的回复response.content存到记忆中
           )

print("==========第二次对话===========================")

prompt2 = "我是谁？"
# ==============获取记忆中的内容，拼接到上下文中======================
old_memory = memory.get(namespace=("musen01", "1234uuid"), key="musen01")
print(f"历史记忆的内容为：{old_memory}")

new_prompt = [
    old_memory.value,
    {"role": "user", "content": prompt2}
]
response2 = llm.stream(new_prompt)
for chunk in response2:
    print(chunk.content, end="")


