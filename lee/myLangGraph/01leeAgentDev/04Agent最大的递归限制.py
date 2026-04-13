# @Author  : 木森
# @weixin: python771
from langchain_core.tools import BaseTool, tool
import dotenv
import os

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()
# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL_NAME'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)


@tool("加法计算", description="计算数值相加的工具")
def add(a: int, b: int) -> int:
    """
    计算两个数值相加的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    print("正在执行工具：add")
    return a + b


@tool("乘法计算", description="计算数值相加的工具")
def multiply(a: int, b: int) -> int:
    """
    计算两个数值相乘的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    print("正在执行工具：multiply")
    return a * b


# ===============创建一个agent==============
agent = create_react_agent(
    # 绑定模型
    model=llm.bind_tools([add, multiply]),
    # 绑定工具
    tools=[add, multiply],
    # 使用字符串，直接传模版对象会有问题
    prompt=PromptTemplate(template="您是一位数学计算助手，请根据输入的指令，选择合适的工具计算出结果,请计算1*2的结果"),
)
# 设置默认最大递归次数
agent = agent.with_config({"recursion_limit": 30})

# 在执行的时候去设置最大递归的次数
response = agent.stream({"messages": [{"role": "user", "content": "请计算1*2的结果"}]},
                        {"recursion_limit": 30}
                        )
for item in response:
    print(item)
