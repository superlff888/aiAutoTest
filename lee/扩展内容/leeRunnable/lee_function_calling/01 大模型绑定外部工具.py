# @Author  : 木森
# @weixin: python771
"""
langchain中的工具function calling的具体实现

# 工具的本质其实就是一个函数

# 工具的定义:
    方式一：使用装饰器@tool

    方式二：继承BaseTool这个类，自定义工具类
"""

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

prompt = PromptTemplate(
    input_variables=["name"],
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


# 在没有给大模型绑定工具的情况下，输出的结果
# chain = prompt | llm
# response = chain.invoke({"name": "张三"})
# print(response.content)


# =========================定义工具函数=========================
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


# 给大模型绑定工具，再调用大模型输出结果
llm_with_tool = llm.bind_tools(tools=[get_user_sex, get_user_age])
chain = prompt | llm_with_tool
response = chain.invoke({"name": "张丽"})

print("大模型返回response：\n", response)
print("需要调用的工具", response.tool_calls)

# 注意点：只有支持function calling的模型才可以使用工具，否则会报错

"""
bind_tools只是绑定了大模型，并没有调用工具
"""

