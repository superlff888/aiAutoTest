# @Author  : 木森
# @weixin: python771
from mcp.server.fastmcp import FastMCP
import requests

# 初始化mcp服务
mcp = FastMCP("http-mcp")


@mcp.tool("get_requests", description="发送get请求的工具")
def get_requests(url: str, request):
    """
    获取请求参数
    :param request:
    :return:
    """
    response = requests.get(url)
    if response.status_code == 200:
        return response.content
    else:
        return "请求失败"





# 在里面可以封装N个工具
if __name__ == '__main__':
    # mcp.run(transport="stdio")
    mcp.run(transport="streamable-http")




