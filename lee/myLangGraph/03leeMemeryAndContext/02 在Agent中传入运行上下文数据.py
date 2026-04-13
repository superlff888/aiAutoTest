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

from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dataclasses import dataclass

from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.runtime import get_runtime, Runtime

"""
使用方式：
1. 传入上下文数据：通过agent.invoke()方法，传入参数字典类型的context
2. AgentState状态包含整个工作流中涉及到的输入、输出、节点之间共享的数据

"""

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

"""
02lee: 
@dataclass上下文管理 与 AgentState状态类也可以用两个不同类维护

@dataclass
class ContextSchema:
    user_name: str
    
# 定义运行时的上下文参数
# 定义agent的state
class CustomState(AgentState):
    input_value: str
 """
# 01musen: Agent中的状态管理参数类 需要继承AgentState类，AgentState与工作流State(GraphState)不是一回事, 一般用于传运行时的一些不需要修改的值，比如项目id、接口id等,要是非要改的话,也是可以改的
@dataclass
class ContextSchema(AgentState): # 既可以通过运行时上下文Runtime获取上下文信息，也可以通过AgentState状态获取上下文信息
    """
    自定义的运行时上下文参数：智能体在agent.stream运行开始时传入的静态数据
    继承AgentState: 既是运行时上下文参数，又是AgentState状态可通过用户输入（对应input参数）；既可以通过运行时上下文Runtime获取上下文信息，也可以通过AgentState状态获取上下文信息
    不继承AgentState: 只是运行时上下文参数（对应context参数），仅可以通过运行时上下文Runtime获取上下文信息
    """
    system_role: str
    user_prompt: str  # messages也可以


@tool
def get_user_info():
    """获取用户信息的工具"""
    runtime = get_runtime()  # 获取运行时上下文信息数据
    role = runtime.context['system_role']
    print("当前系统的角色：", role)

    return "用户名是张三"

def generator_test_case(state: ContextSchema): # AgentState状态类
    """生成测试用例"""
    print(f"用户输入的需求是:{state.get('messages')},开始进行测试用例生成")
    # 这里核心的功能实现需要调用llm进行生成，暂时跳过
    print("测试用例已经生成")
    return {"test_cases": ["测试用例1", "测试用例2"]}

# def generator_test_case2(runtime: Runtime[ContextSchema]):  # @dataclass装饰的状态类决定了运行时上下文Runtime
#     """生成测试用例"""
#     print(f"用户输入的需求是:{runtime.context.get('messages')},开始进行测试用例生成")
#     # 这里核心的功能实现需要调用llm进行生成，暂时跳过
#     print("测试用例已经生成", )
#     return {"test_cases": ["测试用例1", "测试用例2"]}

# def generator_test_case3():  # @dataclass装饰的状态类决定了运行时上下文参数runtime
#     """生成测试用例"""
#     runtime = get_runtime() # 获取运行时上下文信息数据
#     # runtime = get_runtime(ContextSchema)  # 也可以这样写，但是好像没必要传ContextSchema
#     print(f"用户输入的需求是:{runtime.context.get('messages')},开始进行测试用例生成")
#     # 这里核心的功能实现需要调用llm进行生成，暂时跳过
#     print("测试用例已经生成", )
#     return {"test_cases": ["测试用例1", "测试用例2"]}

# state"状态函数"的参数是state，state是继承AgentState类的类ContextSchema
def get_prompt(state):
    """获取系统提示词和用户提示词"""
    runtime = get_runtime()  # 获取上下文信息数据
    role = runtime.context['system_role']
    # state状态：整个工作流中涉及到的输入、输出、节点之间共享的数据
    user_prompt = state['messages']  # 获取用户传入的提示词内容
    print("用户输入的提示词：", user_prompt)
    return [
        {"role": "system", "content": f"您是一位{role}，请站在{role}的角度上去回答用户的问题"},
        *user_prompt
    ]


# 创建一个agent
agent = create_react_agent(
    model=llm,
    tools=[get_user_info],
    prompt=get_prompt, # 指定提示词: 可以传文字，也可以传 方法名实现自动调用该方法
    context_schema=ContextSchema  # 指定运行时上下文参数类，猫这一类动物 Animal[Cat]
)

response = agent.stream({"messages": [{"role": "user", "content": "获取用户名称"}]},
                        context={"system_role": "医生"})
for item in response:
    print(item)
