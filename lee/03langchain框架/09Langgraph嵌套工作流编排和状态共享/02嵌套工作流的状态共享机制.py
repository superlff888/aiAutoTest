# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\03langchain框架\09Langgraph嵌套工作流编排和状态共享\02嵌套工作流的状态共享机制.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================

"""
【用例生成的完整流程】
1. 基于需求生成测试点：
获取需求--->基于需求整理测试点--->分析测试点是否覆盖需求中所有的功能，验证测试点覆盖率--->对于未覆盖的测试点补全--->输出所有的测试点
2. 基于生成的测试点进一步生成测试用例：
基于测试点生成特定格式的测试用例--->对生成的测试用例进行评审---> 分析测试用例是否全部覆盖测试点，验证测试用例的覆盖率--->针对未覆盖的测试点补全测试用例---> 输出所有的测试用例
"""

import operator
import os
import time

from typing import Annotated
import operator
import dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from pydantic import BaseModel, Field

dotenv.load_dotenv()

"""
设一个涵盖用例生成，用例执行的Agent系统

1、一个主WorkFlow,两个子节点
    节点一：用例生成的Agent
    节点二：用例执行的Workflow
    
"""
# 定义模型
model = ChatOpenAI(model=os.getenv("MODEL"))


class MainState(BaseModel):
    """主Workflow的定义状态"""
    docs_id: str = Field(default="", description="文档的id")
    messages: list = Field(default=[], description="保存agent执行过程中聊天记录")
    api_docs: str = Field(default="", description="接口的业务说明文档")
    case_list: Annotated[list, operator.add] = Field(default=[], description="用例列表")
    execute_result: list = Field(default=[], description="保存用例执行结果")


class GenerateState(BaseModel):
    """用例生成agent的状态"""
    generate_messages:list = Field(default=[], description="保存agent执行过程中聊天记录")
    test_points: list = Field(default=[], description="接口的测试点")
    test_point: str = Field(default="", description="生成节点当前正在生成用例的测试点")
    # 和MainState共享的状态
    api_docs: str = Field(default="", description="接口的业务说明文档")
    case_list: Annotated[list, operator.add] = Field(default=[], description="保存生成的用例")


class CaseExecuteState(BaseModel):
    """用例执行的Workflow的状态"""
    execute_messages: list = Field(default=[], description="保存agent执行过程中聊天记录")
    # 和MainState共享的状态
    case_list: Annotated[list, operator.add] = Field(default=[], description="保存生成的用例")
    execute_result: list = Field(default=[], description="保存用例执行的结果")


class GenerateAgent:
    """用例生成agent"""

    def get_test_point(self, state: GenerateState):
        """获取测试点"""
        print("==================获取测试点======================")
        print("当前的接口文档如下：", state.api_docs)
        # 调用大模型去实现测试点的提取生成
        return {"test_points": [
            {"name": "测试点1", "decs": f"文档{state.api_docs},测试点1的描述"},
            {"name": "测试点2", "decs": f"文档{state.api_docs},测试点2的描述"},
            {"name": "测试点3", "decs": f"文档{state.api_docs},测试点3的描述"},
            {"name": "测试点4", "decs": f"文档{state.api_docs},测试点4的描述"},
            {"name": "测试点5", "decs": f"文档{state.api_docs},测试点5的描述"},
            {"name": "测试点6", "decs": f"文档{state.api_docs},测试点6的描述"},
            {"name": "测试点7", "decs": f"文档{state.api_docs},测试点7的描述"},
        ]}

    def generate_autotest_case(self, state: dict):
        """生成自动化用例"""
        print("==================自动化用例生成======================")
        test_point = state.get("test_point")
        # 调用大模型去实现自动化用例生成

        print(f"正在为测试点{test_point}生成自动化用例")
        time.sleep(3)
        print(f"正在为测试点{test_point}生成自动化用例生成完毕")
        return {"case_list": [f"测试点{test_point}自动化用例"]}

    def auto_test_case_save(self, state: GenerateState):
        """保存自动化用例"""
        print("==================保存自动化用例======================")
        # 获取当前所有的自动化用
        case_list = state.case_list
        print(f"正在保存自动化用例：{case_list}")

    def router_func(self, state: GenerateState):
        """路由函数"""
        print("==================路由函数======================")
        test_points = state.test_points

        run_list = []
        # 获取当前节点的输出
        for i in test_points:
            run_list.append(Send("自动化用例生成", {"test_point": i.get("name")}))
        return run_list

    def create_agent(self):
        """创建agent"""
        agent = StateGraph(GenerateState)
        agent.add_node("接口测试点提取", self.get_test_point)
        agent.add_node("自动化用例生成", self.generate_autotest_case)
        agent.add_node("自动化用例保存", self.auto_test_case_save)
        # 节点编排
        agent.add_edge(START, "接口测试点提取")
        agent.add_conditional_edges("接口测试点提取", self.router_func)
        agent.add_edge("自动化用例生成", "自动化用例保存")
        agent.add_edge("自动化用例保存", END)
        # 返回编译的结果
        return agent.compile()


