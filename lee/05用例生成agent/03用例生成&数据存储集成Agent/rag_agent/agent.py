# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\agent.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from rag_agent.pormpts.system_prompt import get_system_prompt
from rag_agent.tools.rag_tools import lightrag_query
from rag_agent.tools import case_generator_tools
from rag_agent.tools.case_database_tools import save_case_to_database, query_exist_case

dotenv.load_dotenv()

# 初始模型配置
model = init_chat_model(
    model_provider="openai",
    model=os.getenv("MODEL2"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    temperature=0.5,
)

# 快速创建一个agent
agent = create_deep_agent(
    model=model,
    # 通过工具接入知识库系统
    tools=[
        # 知识库检索工具
        lightrag_query,
        # 用例生成的工具
        case_generator_tools.generate_case,
        # 补充生成用例的工具
        case_generator_tools.generate_case_by_exist,
        # 用例保存的工具
        save_case_to_database,
        # 查询数据库中已存在的用例
        query_exist_case,
    ],
    system_prompt=get_system_prompt()
)

# 使用agent进行问答
response = agent.stream({
    "messages": [{
        "role": "user",
        "content": "帮我给 用户收货地址添加功能 生成测试用例！"
    }]
},
    stream_mode=["updates", "messages"],
    version="v2",
)

for chunk in response:
    if chunk["type"] == "messages":
        print(chunk["data"][0].content, end='')
