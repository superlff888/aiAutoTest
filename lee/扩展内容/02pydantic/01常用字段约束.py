#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 01常用字段约束.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2026/3/17 23:01
# @Desc    : AI大模型应用
# ============================================================================
"""
Field()的约束（如 ge, pattern）用于声明式验证，简洁但功能有限
field_validator用于过程式验证，可以编写任意复杂的业务逻辑
两者结合使用，先通过 Field()做基本验证，再用 field_validator做业务验证
通过这种组合，Pydantic 既能保证数据的基本正确性，又能满足复杂的业务验证需求。
"""

from pydantic import BaseModel, Field, field_validator, ValidationError


# noinspection PyMethodParameters
class User(BaseModel):
    name: str = Field(..., min_length=2, max_length=5)  # … 表示name为必填字段
    age: int = Field(..., ge=0, le=150)  # 大于等于0，小于等于150
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # None表示email为可选字段，默认为None
    salary: float = Field(..., gt=0)  # 大于0
    notes: str = Field(default=None, description="这是一个备注字段")  # 默认为None

    # 自定义字段的验证方法 @field_validator("email")表示这个装饰器下面的方法专门用于验证 email字段
    @field_validator("email", mode="after")
    @classmethod  # 不需要显式添加 @classmethod装饰器（field_validator会自动处理），但第一个参数必须是 cls
    def validate_email(cls, value):  # 第一个参数必须是 cls，cls表示当前模型类
        if "@qq" not in value:
            raise ValueError("邮箱只能使用QQ邮箱")
        else:
            return value.strip().lower()
    @field_validator("age")
    def validate_age(cls, value):  # cls表示当前模型类
        if value < 18:
            raise ValueError("年龄必须大于18")
        else:
            return value


musen = User(name="aiAgent", age=18, email="12333@qq.com", salary=1000)
print(musen)

"""
【总结】
1. Field()的约束（如 ge, pattern）用于声明式验证，简洁但功能有限
2. field_validator用于过程式验证，可以编写任意复杂的业务逻辑，其装饰的方法第一个参数必须是self
3. 两者结合使用，先通过 Field()做基本验证，再用 field_validator做业务验证
 通过这种组合，Pydantic 既能保证数据的基本正确性，又能满足复杂的业务验证需求。
"""
"""
mode="after"表示在字段的常规验证之后执行:
    # 当创建 User(email="  USER@QQ.COM  ") 时，执行顺序如下：
    1. 原始输入: "  USER@QQ.COM  "
       ↓
    2. 类型转换: 确保是字符串 → "  USER@QQ.COM  "
       ↓
    3. Field约束验证: 检查正则表达式 pattern → 通过
       ↓
    4. mode="after" 验证器执行: validate_email("  USER@QQ.COM  ")
       │
       ├→ 验证: 检查 "qq.com" 是否在值中 → 是
       │
       └→ 转换: 执行 value.strip().lower() → "user@qq.com"
       ↓
    5. 最终存储值: "user@qq.com"
"""