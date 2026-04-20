#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leePydanticOutputParser.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/21 0:20
# @Desc    : 允许我们定义期望的输出字段，并从模型响应中提取这些字段，输出pydantic的模型对象
# ========================================================

import os
import dotenv
from typing import List
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

"""
1.定义结构化数据模型（Pydantic） 

2.创建输出解析器

3.构建包含格式指令的提示模板

4.通过链式调用获得结构化输出"""
# 加载环境变量
dotenv.load_dotenv()

# 初始化大语言模型
llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

# 定义 Pydantic 数据模型
class TestCase(BaseModel):
    test_case_title: str = Field(..., description="测试用例的标题")  # description会被用于生成提示词
    preconditions: List[str] = Field(..., description="测试前提条件")
    steps: List[str] = Field(..., description="测试步骤")
    expected_result: str = Field(..., description="预期结果")


# 初始化解析器
parser = PydanticOutputParser(pydantic_object=TestCase)

# 获取格式化指令（格式说明）：会生成自动化的格式说明文本
format_instructions = parser.get_format_instructions()
print(f'格式说明文件：{format_instructions}')

# 构建提示词模板
prompt = PromptTemplate(
    template="请根据以下需求生成测试用例，并提供结构化信息:\n{format_instructions}\n需求：{requirement}",  # {format_instructions动态插入格式要求
    input_variables=["requirement"],
    partial_variables={"format_instructions": format_instructions}  # 预绑定固定变量
)
# print(type(prompt))
# print(prompt)

# 构建调用链
chain = prompt | llm | parser

# 执行链
response = chain.invoke({"requirement": "用户登录功能应支持邮箱和密码的验证"})
# 将 Testcase(Pydantic) 对象转为 JSON 字符串
print(response.model_dump_json(), type(response))
print("=" * 50)
print(response)

"""
如果你在构建链时使用了 PromptTemplate 或 RunnableSequence，那么 传入 dict 是必须的:
1. 使用 PromptTemplate 时，传入 dict
2. 使用 RunnableSequence（如 chain = prompt | llm）
3. 使用 StructuredOutputParser
4. 使用工具调用（bind_tools）时
5. 使用多模态输入（如图像 + 文本）时
"""