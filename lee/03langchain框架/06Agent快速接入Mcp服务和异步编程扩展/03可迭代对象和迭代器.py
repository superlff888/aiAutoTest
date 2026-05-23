# @Author  : 木森
# @weixin: python771

"""
可迭代对象：
    1、底层实现：实现了__iter__方法的对象叫做可迭代对象
    2、直观感受：通过用过for循环遍历的的对象都是可迭代对象
    字符、列表、元组、字典、集合(python基础的数据类型里面除了数值(int,float,bool值)，其他的都是可迭代对象

迭代器：
    1、底层实现：实现了__iter__方法 和__next__方法的对象叫做迭代器对象
    2、python内置的可迭代对象，都可以使用内置函数iter()，将可迭代对象转换为迭代器对象

    内置函数：
        iter(对象)  --->对象.__iter__()
        next(对象)  ---> 对象的__next__()

迭代器和可迭代对象的直观区别：
    1、都可以使用for循环遍历
    2、迭代器可以使用next函数进行单次迭代
    3、可迭代对象通过使用for循环重复遍历，而迭代器中的数据只能迭代一次(只能遍历一次)
"""

li = [111, 22, 444, 555, 666, 777]

for i in li:
    print(i)
for i in li:
    print(i)
for i in li:
    print(i)
print("=============1====================")
iter_li = iter(li)
print("iter_li:", iter_li)
print(next(iter_li))
print(next(iter_li))
print(next(iter_li))
print("=================2=======================")
for j in iter_li:
    print(j)