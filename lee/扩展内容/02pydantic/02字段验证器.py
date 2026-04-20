#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 02字段验证器.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/18 14:14
# @Desc    : AI大模型应用
# ============================================================================


"""
Field()的约束（如 ge, pattern）用于声明式验证，简洁但功能有限
field_validator用于过程式验证，可以编写任意复杂的业务逻辑
两者结合使用，先通过 Field()做基本验证，再用 field_validator做业务验证
通过这种组合，Pydantic 既能保证数据的基本正确性，又能满足复杂的业务验证需求。
"""

from pydantic import BaseModel, Field, field_validator, ValidationError


class User(BaseModel):
    name: str = Field(..., min_length=2, max_length=5)  # … 表示name为必填字段
    age: int = Field(..., ge=0, le=150)  # 大于等于0，小于等于150
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # None表示email为可选字段，默认为None
    salary: float = Field(..., gt=0)  # 大于0
    notes: str = Field(None, description="这是一个备注字段")

    # 自定义字段的验证方法 @field_validator("email")表示这个装饰器下面的方法专门用于验证 email字段
    @field_validator("email", mode="after")  # mode='after' / 'before' / 'plain' —- 只传 1 个值;类型转换 + Field 约束 之后执行验证器函数（mode='after'）; 
    # @classmethod  # 不需要显式添加 @classmethod装饰器（field_validator会自动处理），但第一个参数必须是 cls
    def validate_email(cls, email):  # 第一个参数必须是 cls，cls表示当前模型类
        if "@qq" not in email:
            raise ValueError("邮箱只能使用QQ邮箱")
        else:
            return email.strip().lower()

    @field_validator("age")
    def validate_age(cls, value):  # cls表示当前模型类
        if value < 18:
            raise ValueError("年龄必须大于18")
        else:
            return value


if __name__ == '__main__':
    try:
        musen = User(name="aiAgent", age=17, email="12333@qq.com", salary=1000)
    except ValidationError as e:
        print(f"e.title模型名称{e.title}\n")
        print(f"e.errors()获取所有错误列表：{e.errors()}\n")
        print(f"e.error_count()获取错误数量：{e.error_count()}\n")
        print(f"e.json()获取所有错误的JSON格式：{e.json()}\n")

"""
【ValidationError 的核心属性: 捕获field_validator装饰器下面的方法抛出的异常】
    try:
        User(**invalid_data)
    except ValidationError as e:
        # 核心属性
        e.errors()        # 所有错误列表
        e.error_count()   # 错误数量
        e.title          # 模型名称
        
ValidationError用于捕获所有验证错误，包括 field_validator装饰器下面方法抛出的异常，但不止于此——它还会捕获字段类型错误、Field()约束错误等所有验证失败。
在验证器中，你抛出具体的异常（如 ValueError），Pydantic 会收集这些异常，统一封装到 ValidationError中抛出
"""
