#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeCommaSeparatedListOutputParser.py
# @Project : PythonProject
# @Author  : Lee大侠
# @Email   : 1310157572@qq.com
# @Date    : 2025/7/22 20:03
# @Desc    : AI大模型应用开发
# ========================================================


from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_openai import ChatOpenAI
import os, dotenv

# 加载env文件到环境变量
dotenv.load_dotenv()

# 初始化大模型
llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME"),
    openai_api_key=os.getenv("API_KEY"),
    openai_api_base=os.getenv("BASE_URL")
)

# 执行链
response = llm.invoke('列出3种适合春季穿搭的颜色，用逗号分隔。')
print("原始输出：", response.content)
# 初始化输出解析器
parser = CommaSeparatedListOutputParser()
# 解析为结构化列表
structured = parser.parse(response.content)
print("结构化列表：", structured)

