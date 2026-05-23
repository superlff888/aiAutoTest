# @Author  : 木森
# @weixin: python771
#
"""
一、异步函数(协程函数)
    1、通过async def 定义协程函数，
    2、调用的时候不会执行执行,会直接返回一个协程对象
    3、执行协程需要使用：asyncio.run(协程)

asyncio:python异步程序运行的核心库


二、 关于关键字await：
    1、await只能在async定义的异步函数中使用
    2、await的作用是等待 await后面的任务执行完毕
    3、await后面只能写可等待对象(协程、异步任务，asyncio.sleep)


三、协程的调度执行机制：
    事件循环

执行协程程序：创建一个事件循环
    伪代码：
    tasks = [异步执行的任务1，异步执行的任务2，异步执行的任务3]
    for t in  tasks:
        执行任务t，当执行遇到await的，将异步函数挂起(暂停)，再把这个没执行完的异步函数放到tasks的尾部

"""
import asyncio


async def demo():
    print("88888888888-1")
    await asyncio.sleep(3)
    print("88888888888-2")


async def demo2():
    print("111111111111111-1")
    await asyncio.sleep(2)
    print("111111111111111-2")


async def main():
    # 将协程对象封装成task对象
    task1 = asyncio.create_task(demo())
    # 将协程对象封装成task对象
    task2 = asyncio.create_task(demo2())
    await task1
    await task2

async def main2():
    # 将协程对象封装成task对象
    await asyncio.gather(demo(), demo2())

"""


"""

if __name__ == '__main__':
    asyncio.run(main2())