class CaseExecute:
    """用例执行Workflow"""

    def load_test_env(self, state: GenerateState):
        """加载测试环境"""
        print("==================加载测试环境======================")
        return {"test_env": "测试环境"}

    def run_test_case(self, state: CaseExecuteState):
        """执行用例"""
        print("==================执行用例======================")
        test_case = state.case_list
        print(f"正在执行用例：{test_case}")
        time.sleep(3)
        print(f"正在执行用例：{test_case}执行完毕")
        return {"execute_result": [f"用例{test_case}执行结果"]}

    def create_workflow(self):
        """创建Workflow"""
        graph = StateGraph(CaseExecuteState)
        graph.add_node("加载测试环境", self.load_test_env)
        graph.add_node("执行用例", self.run_test_case)
        graph.add_edge(START, "加载测试环境")
        graph.add_edge("加载测试环境", "执行用例")
        graph.add_edge("执行用例", END)
        # 返回编译的结果
        return graph.compile()

# =====================================主工作流，调用用例生成agent和用例执行workflow=================================
class MainWorkFlow:
    """主Workflow"""
    generator_agent = GenerateAgent().create_agent()
    case_execute_workflow = CaseExecute().create_workflow()

    def load_api_docs(self, state: MainState):
        """加载接口的业务说明文档"""
        print("==================加载接口的业务说明文档======================")
        # 获取当前需要加载的文档id
        docs_id = state.docs_id
        return {"api_docs": f"接口业务{docs_id}的说明文档"}

    def save_result(self, state: MainState):
        """保存结果"""
        print("==================保存结果======================")
        print(f"正在保存结果：{state.execute_result}")

    def create_workflow(self):
        """创建Workflow"""
        graph = StateGraph(MainState)
        # 节点编排
        graph.add_node("加载接口的业务说明文档", self.load_api_docs)
        # 用例生成(调用子agent)
        graph.add_node("用例生成", self.generator_agent)
        # 用例执行（调用子workflow）
        graph.add_node("用例执行", self.case_execute_workflow)
        # 保存结果
        graph.add_node("保存结果", self.save_result)

        # 编排执行顺序
        graph.add_edge(START, "加载接口的业务说明文档")
        graph.add_edge("加载接口的业务说明文档", "用例生成")
        graph.add_edge("用例生成", "用例执行")
        graph.add_edge("用例执行", "保存结果")

        return graph.compile()


if __name__ == '__main__':
    workflow = MainWorkFlow().create_workflow()
    response = workflow.invoke({"docs_id": "1"})
    # 通过invoke去调用workflow最后得到的结果(所以节点执行完毕之后的状态MainState)
    print( response)





"""
【子图的使用模式--共享状态模式】

在主工作流中调用子工作流有两种模式：

1、共享状态模式：主工作流和子工作流共享同一个状态对象，主工作流和子工作流对状态对象中的数据进行读写操作，适用于主工作流和子工作流之间需要频繁交互数据的场景。
2、非共享状态模式：主工作流和子工作流各自维护独立的状态对象，主工作流和子工作流之间通过输入输出进行数据传递，适用于主工作流和子工作流之间交互较少，或者需要隔离状态的场景。

"""

"""
【用例生成和执行系统设计思路】
1. 定义状态类，维护共享状态和各自的独立状态：
    # 和MainState共享的状态
    case_list: Annotated[list, operator.add] = Field(default=[], description="保存生成的用例")
    execute_result: list = Field(default=[], description="保存用例执行的结果")
2. 定义用例生成Agent，包含获取测试点、生成用例、保存用例等功能
3. 定义用例执行Workflow，包含加载测试环境、执行用例等功能
4. 定义主Workflow，编排调用用例生成Agent和用例执行Workflow，并维护整体的状态流转
    # 用例生成(调用子agent)
    graph.add_node("用例生成", self.generator_agent)
    # 用例执行（调用子workflow）
    graph.add_node("用例执行", self.case_execute_workflow)
5. 通过状态合并机制实现用例生成Agent和用例执行Workflow之间的状态共享，确保数据在不同节点之间正确传递和更新
6. 最后通过invoke调用主Workflow，触发整个流程的执行，并输出最终的结果
    

"""