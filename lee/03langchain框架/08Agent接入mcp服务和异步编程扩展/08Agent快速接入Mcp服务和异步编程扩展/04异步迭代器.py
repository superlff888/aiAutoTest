# @Author  : 木森
# @weixin: python771
"""

迭代器：
    1、底层实现：实现了__iter__方法 和__next__方法的对象叫做迭代器对象
    2、python内置的可迭代对象，都可以使用内置函数iter()，将可迭代对象转换为迭代器对象

    内置函数：
        iter(对象)  --->对象.__iter__()
        next(对象)  ---> 对象的__next__()

    for循环可以直接遍历

异步迭代器：
    1、底层实现：实现了__aiter__方法 和__anext__方法的对象叫做迭代器对象
    2、python内置的可迭代对象，都可以使用内置函数iter()，将可迭代对象转换为迭代器对象

    内置函数：
        aiter(对象)  --->对象.__aiter__()
        anext(对象)  ---> 对象的__anext__()

    async for来遍历异步迭代器(注意点：async for只能在异步函数中写(async def))

"""

from typing import Iterable,Iterator,Generator,AsyncIterable,AsyncIterator,AsyncGenerator


import asyncio

class AsyncCounter:
    def __init__(self, max):
        self.count = 0
        self.max = max

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.count >= self.max:
            raise StopAsyncIteration
        self.count += 1
        return self.count

# 关注下面一步迭代器的使用语法
async def main():
    obj = AsyncCounter(3)
    async for i in obj:
        print(i)


if __name__ == '__main__':
    asyncio.run(main())

