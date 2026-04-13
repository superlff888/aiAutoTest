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

"""
创建工作流的步骤：
1、定义状态（整个工作流中涉及到的输入、输出、节点之间共享的数据）
2、定义工作节点（本质就是一个函数）
    注意点：
        工作节点的第一个参数必须是state
        返回值必须是一个字典,字典的中的字段必须要在state类中定义

3、创建一个状态图(工作流)
graph = StateGraph(State)

"""
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing import TypedDict


# 一、定义状态：所有流转的数据都必须是字典格式
class State(TypedDict):
    """
    定义状态
    """
    value_1: str
    value_2: int
    report: str
    input_value: str


# 二、定义工作节点（本质就是一个函数）

def step_1(state: State):
    """定义工作节点"""
    print("执行step_1节点")
    return {"value_1": 100}


def step_2(state: State):
    """定义工作节点"""
    print("执行step_2节点")
    return {"value_2": 100}


def generator_test_report(state: State):
    """定义工作节点"""
    print("执行generator_test_report节点")
    return {"report": "这个是一个测试报告"}


# ===========================================================================
# 三、开发工作流
# 3.1 初始化工作流
graph = StateGraph(State)
# 3.2 把节点(node)添加到状态图(工作流)中
graph.add_node("生成测试用例", step_1)
graph.add_node("执行测试用例", step_2)
graph.add_node("生成测试报告", generator_test_report)
# 3.3 对工作节点进行编排

graph.add_edge(START, "生成测试用例")
graph.add_edge("生成测试用例", "执行测试用例")
graph.add_edge("执行测试用例", "生成测试报告")
graph.add_edge("生成测试报告", END)

# 4、对graph对象进行编译
app = graph.compile()

# 获取执行流程图谱，并保存为图片
# image_content = app.get_graph().draw_mermaid_png()
# print(image_content)
# with open("langgraph_graph.png", "wb") as f:
#     f.write(image_content)
