# @Author  : 木森
# @weixin: python771
"""

魔术方法：
    特点：类里面双下划线开头，双下划线结尾的方法
    作用：是python核心语法底层实现的方法 ，都是在特定的情况下面自动调用的，不需要人为手动调用
    魔术方法：一共有几十个
        __init__: 初始化对象的属性
        __new__: 实例化对象
        __iter__
        __next__
        .....

"""



class MyClass:

    def __init__(self):
        print("在类进行实例化对象的时候，自动调用的方法")
    def __getattribute__(self, item):
        print("在获取对象属性的时候，自动调用的方法,__getattribute__")

    def __setattr__(self, key, value):
        print("在设置对象属性的时候，自动调用的方法__setattr__")

    def __delitem__(self, key):
        print("，自动调用的方法__delitem__")

    def __getitem__(self, item):
        print("自动调用的方法__getitem__")

    def __setitem__(self, key, value):
        print("自动调用的方法__setitem__")

    def __add__(self, other):
        print("在两个对象进行相加的时候，自动调用的方法__add__")
if __name__ == '__main__':
    obj = MyClass()
    obj["name"] = "张三"  # obj.__setitem__("name", "张三")
    obj.age = 18  # obj.__setattr__("age", 18)