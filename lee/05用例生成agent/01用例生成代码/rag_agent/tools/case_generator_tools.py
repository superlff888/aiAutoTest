# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\01用例生成代码\rag_agent\tools\case_generator_tools.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from rag_agent.workflow.case_generator import GenerateCaseWorkflow
from langchain.tools import tool


@tool("测试用例生成",description="根据需求生成测试用例")
def generate_case(requirements: str) -> str:
    """
    根据需求生成测试用例
    :param requirements: 功能的需求文档
    :return: 生成的用例
    """
    workflow = GenerateCaseWorkflow().create_workflow()
    # 调用工作流,生成用例
    response = workflow.invoke({
        "requirements": requirements
    })
    return response

