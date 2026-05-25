# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\07Agent接入MCP和Skills\api_testing_agent\core\agent.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
Agent 主逻辑模块
负责协调各个组件，处理用户请求
"""

from typing import Optional, Dict, Any, List
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel


class Agent:
    """接口测试智能体主类"""

    def __init__(
        self,
        model: BaseChatModel,
        tools: Optional[List[Any]] = None,
        checkpointer: Optional[Any] = None,
    ):
        """
        初始化 Agent

        Args:
            model: 聊天模型实例
            tools: 工具列表
            checkpointer: 检查点存储器（用于对话记忆）
        """
        self.model = model
        self.tools = tools or []
        self.checkpointer = checkpointer

    async def arun(self, messages: List[BaseMessage]) -> str:
        """
        异步运行 Agent

        Args:
            messages: 消息列表

        Returns:
            Agent 响应内容
        """
        raise NotImplementedError("请在子类中实现")

    def run(self, messages: List[BaseMessage]) -> str:
        """
        同步运行 Agent

        Args:
            messages: 消息列表

        Returns:
            Agent 响应内容
        """
        raise NotImplementedError("请在子类中实现")
