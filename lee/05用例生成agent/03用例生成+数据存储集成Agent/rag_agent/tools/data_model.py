# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\tools\data_model.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from pydantic import BaseModel, Field


class GenerateCase(BaseModel):
    case_id: str = Field(..., description="用例编号")
    case_name: str = Field(..., description="用例名称")
    priority: str = Field(..., description="优先级")
    test_data: dict = Field(..., description="测试数据")
    setup: list = Field(..., description="前置条件")
    execute_step: list = Field(..., description="用例执行的步骤")
    except_result: list = Field(..., description="预期结果")
    result: str = Field(None, description="实际结果")

    # 用例管理的需求编号
    requirement_id: str = Field(None, description="需求编号")

