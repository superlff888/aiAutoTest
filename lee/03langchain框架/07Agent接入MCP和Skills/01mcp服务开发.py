# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\07Agent接入MCP和Skills\01mcp服务开发.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


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




