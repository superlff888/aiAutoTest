# @Author  : 木森
# @weixin: python771
"""
节点并发执行：
    一个接口测试的业务流---->分析测试点，生成接口用例---->生成自动化用例(因为每条用例都需要生成自动化用例，所以这个节点可以设置为并发调用的节点)

"""

import os
import time

import dotenv
from langchain_openai import ChatOpenAI
from langgraph.constants import START, END

dotenv.load_dotenv()
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph
from langchain.messages import HumanMessage, SystemMessage
from langgraph.types import Send
from typing import Annotated
import operator

class State(BaseModel):
    """定义状态"""
    messages: list = Field(default=[], description="保存agent执行过程中聊天记录")
    api_docs: str = Field(default="", description="接口的业务说明文档")
    # 接口所有测试点
    api_test_points: list = Field(default="", description="接口的测试点")
    # 自动化用例
    api_test_case: Annotated[list[str], operator.add] = Field(default="", description="接口的测试用例")
    # 用来生成自动化用例的测试点
    test_point: str = Field(default="", description="生成的测试点")


class WorkFlow:

    def __init__(self):
        # 初始化大模型
        model = ChatOpenAI(model=os.getenv("MODEL"))
        # 给模型绑定工具
        self.model = model

    # 提取测试点
    def extract_test_point(self, state: State):
        """提取测试点"""
        print("==================接口测试点提取======================")
        # 调用大模型去实现测试点的提取生成
        # api_doc = state.api_docs
        # system_prompt = """
        # 你是一个经验丰富的测试工程师，接下来需要你基于接口的业务说明文档，去系统全面的分析接口中所涉及到的测试点
        # 工作原则：
        #     1、所有的测试点都必须有事实依据，不得推测，或者杜撰文档中没有提及和明确说明的内容
        #
        # 返回的数据格式要求如下，为json格式，不要有过的的说明：
        # [
        #     {"name":"测试点的名称","decs":"测试点的描述"，"type":"测试点的类型"}
        # ]
        # """
        # user_message = f"""
        # 用户提交的接口业务说明文档如下：
        # {api_doc}
        # """
        # # 调用大模型
        # messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        #
        # # 调用大模型
        # ai_messages = self.model.invoke(messages)
        # 把生成的测试点添加到状态中
        return {"api_test_points": [
            {"name": "测试点1", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点2", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点3", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点4", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点5", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点6", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点7", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点8", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点9", "decs": "测试点1的描述", "type": "功能测试"},
            {"name": "测试点10", "decs": "测试点1的描述", "type": "功能测试"},
        ]}

    def generate_autotest_case(self, state: State):
        """生成自动化用例"""
        print("==================自动化用例生成======================")
        test_point = state.get("test_point")
        # 调用大模型去实现自动化用例生成

        print(f"正在为测试点{test_point}生成自动化用例")
        time.sleep(3)
        print(f"正在为测试点{test_point}生成自动化用例生成完毕")
        return {"api_test_case": [f"测试点{test_point}自动化用例"]}

    def auto_test_case_save(self, state: State):
        """保存自动化用例"""
        print("==================保存自动化用例======================")
        # 获取当前所有的自动化用
        api_test_case = state.api_test_case
        print(f"正在保存自动化用例：{api_test_case}")

    def router_func(self, state: State):
        """路由函数"""
        print("==================路由函数======================")
        api_test_points = state.api_test_points

        run_list = []
        # 获取当前节点的输出
        for i in api_test_points:
            run_list.append(Send("自动化用例生成", {"test_point": i.get("name")}))
        return run_list

    def create_workflow(self):
        """创建工作流"""
        graph = StateGraph(State)
        # 添加节点
        graph.add_node("接口测试点提取", self.extract_test_point)
        graph.add_node("自动化用例生成", self.generate_autotest_case)
        graph.add_node("自动化用例保存", self.auto_test_case_save)
        # 节点编排
        graph.add_edge(START, "接口测试点提取")
        graph.add_conditional_edges("接口测试点提取", self.router_func )
        graph.add_edge("自动化用例生成", "自动化用例保存")
        graph.add_edge("自动化用例保存", END)

        # 编译graph
        workflow = graph.compile()
        return workflow


if __name__ == '__main__':
    workflow = WorkFlow().create_workflow()
    response = workflow.invoke({"api_docs": "接口业务说明文档"})
    # for i in response:
    #     print(i)


"""

编排并发执行的节点：
    1、执行到某个节点之后，进入路由分发函数:graph.add_conditional_edges("节点"，"路由分发函数")
    
    2、在路由分发函数，return返回多个Send对象（一个Send对象就是一个并发）
        Send("并发执行的节点名"，给这个节点传递的参数{"key":value}--->参数会传给这个节点的state)

    3、并发节点执行完成之后，拿到的结果，怎么进行合并，就需要通过在State类里面去定义保存结果字段的合并机制：
        列表合并：Annotated[list[str], operator.add]
        字典合并：Annotated[dict, operator.or_]



langgraph的工作流：

    开始---》节点(Agent)--->节点（一个嵌套的工作流）----》节点 ---》结束


在设计嵌套工作流|agent节点的程序的时候，需要考虑的重点问题：
    父工作流(Agent)和子工作流(agent)之间的状态(State)如何保持一致(状态同步)。
    
    用来解决多智能体之间的通信机制(让多Agent系统的数据可以实现的进行传入和共享)
    

"""












