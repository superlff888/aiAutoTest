#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 在工作流中接入MCP.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/9/1 08:34
# @Desc    : AI大模型应用
# ============================================================================

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
import dotenv
import os

# 加载.env文件中的环境变量
dotenv.load_dotenv()


class MCPGraphAgent:
    def __init__(self, mcp_config: dict):
        """
        初始化MCP Graph Agent

        Args:
            mcp_config: MCP客户端配置
        """
        # 初始化语言模型
        self.model = ChatOpenAI(
            model=os.getenv('MODEL_NAME'),
            base_url=os.getenv('BASE_URL'),
            api_key=os.getenv('API_KEY'),
        )

        # 配置并启动多个 MCP 工具服务客户端
        self.client = MultiServerMCPClient(mcp_config)
        self.tools = None
        self.model_with_tools = None
        self.tool_node = None
        self.graph = None

    async def initialize(self):
        """
        初始化agent，获取工具并构建图结构
        """
        # 异步获取工具列表（通过 MCP 协议从服务端动态获取工具定义）
        self.tools = await self.client.get_tools()
        print("工具列表：", self.tools)

        # 将工具绑定到模型，使其具备调用工具的能力
        self.model_with_tools = self.model.bind_tools(self.tools)

        # 创建 ToolNode，用于根据模型生成的 tool_calls 实际调用工具
        self.tool_node = ToolNode(self.tools)

        # 构建状态图（StateGraph）
        builder = StateGraph(MessagesState)

        # 添加节点：模型调用节点
        builder.add_node("call_model", self._call_model)

        # 添加节点：工具调用节点（通过 MCP 执行工具）
        builder.add_node("tools", self.tool_node)

        # 添加边：从起始节点 START 跳转到模型调用节点
        builder.add_edge(START, "call_model")

        # 添加条件边：根据模型输出决定下一步跳转到工具调用或结束
        builder.add_conditional_edges(
            "call_model",
            self._should_continue,
        )

        # 添加边：工具调用完成后继续调用模型（形成循环，直到无需再调用工具）
        builder.add_edge("tools", "call_model")

        # 编译图结构
        self.graph = builder.compile()

    def _should_continue(self, state: MessagesState):
        """
        条件判断函数：判断模型响应是否包含 tool_calls（即是否需要调用工具）
        """
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tools"  # 如果包含工具调用请求，跳转到 tools 节点执行
        return END  # 否则流程结束

    async def _call_model(self, state: MessagesState):
        """
        模型调用函数：向模型发送历史消息并获取响应
        """
        messages = state["messages"]
        response = await self.model_with_tools.ainvoke(messages)
        return {"messages": [response]}

    async def query(self, content: str) -> dict:
        """
        执行查询

        Args:
            content: 查询内容

        Returns:
            查询结果
        """
        if not self.graph:
            raise RuntimeError("Agent未初始化，请先调用initialize()方法")

        response = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": content}]}
        )
        return response


# 使用示例
async def main():
    # MCP配置
    mcp_config = {
        "math": {
            "command": "python",
            "args": [r"G:\AI\上课代码\AI2502\08备课\mcp_server.py"],
            "transport": "stdio",
        },
        "weather": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    }

    # 创建并初始化agent
    agent = MCPGraphAgent(mcp_config)
    await agent.initialize()

    # 测试图流程：提问数学问题，模型应识别并调用 math 工具
    math_response = await agent.query("计算一下 (3 + 5) x 12的结果？")
    print("math_response:", math_response)

    # 测试图流程：提问天气问题，模型应识别并调用 weather 工具
    weather_response = await agent.query("北京今天的天气怎么样")
    print("weather_response:", weather_response)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
