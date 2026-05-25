# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\07Agent接入MCP和Skills\agent_demo5\demo2.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from deepagents.backends import LocalShellBackend
from deepagents.middleware import SkillsMiddleware
from langchain.agents import create_agent

agent = create_agent(

    # 通过skills中间件实现支持skills
    middleware=[SkillsMiddleware(backend=LocalShellBackend(root_dir=".", virtual_mode=True),
                                 sources=['skills'])]
)
