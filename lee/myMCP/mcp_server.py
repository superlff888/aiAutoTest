# @Author  : 木森
# @weixin: python771

from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright

# 实例化一个MCP对象:服务的名称
mcp = FastMCP("wechat")


# ===============开发mcp服务的工具函数======================
@mcp.tool()
def open_wechat(a: int, b: int) -> int:
    """
    启动微信
    :param a:
    :param b:
    :return:
    """
    print("正在调用工具: add")
    # 里面实现工具的具体逻辑
    return a + b


@mcp.tool()
def send_message(city: str) -> str:
    """
    微信好友发生消息
    :param city:
    :return:
    """
    print("正在调用工具: get_weather")
    # 这通常会调用天气API
    return f"{city}的天气: 晴，气温22度"



if __name__ == "__main__":
    # 使用stdio模型通信运行mcp服务
    mcp.run(transport="stdio")
    # 使用http模型通信运行mcp服务
    # mcp.run(transport="streamable-http")
