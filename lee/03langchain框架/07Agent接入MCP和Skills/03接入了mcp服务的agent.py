# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\07Agent接入MCP和Skills\03接入了mcp服务的agent.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import asyncio
import os
import dotenv
from dataclasses import dataclass

from anyio.lowlevel import checkpoint
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

dotenv.load_dotenv()


class MusenAgent:

    async def loads_mcp_tools(self):
        """加载mcp服务中的工具"""
        mcp_client = MultiServerMCPClient(
            {
                # 配置mcp服务
                "http-mcp": {
                    "url": "http://localhost:8000/mcp",
                    "transport": "streamable-http"
                },
                # "http-mcp": {
                #     "command": "python",
                #     "args": ["01mcp服务开发.py"],
                #     "transport": "stdio"
                # },
                # 配置一个playwright mcp服务
                "playwright": {
                    "command": "npx",
                    "args": [
                        "@playwright/mcp@latest"
                    ],
                    "transport": "stdio",
                }
            }
        )
        tools = await mcp_client.get_tools()
        return tools

    def __init__(self, user_id):
        self.model = ChatOpenAI(
            model=os.getenv("MODEL"),
        )
        self.user_id = user_id

    async def create_agent(self):
        """创建agent"""
        return create_agent(
            model=self.model,
            tools=await self.loads_mcp_tools(),
            # 启动短期记忆
            checkpointer=InMemorySaver(),
        )

    async def run(self):
        """运行agent"""
        agent = await self.create_agent()
        while True:
            user = input(f"\n🔥用户【{self.user_id}】：")
            # 组装用户消息
            messages = [
                HumanMessage(content=user)
            ]
            # 调用agent，也需要使用异步的方式去调用
            response = agent.astream({
                "messages": messages
            },
                checkpoint=InMemorySaver(),
                config={"configurable": {"thread_id": self.user_id}},
                stream_mode=['updates', 'messages', 'custom'],
                version="v2"
            )
            async for chunk in response:
                if chunk['type'] == "custom":
                    print("✅自定义输出：", chunk['data'])
                elif chunk['type'] == "messages":
                    print(chunk['data'][0].content, end='')


if __name__ == '__main__':
    agent = MusenAgent("musen_001")
    asyncio.run(agent.run())
