#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 03序列化和反序列化.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/18 14:48
# @Desc    : AI大模型应用
# ============================================================================
"""
序列化方法
把 pydantic 的数据模型对象转换为 字典、Json
反序列化
把字典转换为 pydantic 的数据模型
"""
"""站在pydantic 的数据模型的角度，转化为其他数据类型为序列化，其他数据类型转化为pydantic为反序列化"""


from pydantic import BaseModel


"""序列化方法
把 pydantic 的数据模型对象转换为 字典、Json
"""


class User(BaseModel):
    id: int
    name: str
    age: int

user = User(id=1, name="李四", age=30)

""" 
IncEx 表示无限嵌套
Mapping[int, Union['IncEx', bool]  ->  Mapping映射的键可以是int整数,值可以是布尔值（True或False）或者另一个IncEx字典

"""
# 转换为字典
user_dict = user.model_dump()
print("字典:", user_dict)  # 字典: {'id': 1, 'name': '李四', 'age': 30}

# 转换为JSON
user_json = user.model_dump_json()
print("JSON:", user_json,"数据类型", type(user_json))  # JSON: {"id": 1, "name": "李四", "age": 30} 数据类型 <class 'str'>

# 包含特定字段
partial_dict = user.model_dump(include={'name', 'age'})   # IncEx 表示无限嵌套  set集合
print("部分字段:", partial_dict)  # 部分字段: {'name': '李四', 'age': 30}

# 排除特定字段
filtered_dict = user.model_dump(exclude={'id'})
print("排除ID:", filtered_dict)  # 排除ID: {'name': '李四', 'age': 30}


"""反序列化
把字典转换为 pydantic 的数据模型
"""

# 从 字典 创建 pydantic 的数据模型
data = {"id": 2, "name": "王五", "age": 28}  # 与json的区别是没有的单引号，因为json是字符串格式
print("数据类型:", type(data))
user_from_dict = User(**data)
print("从字典创建:", user_from_dict, "数据类型", type(user_from_dict))  # 从字典创建: User(id=2, name='王五', age=28) 数据类型 <class 'pydantic.main.User'>

# 从 JSON 创建 pydantic 的数据模型
json_data = '{"id": 3, "name": "赵六", "age": 35}'
user_from_json = User.model_validate_json(json_data)
print("从JSON创建:", user_from_json, "数据类型", type(user_from_json))  # 从JSON创建: User(id=3, name='赵六', age=35) 数据类型 <class '__main__.User'>