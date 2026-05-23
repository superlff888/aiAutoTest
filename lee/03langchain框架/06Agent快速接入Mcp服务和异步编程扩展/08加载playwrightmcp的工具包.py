# @Author  : 木森
# @weixin: python771

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