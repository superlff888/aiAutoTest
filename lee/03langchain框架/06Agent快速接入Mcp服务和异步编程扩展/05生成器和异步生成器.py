# @Author  : 木森
# @weixin: python771

"""
生成器是一种特殊的迭代器，可以让程序员快速去创建迭代器

生成器的创建方式：
    1、方式一：生成器表达式
        generator_obj = (i for i in range(100000))

    2、生成器函数：函数中 使用了yield这个关键字的函数叫做生成器函数
        def func():
            yield

        特点：
            1、调用的时候不会直接执行，会返回一个生成器对象
            2、当遍历(迭代)生成器函数的时候，会执行生成器函数内部的代码
                每迭代一次，会执行到yield这个关键字的地方暂停，并且把yield后面的值返回(生成)出去


后续要实现sse服务的时候，会用到生成器函数


1、生成器(迭代器)和普通的列表存储数据有什么区别？
    当数据量大的时候，可以显著的节约内存开销，列表里面所有的数据都是存储在内存中的，而生成器里面只保存数据生成的规则，用一条生成一条，几乎不占用内存
"""


# 列表推导式
# li  = [i for i in range(100000000)]
# print("li:", li)

# generator_obj = (i for i in range(100000000))
# print("generator_obj:", generator_obj)
# input()


# def demo():
#     print("============1===============")
#     yield 1111
#     print("============2===============")
#     yield 2222
#     print("============3===============")
#     yield 3333
#     print("============4===============")
#     yield 4444
#     print("============5===============")
#     yield 5555
#     print("============6===============")
# if __name__ == '__main__':
#     g_obj = demo()
#     print("g_obj:", g_obj)
#     print(next(g_obj))
#     print(next(g_obj))
#     for i in g_obj:
#         print(i)

def demo2(max):
    i = 0
    while True:
        i += 1
        if i <= max:
            yield i
        else:
            break


if __name__ == '__main__':
    g_obj = demo2(100)
    for i in g_obj:
        print(i)
