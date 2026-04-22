#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 实际需要 nest_asyncio 的场景.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/24 23:59
# @Desc    : AI大模型应用
# ============================================================================

# test_nested.py - 会报错
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