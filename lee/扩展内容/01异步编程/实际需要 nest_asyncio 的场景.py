# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\扩展内容\01异步编程\实际需要 nest_asyncio 的场景.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import asyncio
import nest_asyncio

nest_asyncio.apply()  # ✅ 打补丁后就可以运行了
async def 内部任务():
    await asyncio.sleep(1)
    return "结果"

async def 中间任务():
    # 这里想重新启动事件循环
    result = asyncio.run(内部任务())  # ❌ nest_asyncio.apply() 若不打补丁，报错！不允许嵌套运行
    return result

if __name__ == '__main__':
    r = asyncio.run(中间任务())
    print(r)