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
1. state: 图形的状态
    继承typeDict的类
2. config：包含配置信息（如）和跟踪信息（如Runnable Config thread_id tags）
3. runtime：包含运行时上下文和其他信息（如 Runtime store stream_writer）
4. state状态和context上下文的区别：
    定义在上下文的值不可以改变，运行过程中上下文对应的值是固定的；
    定义在状态中的值在每个节点返回数据都可以对状态数据进行覆盖或者修改
"""

from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from dataclasses import dataclass
from langchain_core.runnables import RunnableConfig

from langgraph.runtime import Runtime


# 工作流中定义状态（Agent智能体不需要定义状态），GraphState定义状态关键是要继承TypedDict
from pydantic import BaseModel, Field

class State(BaseModel):
    """状态"""
    user_input: str = Field(description="用户输入的需求")
    test_cases: list = Field(default_factory=list, description="生成的测试用例")  # 共享数据


# 定义运行时的上下文参数
@dataclass
class RuntimeContext:
    """运行时上下文参数：在运行开始时传入的静态数据"""
    test_env: str  # 测试环境
    tester_name: str  # 测试人员名称


# ================定义运行节点函数=================

def generator_test_case(state: State):
    """生成测试用例"""
    print(f"用户输入的需求是:{state.user_input},开始进行测试用例生成")
    # 这里核心的功能实现需要调用llm进行生成，暂时跳过
    print("测试用例已经生成")
    state.test_cases.extend(["测试用例1", "测试用例2"])


def run_test_cases(state: State, runtime: Runtime[RuntimeContext]):
    """执行测试用例"""
    print("正在执行测试用例：", state.test_cases)
    print("当前执行的测试环境", runtime.context.test_env)
    print("执行人", runtime.context.tester_name)
    # print("执行人", runtime.context.get('tester_name'))
    return {"report": "这个是一个测试报告"}


def generator_test_report(state: State, config: RunnableConfig):
    """生成测试报告"""
    print("执行generator_test_report节点")
    print("配置信息：", config.get("configurable"))

    return {"report": "这个是一个测试报告"}


# =================工作流的创建个编排===================

graph = StateGraph(State, context_schema=RuntimeContext)
graph.add_node("生成测试用例", generator_test_case)
graph.add_node("执行测试用例", run_test_cases)
graph.add_node("生成测试报告", generator_test_report)

# 设置起点
# graph.set_entry_point("生成测试用例")
graph.add_edge(START, "生成测试用例")
graph.add_edge("生成测试用例", "执行测试用例")
graph.add_edge("执行测试用例", "生成测试报告")
# graph.set_finish_point("生成测试报告")
graph.add_edge("生成测试报告", END)

app = graph.compile()
# res = app.invoke({"user_input": "测试项目A"},
#                  config={"recursion_limit": 5},
#                  context={"test_env": "测试环境A", "tester_name": "张三"}
#                  )

res = app.invoke({"user_input": "测试项目A"},
                 config=RunnableConfig(configurable={"thread_id": "BUG#123"}),
                 context=RuntimeContext(test_env="测试环境A", tester_name="张三")
                 )

print(res)
