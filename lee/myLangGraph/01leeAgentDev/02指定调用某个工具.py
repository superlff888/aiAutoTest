# @Author  : 木森
# @weixin: python771
from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model_name=os.getenv('MODEL_NAME_QWEN3'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)


@tool("add01", description="计算数值相加的工具")
def add(a: int, b: int) -> int:
    """
    计算两个数值相加的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    print("正在执行工具: add")
    return a + b


@tool
def multiply(a: int, b: int) -> int:
    """
    计算两个数值相乘的工具
    :param a: 数值a
    :param b: 数值b
    :return:
    """
    print("正在执行工具: multiply")
    return a * b


# 直接执行工具函数 ，工具也是langchain的Runnable对象
# res = add.invoke({"a": 10, "b": 2})
# print(res)

# 绑定工具
llm_tool = llm.bind_tools(tools=[add, multiply], tool_choice="auto") # 优先使用“multiply”


print("="*50)
print(llm_tool.invoke("请计算10和2的乘积结果"))

## langchain  中的agent
