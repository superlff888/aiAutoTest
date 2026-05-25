# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\04中间件\自定义中间件\基于装饰器&中间件创建的中间件\MyMiddlewer.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import json
import os
from typing import Any

from langchain.agents import AgentState
from langchain.agents.middleware.types import StateT, ModelRequest, ModelResponse
from langgraph.runtime import Runtime
from langchain.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.agents.middleware import (AgentMiddleware,SummarizationMiddleware,ModelFallbackMiddleware,
                                         TodoListMiddleware,ToolRetryMiddleware)
from langgraph.typing import ContextT
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model=os.getenv("MODEL"),
)

vl_model = ChatOpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    model=os.getenv("VL_MODEL"),
)


class MyAgentMiddleware(AgentMiddleware):

    def before_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """模型调用执行会执行的中间件"""
        print("模型调用执行前")

    def after_model(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """模型调用执行完毕会执行的中间件"""
        print("模型调用执行完毕")
        return None

    def after_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """agent调用执行前会执行的中间件"""
        print("agent调用执行前")
        return None

    def before_agent(self, state: StateT, runtime: Runtime[ContextT]) -> dict[str, Any] | None:
        """agent调用执行完毕会执行的中间件"""
        print("agent调用执行完毕")
        return None

    def __if_message_type_is_image(messages):
        """判断消息中是否包含图片，如果包含图片则使用视觉模型，不包含图片则使用文本模型"""
        for message in messages:
            if message.type == "human" and isinstance(message.content, list):
                for content in message.content:
                    if content["type"] == "image":
                        return vl_model
        return model

    def wrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        """这个方法是agent调用大模型的时候会自动执行的一个方法"""
        # 在这个函数中，根据消息的内容类型来选择使用文本模型还是视觉模型
        select_model = self.__if_message_type_is_image(request.state["messages"])

        return handler(request.override(model=select_model))

    def dynamic_prompt(self):
        """这个方法会自动执行，根据消息的类型来动态生成prompt"""
        return """
        你是一个编程助手
        """
