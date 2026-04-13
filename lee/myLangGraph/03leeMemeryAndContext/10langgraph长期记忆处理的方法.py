#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : AIBasic.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/20 09:42
# @Desc    : AI大模型应用开发理论基础
# ========================================================


from langgraph.store.memory import InMemoryStore

# 长期记忆(内存存储)
memory = InMemoryStore()

# 添加记忆内容(存储内容)
memory.put(namespace=("musen01", "1234uuid"),  # namespace=("用户ID", "对话的uuid")
           key="role_set",
           value={"role": "system", "content": "您是一位资深软件测试工程师"}
           )

memory.put(namespace=("用户id", "对话的uuid"),
           key="target",
           value={"role": "user", "content": "编写用户注册功能的测试用例"}
           )

# 获取记忆内容(获取内容)
res = memory.get(namespace=("musen01", "1234uuid"), key="role_set")
print(res)

# 获取记忆列表
res = memory.list_namespaces()
print(res)

