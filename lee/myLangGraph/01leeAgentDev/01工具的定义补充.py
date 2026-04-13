#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------
# @File    : AIBasic.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/12/20 09:42
# @Desc    : AI大模型应用开发
# ========================================================

from typing import Type

from langchain_core.tools import BaseTool, tool


# 1、工具的参数声明


@tool("add01", description="计算数值相加的工具")
def add(a: int, b: int) -> int:
    """
    计算两个数值相加的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """
    计算两个数值相乘的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    return a * b


# ============================工具定义的方式二=====================

from pydantic import BaseModel, Field


class AddInput(BaseModel):
    """工具AddTool的参数说明类"""
    a: int = Field(..., description="数值a")
    b: int = Field(..., description="数值b")


class AddTool(BaseTool):
    name: str = "add02"
    description: str = "计算两个数值相加的工具"
    args_schema: Type[BaseModel] = AddInput  # 声明工具的参数

    def _run(self, a: int, b: int) -> int:
        return a + b


""""
工具定义时设置的 工具名称，工具描述，参数声明都是给大模型看的，
所以定义工具时：
    工具名称要是唯一的不能重复
    参数说明要详细，一定要声明类型
    工具描述也要详细
"""
