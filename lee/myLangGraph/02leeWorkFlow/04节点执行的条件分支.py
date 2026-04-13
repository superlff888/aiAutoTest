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

节点函数可以接受以下三种类型的参数
1. state：图形的状态
    继承typeDict的类
2. config：包含配置信息（如）和跟踪信息（如RunnableConfig thread_tags
3. runtime：包含运行时上下文和其他信息（如 Reactivestreams_writer
"""
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END


# 定义状态
class State(TypedDict):
    """状态"""
    user_input: str
    test_cases: list
    check_result: bool


# ================定义运行节点函数=================

def generator_test_case(state: State) -> dict[str, list[str]]:
    """生成测试用例"""
    print("开始执行生成用例的节点,用户输入的需求是：", state.get("user_input"))
    return {"test_cases": ["测试用例1", "测试用例2"]}


def check_test_case(state: State) -> dict[str, bool]:
    """检查测试用例是否可用"""
    print("校验测试用例是否可用,当前的用例为：", state.get("test_cases"))
    # 校验逻辑后续讲项目的时候完善,校验用例的数量是否大于3
    if len(state.get("test_cases")) >= 3:
        return {"check_result": True}
    else:
        return {"check_result": False}


def generator_test_case_addition(state: State) -> dict[str, list[str]]:
    """补充生成测试用例的节点"""
    print("正在补充生成测试用例的节点……")
    return {"test_cases": state.get("test_cases") + ['测试用例3']}  # list类型数据可以相加，返回list


def run_test_cases(state: State) -> dict[str, str]:
    """执行测试用例"""
    print("开始执行测试用例：", state.get("test_cases"))
    return {"report": "这个是一个测试报告"}


def generator_test_report(state: State, ) -> dict[str, str]:
    """生成测试报告"""
    print("执行generator_test_report节点,生成测试报告")
    return {"report": "这个是一个测试报告"}

# 控制节点执行分支的路由1
def router(state: State) -> str:
    """根据条件去控制执行的路由"""
    if state["check_result"]:
        return "执行测试用例"  # 下一步要执行的节点名称
    else:
        return "补充生成测试用例" # 下一步要执行的节点名称

# def router(state: State) -> str:
#     """根据条件去控制执行的路由"""
#     if state["check_result"]:
#         return True  # 下一步要执行的节点名称
#     return False # 下一步要执行的节点名称

# =================工作流的创建个编排===================
graph = StateGraph(State)
graph.add_node("生成测试用例", generator_test_case)
graph.add_node("检查测试用例", check_test_case)
graph.add_node("补充生成测试用例", generator_test_case_addition)
graph.add_node("执行测试用例", run_test_cases)
graph.add_node("生成测试报告", generator_test_report)


graph.add_edge(START, "生成测试用例")  # 设置起点
graph.add_edge("生成测试用例", "检查测试用例")

# 设置一个控制节点执行分支的条件;条件入口点允许您根据自定义逻辑从不同的节点开始
# path_map: 路由函数返回值不是节点名称，则需要在path_map中映射到节点名称，例如：return True,则 {True: "执行测试用例", False: "补充生成测试用例"}
# graph.add_conditional_edges("检查测试用例", router, {True: "执行测试用例", False: "补充生成测试用例"})
# graph.add_conditional_edges("检查测试用例", router) # 路由函数返回节点名称，则不需要path_map
graph.add_conditional_edges("检查测试用例", router, ["补充生成测试用例", "执行测试用例"]) # 路由函数返回节点名称；path_map用列表维护分支节点名称也可以


graph.add_edge("补充生成测试用例", "执行测试用例")
graph.add_edge("执行测试用例", "生成测试报告")
graph.add_edge("生成测试报告", END)

app = graph.compile()
res = app.invoke({"user_input": "测试项目A"})

print(res)
