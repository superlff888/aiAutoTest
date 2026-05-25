# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\01用例生成代码\rag_agent\tools\rag_tools.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv

dotenv.load_dotenv()
import requests
from langchain.tools import tool


@tool('知识库检索工具', description='通过输入问题，从知识库检索详细的内容答案，比如查询某个功能详细的需求和api接口详情')
def lightrag_query(query):
    """
    :param query: 要查询的内容
    :return:
    """
    print(f"========开始从知识库检索内容:{query}=========")

    url = f"{os.getenv('RAG_KNOWLEDGE_BASE_URL')}/query"
    params = {
        "query": query,
        "mode": "global",
    }
    response = requests.post(url, json=params, stream=True)
    result = response.json()['response']
    print("==========知识库内容检索完成==========")
    return result
