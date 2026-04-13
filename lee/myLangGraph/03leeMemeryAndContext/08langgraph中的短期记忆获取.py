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

import os

from typing import Annotated

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
import dotenv

"""
想象一下，你让一个助手（Agent）帮你规划一次旅行:

1.开始聊天：你告诉助手：“我想去上海玩。”
2.助手需要记笔记：助手拿出一个笔记本（AgentState），在第一页写下：“用户目标：上海旅游”。
3.你接着问：“有哪里好玩？”
4.助手查阅笔记：助手看了一眼笔记本，知道目标是“上海旅游”，然后它去查资料，找到“外滩、迪士尼、博物馆”等，并把这些写进笔记本的“景点列表”这一栏。
5.你又问：“预算5000元够吗？”
6.助手再次查阅笔记：助手看到笔记本上的“景点列表”，估算一下花费，然后把“预算：5000元（可能足够）”也记录下来。
7.最终回复：助手根据笔记本上所有记录的信息（目的地、景点、预算），给你生成一个完整的旅行方案。

在这个例子里，如果没有这个笔记本（AgentState），助手（Agent）每次回答你的问题时，都会忘记之前的对话内容。你每次都得重复说“我要去上海”、“我的预算是5000”，整个对话就无法连贯地进行下去。
"""




# 加载.env文件中的环境变量
dotenv.load_dotenv()


# 定义agent的state，即短期记忆
class CustomState(AgentState):
    user_id: str

# CustomState 是你自定义的状态类型，定义了agent可以访问哪些状态信息
@tool
def get_user_info(state: Annotated[CustomState, InjectedState]) -> str:  # InjectedState 是一个特殊标记，告诉LangGraph框架"请自动注入当前的state状态"
    """获取用户信息"""
    # 获取短期记忆(状态)--->agent中使用AgentState来管理
    # 获取状态中的user_id
    user_id = state["user_id"]

    return "用户是lee" if user_id == "user_123" else "用户是李四"


# 创建一个React Agent，如果定义的state参数（state_schema），那么在使用的时候，就可以在input输入内容中传递state中定义的字段
agent = create_react_agent(
    model=ChatOpenAI(
        model=os.getenv('MODEL'),
        base_url=os.getenv('BASE_URL'),
        api_key=os.getenv('API_KEY'),
    ),
    tools=[get_user_info],
    state_schema=CustomState  # 定义状态类型，state中定义的参数，可以在input中传入
)

response = agent.stream({
    # messages是传入的 用户提示词
    "messages": [{"role": "user", "content": "我是谁"}],
    # state中定义的参数，可以在input中传入
    "user_id": "user_122"
    },
    stream_mode="messages"
)
for chunk, item in response:
    print(chunk.content, end="")
