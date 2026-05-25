# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\04中间件\自定义中间件\基于装饰器&中间件创建的中间件\tools.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime


# 定义一个文件写入的工具
@tool("文件写入的工具", description="用于写入文件")
def write_file(file_path: str, content: str, runtime: ToolRuntime):
    """
    :param file_path: 文件路径
    :param content: 文件内容
    :param runtime:
    :return:
    """
    # 先判断文件路径是否存在
    if not os.path.exists(os.path.dirname(file_path)):
        # 如果不存在则创建
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


@tool("文件读取的工具", description="用于读取文件")
def read_file(file_path: str, runtime: ToolRuntime):
    """
    :param file_path: 文件路径
    :param runtime:
    :return:
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# 二进制文件读取的工具
@tool("文件读取二进制文件的工具", description="用于读取二进制文件")
def read_binary_file(file_path: str, runtime: ToolRuntime):
    """
    :param file_path: 文件的路径
    :param runtime:
    :return:
    """
    with open(file_path, "rb") as f:
        return f.read()


# 二进制文件写入的工具
@tool("文件写入二进制文件的工具", description="用于写入二进制文件")
def write_binary_file(file_path: str, content: bytes, runtime: ToolRuntime):
    """
    :param file_path: 文件路径
    :param content: 文件的二进制内容
    :param runtime:
    :return:
    """
    # 先判断文件路径是否存在
    if not os.path.exists(os.path.dirname(file_path)):
        # 如果不存在则创建
        os.makedirs(os.path.dirname(file_path))
    with open(file_path, "wb") as f:
        f.write(content)


# 文件目录读取的工具
@tool("文件目录读取的工具", description="用于读取文件目录")
def read_directory(file_path: str, runtime: ToolRuntime):
    """
    :param file_path: 文件目录的路径
    :param runtime:
    :return:
    """
    if not os.path.exists(file_path):
        return []
    return os.listdir(file_path)
