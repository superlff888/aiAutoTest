# @Author  : 木森
# @weixin: python771
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
