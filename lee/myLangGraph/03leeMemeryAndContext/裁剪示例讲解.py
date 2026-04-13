#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================
# @File    : 裁剪示例讲解.py
# @Project : AIDev
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/8/31 22:36
# @Desc    : AI大模型应用
# ============================================================================

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately

"""
过滤出所有的SystemMessage、AIMessage
"""

# 假设这是我们的对话记录，就像一本书的章节
messages = [
    SystemMessage(content="系统提示：你是个助手"),      # 相当于"前言"
    HumanMessage(content="用户：你好"),                # 相当于"第一章"
    AIMessage(content="AI：你好！有什么需要帮助？"),    # 相当于"第二章"
    HumanMessage(content="用户：今天天气如何？"),       # 相当于"第三章"
    AIMessage(content="AI：今天天气晴朗"),             # 相当于"第四章"
    HumanMessage(content="用户：谢谢"),               # 相当于"第五章"
    AIMessage(content="AI：不客气")                   # 相当于"后记"
]

# 先过滤类型
filtered_messages = [
    msg for msg in messages if isinstance(msg, (AIMessage, SystemMessage))
]

# 再修剪token数量（如果需要）
if len(filtered_messages) > 0:
    trimmed = trim_messages(
        messages=filtered_messages,
        max_tokens=100,  # 你想要的token限制
        token_counter=count_tokens_approximately,
        strategy="last",
        allow_partial=True
    )
# 现在让我们看看划出来的结果是什么
print("划出来的范围:") 
for msg in trimmed:
    print(f"- {type(msg).__name__}: {msg.content}")