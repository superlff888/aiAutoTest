# @Author  : 木森
# @weixin: python771

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
import dotenv
import os

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

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

database_info = {"工具": "add", '工具2': "multiply"}

# 注意：必须转化成字符串
prompt = str(PromptTemplate.from_template(
    "您是一位数学计算助手，请根据输入的指令和数据库数据{database_info}，选择合适的工具计算出结果"
).format(database_info=database_info)) # 将提示词模板需要的数据进行组装和格式化

# ===============创建一个agent==============
agent = create_react_agent(
    model=llm.bind_tools([add, multiply]),
    tools=[add, multiply],
    # 使用字符串，直接传模版对象会有问题
    prompt=prompt
)

# 模拟用户输入
user_input = "请计算1*2的结果"
# 从数据库检索相关信息
agent.with_config({"recursion_limit": 30}) # 设置最大递归次数
# 使用 HumanMessage 封装输入内容以符合类型要求
input_message = {
    "messages": [HumanMessage(content=user_input)],
    "input": user_input
}
# input_message = {"messages": [HumanMessage(content="请计算1*2的结果")]}  # 流式执行
response = agent.stream(input_message) # 设置最大递归次数
for item in response:
    print(item)
print(f"\n提示词：{prompt}")
# 获取agent执行的流程图谱，并保存为图片
res = agent.get_graph().draw_mermaid_png()
print(res)
with open("03langgraph开发Agent.png", "wb") as f:
    f.write(res)
