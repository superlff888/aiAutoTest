# @Author  : 木森
# @weixin: python771
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
