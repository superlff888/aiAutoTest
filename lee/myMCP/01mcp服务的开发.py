
from mcp.server.fastmcp import FastMCP
from playwright.sync_api import sync_playwright

# 实例化一个MCP对象:服务的名称
mcp = FastMCP("Playwright-Mcp")


# ===============开发mcp服务的工具函数======================
@mcp.tool()
def add(a: int, b: int) -> int:
    """将两个数字相加"""
    print("正在调用工具: add")
    # 里面实现工具的具体逻辑
    return a + b

@mcp.tool()
def get_weather(city: str) -> str:
    """获取城市天气。"""
    print("正在调用工具: get_weather")
    # 这通常会调用天气API
    return f"{city}的天气: 晴,气温22度"


@mcp.tool()
def open_url(url: str) -> str:
    """打开一个网页地址,获取网页源码"""
    # 使用Playwright打开网页
    print("正在调用工具: open_url")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url)
    return f"已打开URL: {url}"


if __name__ == "__main__":
    # 使用stdio模型通信运行mcp服务
    # mcp.run(transport="stdio")
    # 使用http模型通信运行mcp服务
    mcp.run(transport="streamable-http")
