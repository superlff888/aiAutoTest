# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\08langgraph编排Agent流程\04循环边界.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from typing import TypedDict
from langchain_openai import ChatOpenAI
import os, dotenv
from langgraph.constants import START, END

from langgraph.graph import StateGraph

dotenv.load_dotenv()

llm = ChatOpenAI(
    model_name="Pro/deepseek-ai/DeepSeek-V3",
    openai_api_key=os.getenv('API_KEY'),
    openai_api_base="https://api.siliconflow.cn/v1",
)


#  1、定义State
class State(TypedDict):
    user_input: str  # 用户输入的数据
    csv_data: str  # csv格式的数据
    json_data: str  # json格式的数据
    other_data: str  # 其他格式的数据
    run_flow: str  # 运行对应的业务流


# 2、定义工作节点
def select_run_flow(state: State) -> dict:
    """自动选择运行的业务流"""
    user_input = input("请输入你的需求:")
    prompt = f"""
    你是一个资深测试工程师，请分析用户输入一个功能的说明文档，还是接口的文档信息，
    输入内容如下：{user_input}
    如果是接口的文档信息 则输出返回数字1559729，如果是需求说明则输出返回数字2232309729，其他的内容则输出返回数字0
    """
    result = llm.invoke(prompt)
    if '1559729' in result.content:
        return {"run_flow": "generator_api_case", 'user_input': user_input}
    elif '2232309729' in result.content:
        return {"run_flow": "generator_test_case", 'user_input': user_input}
    else:
        return {"run_flow": "work3"}


def generator_api_case(state: State) -> dict:
    prompt = f"""
    您是一个工作10年的测试工程师，您需要根据用户输入的接口文档，生成对应的测试用例，先考虑正常功能执行的用例，
    然后考虑异常场景的用例，最后考虑边界场景的用例，最后考虑性能场景的用例，最后考虑兼容性
    输入内容如下：{state["user_input"]}
    输出结果要是是json格式的用例数据
    """
    result = llm.invoke(prompt)
    return {'json_data': result.content}


def generator_test_case(state: State) -> dict:
    prompt = f"""
        您是一个工作10年的测试工程师，您需要根据用户需求文档生成对应的测试用例，先考虑正常功能执行的用例，
        然后考虑异常场景的用例，最后考虑边界场景的用例，最后考虑性能场景的用例，最后考虑兼容性
        输入内容如下：{state["user_input"]}
        输入格式的要求是csv格式的用例数据
        """
    result = llm.invoke(prompt)
    return {'csv_data': result.content}


def work3(state: State) -> dict:
    return {'other_data': "输入的内容不是接口文档，也不是需求说明"}


# 定义一个路由
def router(state: State) -> str:
    if state["run_flow"] == "generator_api_case":
        return "generator_api_case"
    elif state["run_flow"] == "generator_test_case":
        return "generator_test_case"
    else:
        return "work3"


# 创建一个graph
graph = StateGraph(State)
# 往graph中添加节点
graph.add_node("select1", select_run_flow)
graph.add_node("api_case", generator_api_case)
graph.add_node("test_case", generator_test_case)
graph.add_node("work3", work3)

# 进行节点编排
graph.add_edge(START, "select1")
# 设置一个边条件(流程分支判断)
graph.add_conditional_edges('select1', router, {
    "generator_api_case": "api_case",
    "generator_test_case": "test_case",
    "work3": "work3"
})

graph.add_edge("api_case", END)
graph.add_edge("test_case", END)
# 执行完后会跳回 select1，而 select1 又会重新做分类判断，然后可能又走到某个分支……形成循环
graph.add_edge("work3", 'select1')  # 把节点执行完之后指向前面的某个节点，就可以实现循环

# 编译graph
app = graph.compile()
# print(app.get_graph().draw_mermaid())

if __name__ == '__main__':
    result = app.stream({})
    for r in result:
        print(r)
