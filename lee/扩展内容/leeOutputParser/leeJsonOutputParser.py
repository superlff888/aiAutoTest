#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeJsonOutputParser.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/21 23:23
# @Desc    : JsonOutputParser
# ========================================================

import dotenv
import os
import json
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# 定义 pydantic 数据类型
class UserInfo(BaseModel):
    """需要解析的数据模型类(定义需要解析的字段)"""
    name: str = Field(..., description="用户名")
    age: int = Field(..., description="用户年龄")
    sex: str = Field(..., description="用户性别")


# 加载统计目录.env文件中的环境变量
dotenv.load_dotenv()
# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model_name=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)
# 构建提示词模板
prompt = PromptTemplate(
    input_variables=["name"],
    template="""
    我的名字叫{name}，年龄是18，性别是男
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {{"name":xx,"age":xx,"sex":xx}}
    """,
)


# 创建一个响应数据解析器,用于解析调用LLM的输出到JSON对象
parser = JsonOutputParser(pydantic_project=UserInfo)

# 创建调用链
chain = prompt | llm | parser
# 执行调用链
response = chain.invoke({"name": "张三"})
"""
如果你在构建链时使用了 PromptTemplate 或 RunnableSequence，那么 传入 dict 是必须的:
1. 使用 PromptTemplate 时，传入 dict
2. 使用 RunnableSequence（如 chain = prompt | llm）
3. 使用 StructuredOutputParser
4. 使用工具调用（bind_tools）时
5. 使用多模态输入（如图像 + 文本）时
"""
print(type(json.dumps(response, indent=4, ensure_ascii=False)))
print(json.dumps(response, indent=4, ensure_ascii=False))




