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

from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.tools import tool, InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import InjectedState, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
import dotenv

# 加载.env文件中的环境变量
dotenv.load_dotenv()


# 定义agent的state
class CustomState(AgentState):
    user_name: str


@tool
def get_user_info(state: Annotated[CustomState, InjectedState]) -> str:
    """获取用户信息"""

    # 获取短期记忆(状态)--->agent中使用AgentState来管理
    # 获取状态中的user_id
    return state["user_name"]

# 更新短期记忆AgentState中的信息
@tool
def update_user_info(
        tool_call_id: Annotated[str, InjectedToolCallId],  # 工具状态的id
        state: Annotated[CustomState, InjectedState]):
    """更新用户信息"""
    print("\n'更新用户信息工具'的输入：", state["user_name"])
    # 更新State状态，使用langgraph提供的Command
    return Command(update={
        "user_name": "李四",
        "messages": [
            ToolMessage(
                "用户信息更新成功\n",  # 提示信息
                tool_call_id=tool_call_id
            )
        ]
    })


# 创建一个React Agent，如果定义的state参数，那么在使用的时候，就可以在input输出内容中传递state中定义的字段
agent = create_react_agent(
    model=ChatOpenAI(
        model=os.getenv('MODEL_NAME'),
        base_url=os.getenv('BASE_URL'),
        api_key=os.getenv('API_KEY'),
    ),
    tools=[get_user_info, update_user_info],
    state_schema=CustomState
)

response = agent.stream({
    # messages是传入用户的提示词
    "messages": [{"role": "user", "content": "先获取用户信息，然后更新用户信息，再获取用户信息"}],
    # state中定义的参数，可以在input中传入
    "user_name": "02lee"
    },
    stream_mode="messages"
)
for chunk, item in response:
    print(chunk.content, end="")
