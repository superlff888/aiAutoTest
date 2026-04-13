# @Author  : 木森
# @weixin: python771

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore

# 加载.env文件中的环境变量
dotenv.load_dotenv()
# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

# 创建mcp客户端
client = MultiServerMCPClient({
    "Playwright-Mcp": {
        # 确保你已经在本地 8000 端口启动 weather 工具服务
        "url": "http://127.0.0.1:8000/mcp",  # 工具服务地址
        "transport": "streamable_http",  # 使用支持流式传输的 HTTP 协议通信
    },
    # "wechat": {
    #     "command": "python",  # 启动工具使用的命令
    #     # 替换为你本地 math_server.py 文件的绝对路径
    #     "args": [r"G:\AI\上课代码\AI2502\08langgraph接入MCP\mcp_server.py"],
    #     "transport": "stdio",  # 使用标准输入输出协议与模型通信
    # },
    # 有多个mcp服务要接入，直接在上加配置即可
})


# 定义一个异步函数
async def main():
    """agent的入口函数"""
    # 获取工具列表
    tools = await client.get_tools()
    # 创建一个react型agent
    agent = create_react_agent(
        llm,
        tools=tools,
        store=InMemoryStore(),
        prompt="""请使用以下工具来帮助回答用户问题。"""
    )
    print("==================任务1=======================")
    response = await agent.ainvoke(
        input={"messages": [{"role": "user", "content": "请计算1+1"}]},
        stream_mode="messages"
    )
    print(response)
    print("==================任务2=======================")
    response = await agent.ainvoke(
        input={"messages": [{"role": "user", "content": "打开百度首页"}]},
        stream_mode="messages"
    )
    print(response)


if __name__ == '__main__':
    # 异步函数的入口需要使用asyncio模块中的run方法
    asyncio.run(main())
