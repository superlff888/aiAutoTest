# @Author  : 木森
# @weixin: python771
"""
上下文管理对象：
    核心关键字：with
    底层的核心实现方法：__enter__() 和 __exit__()构成了对象的上下文管理协议

异步上下文管理对象：
    核心关键字：async with
    底层的核心实现方法： aysnc def __aenter__() 和 aysnc def __aexit__()构成了对象的上下文管理协议
    async with 只能在async def定义的异步函数中使用


异步编程语法总结：
核心库：asyncio
关键字：async  、await 、 yield
语法 :
    async def
    async for
    async with


"""
import asyncio


# f = open("01python异步编程知识补充.py", "r")

# with open("01python异步编程知识补充.py", "r") as f:
#     print(f.read())


# class MyContext:
#     def __enter__(self):
#         print("进入上下文")
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         print("exc_type:", exc_type)
#         print("exc_val:", exc_val)
#         print("exc_tb:", exc_tb)
#         print("退出上下文，释放资源")

# with MyContext() as ctx:
#     print("处理中...")
#     print(a)
# print("=========end================")


# print("=================================")
class MyContext2:
    async def __aenter__(self):
        print("进入上下文")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("exc_type:", exc_type)
        print("exc_val:", exc_val)
        print("exc_tb:", exc_tb)
        print("退出上下文，释放资源")





async def main():
    async with MyContext2() as ctx:
        print("=========start================")
        print(ctx)
        print("处理中...")


if __name__ == '__main__':
    asyncio.run(main())
