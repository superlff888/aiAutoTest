#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeRunnableMap.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/22 21:14
# @Desc    : 将任意 Python函数封装为链路组件
# ========================================================

import dotenv
import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model_name=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)



prompt = PromptTemplate(
    input_variables=["name", "output"],
    template="""
    我的名字叫{name}，年龄是18，性别是男
    请帮我把个人信息转换为json格式输出，
    输出格式要求如下:
    {output}
    """,
)


def handle_response(response):
    """
    处理大模型返回的响应数据
    :param response:
    :return:
    """
    print("handle_response:", response)
    print("upper处理后的数据的type为:", type(response))
    return response.lower()


# 自定义runnable对象，传入普通的函数
lower = RunnableLambda(handle_response)
# 自定义runnable对象,传入lambda函数
upper = RunnableLambda(lambda x: x.content.upper())
# 大模型输出AIMessage传递给upper,upper输出的数据是str（因为返回的是key转化为大写的content）
# 对应Runnable对象，可以使用langchain语言表达式进行链式调用
chain = prompt | llm | upper | lower

# 调用大模型
response = chain.invoke({"name": "张三", "output": "{'name': 'XX', 'age': XX, 'sex': 'XX'}"})

# 打印响应数据
print("最终的结果：", response)
