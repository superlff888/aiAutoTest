# @Author  : 木森
# @weixin: python771
# @Author  : 木森
# @weixin: python771
from langchain_core.tools import BaseTool, tool
import dotenv
import os

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore
from langgraph.config import get_store

"""
Agent本身不会自动存储记忆，所以该文件第二轮不晓得第一轮的问题
"""

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 长期记忆(内存存储)
memory = InMemoryStore()

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
    store = get_store()  # 获取记忆对象
    # 在工具中往记忆中写入内容
    store.put(namespace=("user_id", "thread_id"), key="tools",
              value={"add": add, "content": f"调用工具进行计算{a}+{b}的值"})
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


# prompt = PromptTemplate(
#     template="""您是一位数学计算助手,请根据输入的指令，选择合适的工具计算出结果,请计算2+1的结果""",
# )


# ===============创建一个agent==============
agent = create_react_agent(
    model=llm.bind_tools([add, multiply]),
    tools=[add, multiply],
    # 使用字符串，之前传入模版会有问题
    prompt="您是一位数学计算助手,请根据输入的指令，选择合适的工具计算出结果,",
    store=memory,  # 配置记忆存储对象，用来进行长期记忆的存储
)

"""
agent中会自动记忆单轮任务中多次和大模型交互的信息(比如add、multiply)
"""

# =====================多轮对话====================
print("===================第一轮========================")
response = agent.stream(
    {"messages": [{"role": "user", "content": "请计算2+1的结果"}]},
    stream_mode="messages" # 注意：stream_mode=["messages"]
)
for item, metadata in response:
    print(item.content, end='') # 注意：stream_mode=["messages"]时，item[0].content

print("\n===================第二轮========================")
response = agent.stream({"messages": [{"role": "user", "content": "我上一个问题是什么"}]},
                        stream_mode="messages"
                        )
for item, metadata in response:
    print(item.content, end='')
