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
