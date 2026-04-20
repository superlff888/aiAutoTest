#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 01异步函数的定义.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/16 20:11
# @Desc    : AI大模型应用
# ============================================================================
"""基于携程，实现并发"""

import asyncio

async def demo(name):
    """携程函数，即异步函数"""
    print(f"Hello {name}!")
    await asyncio.sleep(1)
    print(f"Hello {name} again!")
    await asyncio.sleep(5)
    print(f"Hello {name} last time!")

async def main1():
    """提前调度多个协程并发执行，包装协程为并发任务"""
    task1 = asyncio.create_task(demo("lee1"))
    task2 = asyncio.create_task(demo("lee2"))
    task3 = asyncio.create_task(demo("lee3"))
    await task1
    await task2
    await task3

# （推荐）批量创建协程任务
async def main2():
    """使用asyncio.gather()方法,批量创建协程任务,并发执行"""
    await asyncio.gather(demo("lee1"), demo("lee2"), demo("lee3"))

if __name__ == '__main__':
    g1 = asyncio.run(main1())
    print(g1)
    g2 = asyncio.run(main2())
    print(g2)


# 包装协程为并发任务
"""生活中的协程(异步)例子: 并发任务"""
import asyncio
import time

# 模拟三个耗时的任务
async def 煮饭():
    print("开始煮饭...")
    await asyncio.sleep(5)  # 煮饭要3分钟
    return "饭煮好了"


async def 炒菜():
    print("开始炒菜...")
    await asyncio.sleep(2)  # 炒菜要2分钟
    return "菜炒好了"


async def 烧汤():
    print("开始烧汤...")
    await asyncio.sleep(1)  # 烧汤要1分钟   可等待对象加await
    return "汤烧好了"


async def 做晚饭():
    start_time = time.time()

    # 同步方式（总耗时6分钟） -- 傻等
    # 饭 = await 煮饭()  # 等3分钟    在窗口A排队3分钟，期间什么也不干
    # 菜 = await 炒菜()  # 等2分钟    去窗口B排队2分钟
    # 汤 = await 烧汤()  # 等1分钟    最后去窗口C排队1分钟

    # 下面的每个任务都是等前一个完成才开始的！
    饭 = await asyncio.create_task(煮饭())  # 创建煮饭任务 → 立即等待它完成（3分钟）
    菜 = await asyncio.create_task(炒菜())  # 煮饭完成 → 创建炒菜任务 → 立即等待它完成（2分钟）
    汤 = await asyncio.create_task(烧汤())  # 炒菜完成 → 创建烧汤任务 → 立即等待它完成（1分钟）


    # # 异步方式（总耗时3分钟） ，包装协程为并发任务  --
    # 饭任务 = asyncio.create_task(煮饭())  # 朋友A去窗口A排队    可等待对象，创建一个协程任务
    # 菜任务 = asyncio.create_task(炒菜())  # 朋友B去窗口B排队    可等待对象，创建一个协程任务
    # 汤任务 = asyncio.create_task(烧汤())  # 你自己去窗口C排队    可等待对象，创建一个协程任务
    # # 同时进行，等最慢的那个完成
    # 饭 = await 饭任务  # 朋友A去窗口A排队，期间什么也不干
    # 菜 = await 菜任务  # 朋友B去窗口B排队，期间什么也不干
    # 汤 = await 汤任务  # 你自己去窗口C排队，期间什么也不干
    # print(f"{饭}, {菜}, {汤}")
    # print(f"总耗时: {time.time() - start_time:.1f}秒钟")


if __name__ == '__main__':
    # 运行
    asyncio.run(做晚饭())

"""
总结：
await是"我等"
create_task是"你去做" 
想要快，就要让多个任务同时开始做，然后一起等结果（等最后一个子协程函数完成）
"""