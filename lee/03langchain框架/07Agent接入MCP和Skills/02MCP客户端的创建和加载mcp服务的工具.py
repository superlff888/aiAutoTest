# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\07Agent接入MCP和Skills\02MCP客户端的创建和加载mcp服务的工具.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from langchain_mcp_adapters.client import MultiServerMCPClient

# 创建一个mcp客户端
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


# 获取mcp客户端中所有的工具
async def main():
    tools = await mcp_client.get_tools()
    print(tools)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
