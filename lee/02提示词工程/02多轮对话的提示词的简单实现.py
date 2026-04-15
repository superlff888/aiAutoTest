# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\02提示词工程\02多轮对话的提示词的简单实现.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/14 01:05
# @UpdateTime  : 2026/04/15 22:44
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================
import os
import dotenv
from langchain_openai import ChatOpenAI

# 加载环境变量
dotenv.load_dotenv()

# 创建模型实例
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY")
)

