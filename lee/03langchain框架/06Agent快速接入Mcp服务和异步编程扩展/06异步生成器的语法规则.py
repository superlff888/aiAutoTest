# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\06Agent快速接入Mcp服务和异步编程扩展\06异步生成器的语法规则.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import asyncio
from unittest import main

# 定义异步生成器函数
async def demo2(max):
    i = 0
    while True:
        i += 1
        if i <= max:
            yield i
        else:
            break


async def mian():
    obj = demo2(10)
    print("obj:", obj)
    # 遍历异步生成器的语法
    async for i in obj:
        print(i)


if __name__ == '__main__':
    asyncio.run(mian())
