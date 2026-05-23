# @Author  : 木森
# @weixin: python771
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

1、一个主WorkFlow,两个节点
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
