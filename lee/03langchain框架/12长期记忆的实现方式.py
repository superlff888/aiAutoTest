#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : demo.py
# @Project : musen
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/4/25 15:19
# @Desc    : AI大模型应用
# ============================================================================


from dataclasses import dataclass
import os
from langchain.agents import create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain.tools import ToolRuntime, tool
from langchain_openai import ChatOpenAI
from langgraph.store.mysql import MySQLStore  # type: ignore[import-not-found]
from typing_extensions import TypedDict
from utils.database_uri import get_db_uri

"""
长期记忆的概念：持久化记住并保存的内容
    对话的内容过程，放在短期记忆中，不需要持久化存储
    一些重要的规则和规范才需要保存到长期记忆中

记忆的操作：
    1、记忆读取
    2、记忆写入：

:: for example:
    runtime.store.put(
    ("users",),        # 组名（namespace）
    "user_123",        # key（用户ID）
    {"name": "John"}   # value（要存的数据）
    )


"""


@dataclass
class Context:
    user_id: str


class UserInfo(TypedDict):
    name: str


minimax27 = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    temperature=0.9
)


@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save the current user's name to long-term memory."""
    assert runtime.store is not None
    runtime.store.put(("users",), runtime.context.user_id, dict(user_info))
    return "Successfully saved user info."


@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Look up user info."""
    assert runtime.store is not None # 判断存储是否注入agent
    user_info = runtime.store.get(("users",), runtime.context.user_id)
    return str(user_info) if user_info else "Unknown user"


# MySQL 连接串
DB_URI = get_db_uri()
if not DB_URI:
    raise ValueError("DB_URI is not configured")

# 连接数据库
with MySQLStore.from_conn_string(DB_URI) as store:
    store.setup()  # ✅ 自动建表
    agent = create_agent(
        minimax27,
        [save_user_info, get_user_info],
        store=store,  # 把存储注入 Agent
        context_schema=Context,  # 不可变上下文结构（agent每次调用时的附加信息）
    )

    result = agent.invoke(
        {"messages": [
            SystemMessage(content="你是一个助手。如果用户告诉你他的名字，请使用 save_user_info 工具保存下来。"),
            HumanMessage(content="我是lee"),
        ]},
        context=Context(user_id="user_123"),
    )

    print(result["messages"][-1].content)

