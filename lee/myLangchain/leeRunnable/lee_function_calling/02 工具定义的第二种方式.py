# @Author  : 木森
# @weixin: python771

from langchain_core.tools import tool, BaseTool
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


class AddTool(BaseTool):
    """实现两个数字相加"""

    def _run(self, a: int, b: int):
        return a + b


llm.bind_tools(tools=[AddTool()])