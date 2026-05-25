# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\06Agent快速接入Mcp服务和异步编程扩展\08加载playwrightmcp的工具包.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from langchain_mcp_adapters.client import MultiServerMCPClient

async def load_mcp_tools():
    """加载mcp服务中的工具"""
    # 创建一个mcp客户端
    mcp_client = MultiServerMCPClient(
        {
            "playwright": {
                "command": "npx",
                "args": [
                    "@playwright/mcp@latest"
                ],
                "transport": "stdio",
            }
        }
    )
    # 加载mcp服务中所有的工具
    tools = await mcp_client.get_tools()
    for tool in tools:
        print(tool.name)

if __name__ == '__main__':
    import asyncio
    asyncio.run(load_mcp_tools())