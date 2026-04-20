#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 迭代器与迭代器和异步迭代器.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/16 21:11
# @Desc    : AI大模型应用
# ============================================================================
import asyncio
"""
迭代器的核心比喻：待办清单（可迭代对象） vs. 带指针的阅读器（迭代器）
"""


# res = iter([11,22,33])  # 创建一个迭代器对象
# print(next(res))
# print(next(res))
# print(next(res))

"""
● 迭代器对象需要实现：
  ○ __iter__() → 返回迭代器自身
  ○ __next__() → 每次迭代返回一个值，结束时抛出 StopIteration
● 可迭代对象需要实现：
  ○ __next__() → 每次迭代返回一个值或None
"""

# 定义一个迭代器类
class SyncCounter:
    def __init__(self, max=3):
        self.count = 0
        self.max = max

    def __iter__(self):
        return self

    def __next__(self):
        if self.count >= self.max:
            raise StopIteration
        self.count += 1
        return self.count


# # 1. 通过for循环便利
# for num in SyncCounter(3):
#     print(num)

# 2. 通过next()方法，获取下一个值
items = SyncCounter()  # 创建一个iterable可迭代对象
# res = iter(SyncCounter())  # iter()相当于SyncCounter()。__iter__ ,创建一个iter迭代器对象
print(next(items))  # 输出: 1  # 有了迭代器，你就用 next()函数来指挥迭代器工作
print(next(items))  # 输出: 2  # 有了迭代器，你就用 next()函数来指挥迭代器工作
print(next(items))  # 输出: 3  # 有了迭代器，你就用 next()函数来指挥迭代器工作


"""
● 异步迭代器对象需要实现：
  ○ __aiter__() → 返回异步迭代器对象（一般为 self）
  ○ __anext__() →  使用 await 返回下一个值；结束时抛出 StopAsyncIteration
● 异步可迭代对象需要实现：
  ○ __anext__() → 每使用 await 返回下一个值或None
"""

class AsyncCounter:
    def __init__(self, max):
        self.count = 0
        self.max = max

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.count >= self.max:
            raise StopAsyncIteration
        await asyncio.sleep(1)
        self.count += 1
        return self.count

async def main():
    async for i in AsyncCounter(3):
        print(i)

asyncio.run(main())


"""
LangChain中异步迭代器的应用
.astream()方法执行的返回就是异步迭代器
 ● 当你运行一个多轮对话、决策链、或 Agent 图谱时，可以通过 .astream() 以“事件流”的形式异步获取每个节点的中间状态或输出。
"""

import dotenv
import os
from langchain_openai import ChatOpenAI
import asyncio
from langchain_core.messages import HumanMessage

dotenv.load_dotenv()

# 创建一个支持流式的LLM
llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    # streaming=True
)

async def stream_response():
    # 创建异步迭代器
    stream = llm.astream("用100字介绍太阳系")
    # 异步迭代：LLM一边生成，我们一边打印
    async for chunk in stream: # 迭代器可以被next(),也可以for循环
        print(chunk.content, end="", flush=True)  # 逐词显示，像打字机一样


if __name__ == '__main__':
    # 运行
    asyncio.run(stream_response())