# @Author  : 木森
# @weixin: python771

from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer
from langgraph.prebuilt import create_react_agent
from dataclasses import dataclass

from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.runtime import get_runtime

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)


# agent中的状态管理参数类需要继承AgentState类
@dataclass
class CustomState(AgentState):
    """自定义的运行时上下文参数"""
    system_role: str


@tool
def get_user_info():
    """获取用户信息的工具"""
    runtime = get_runtime()
    role = runtime.context['system_role']
    print("当前系统的角色：", role)
    writer = get_stream_writer()
    writer(f"【工具中自定义的输出内容】:99999999999999")
    return "用户名是张三"


def get_system_prompt(state: CustomState):
    """获取系统提示词"""
    # 获取上下文数据
    runtime = get_runtime()
    role = runtime.context['system_role']
    # 获取用户传入的提示词内容
    user_prompt = state['messages']
    # print("用户输入的提示词：", user_prompt)
    return [
        {"role": "system", "content": f"您是一位{role}，请站在{role}的角度上去回答用户的问题"},
        *user_prompt
    ]


# 创建一个agent
agent = create_react_agent(
    model=llm,
    tools=[get_user_info],
    prompt=get_system_prompt,
    context_schema=CustomState  # 指定运行时上下文参数类
)

response = agent.stream(input={"messages": [{"role": "user", "content": "获取用户名称"}]},
                        context={"system_role": "医生"},
                        stream_mode=["messages", "custom"]
                        )
for input_type, chunk in response:
    if input_type == "messages":
        # ai的输出内容
        print(chunk[0].content, end="", flush=True)
    elif input_type == "custom":
        # 工具执行的输出内容
        print(chunk)
