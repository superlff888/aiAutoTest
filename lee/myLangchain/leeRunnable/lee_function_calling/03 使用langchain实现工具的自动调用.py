#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : 03 使用langchain实现工具的自动调用.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/24 22:45
# @Desc    : AI大模型应用开发理论基础
# ========================================================


"""
langchain中的工具function calling的具体实现

# 工具的本质其实就是一个函数

# 工具的定义:
    方式一：使用装饰器@tool

    方式二：继承BaseTool这个类，自定义工具类
"""

from langchain_core.tools import tool
import dotenv
import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model="Qwen/Qwen3-14B",
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)

prompt = PromptTemplate(
    input_variables=["name"],
    # 样本中含有花括号，则需要额外使用花括号将原来花括号括起来，进行转义
    template="""
    # 角色定位
    你是一个智能助手，现在你需要获取用户信息，请根据用户输入的用户名，获取用户信息，返回格式为json，格式如下：
    {{
        "name": "用户名",
        "age": "用户年龄",
        "sex": "用户性别"
    }}
    # 用户输入
    {name}
    # 输出
    """,
)


# =========================定义工具函数方式1=========================
@tool
def get_user_sex(name: str) -> str:
    """获取用户性别"""
    print("工具接收到的参数为：", name)
    return f"名字叫张三，性别：男"


@tool
def get_user_age(name: str) -> str:
    """获取用户年龄"""
    print("工具接收到的参数为：", name)
    return f"名字叫张三，年龄：18"


# 保存工具名称和对应工具函数的映射关系
tool_map = {
    "get_user_sex": get_user_sex,
    "get_user_age": get_user_age,
}


# 进行工具调用的处理Runnable对象
def function_calling_handler(response):
    """处理工具调用"""
    tool_list = response.tool_calls

    # 保存工具调用的结果
    tool_call_result = []

    # 遍历工具列表,进行调用
    for tool in tool_list:
        # 根据工具名称获取对应的工具函数
        func = tool_map[tool.get("name")] # key只是一个用于映射的字符串，value才是具体函数名
        # 获取调用工具的时候，需要的参数
        args = tool.get("args")
        # 调用工具函数，获取工具函数的返回结果
        result = func.invoke(args)  # @tool装饰的函数，其实返回Runnable，可以调用invoke方法
        print(f"工具{tool.get('name')}调用的结果为:{result}")
        tool_call_result.append(result)

    return tool_call_result


def get_llm_and_tool(tool_result):
    """获取大模型和工具调用的结果"""
    # 获取原来提示词的内容，再在上面添加工具调用结果
    prompt_content = prompt.invoke({"name": "张三"})
    print("工具调用之前的提示词：", prompt_content)
    new_prompt = str(prompt_content) + "\n" + str(tool_result)
    print("工具调用之后的提示词：", new_prompt)
    # 使用大模型输出结果
    return llm.invoke(new_prompt)


# 给大模型绑定工具，再调用大模型输出结果
llm_with_tool = llm.bind_tools(tools=[get_user_sex, get_user_age])

tool_run = RunnableLambda(function_calling_handler)

# 大模型获取工具调用结果，返回最终的内容
get_result = RunnableLambda(get_llm_and_tool)

# 构建工具调用的完整链路
chain = prompt | llm_with_tool | tool_run | get_result

response = chain.invoke({"name": "张三"})
print("==================最终大模型输出结果==================")
print(response.content)
# 注意点：只有支持function calling的模型才可以使用工具，否则会报错

"""
bind_tools只是绑定了大模型，并没有调用工具！！！
llm_with_tool调用了了绑定外部工具的大模型，但是并没有调用外部工具
=============================================================
chain.invoke() 
  ↓
执行 prompt | llm_with_tool
  ↓
调用大模型（携带工具定义信息）
  ↓
大模型返回响应（可能包含 tool_calls）
"""
