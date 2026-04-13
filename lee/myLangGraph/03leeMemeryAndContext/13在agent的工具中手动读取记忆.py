# @Author  : 木森
# @weixin: python771
import os

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import dotenv
from langgraph.config import get_store
from pydantic import BaseModel

# 加载.env文件中的环境变量
dotenv.load_dotenv()
from langgraph.store.memory import InMemoryStore

# 长期记忆(内存存储)
memory = InMemoryStore()


class UserInfo(BaseModel):
    name: str
    age: int


@tool
def get_user_info(config: RunnableConfig):
    """获取用户信息"""
    print("执行工具：get_user_info")
    store = get_store()
    # 获取状态中的user_id
    user_id = config["configurable"].get("user_id")
    thread_id = config["configurable"].get("thread_id")
    userinfo = store.get((user_id, thread_id), "name")
    print("工具get_user_info执行的结果：",userinfo)
    return userinfo


@tool
def save_user_info(user_info: UserInfo, config: RunnableConfig) -> str:
    """保存用户信息"""
    print("执行工具:save_user_info")
    store = get_store()  # 获取记忆对象
    user_id = config["configurable"].get("user_id")  # 从运行配置中获取用户id
    thread_id = config["configurable"].get("thread_id")  # 从运行配置中获取线程id

    store.put((user_id, thread_id), "name", dict(user_info))
    return "用户信息保存成功"


# 创建一个React Agent，如果定义的state参数，那么在使用的时候，就可以在input输出内容中传递state中定义的字段
agent = create_react_agent(
    model=ChatOpenAI(
        model=os.getenv('MODEL_NAME'),
        base_url=os.getenv('BASE_URL'),
        api_key=os.getenv('API_KEY'),
    ),
    store=memory,
    tools=[save_user_info, get_user_info])  # 自动调用tool工具

response = agent.stream(input={"messages": [{"role": "user", "content": "请记住我叫木森，今天18岁"}]},
                        # 在运行配置中传入运行的配置参数
                        config={"configurable": {"user_id": "user_123", "thread_id": "musen001"}},
                        stream_mode="messages"
                        )
for chunk, item in response:
    print(chunk.content, end="")
print()

print("================第二次提问===================")
response2 = agent.stream(input={"messages": [{"role": "user", "content": "获取用户信息"}]},
                         # 在运行配置中传入运行的配置参数
                         config={"configurable": {"user_id": "user_123", "thread_id": "musen001"}},
                         stream_mode="messages"
                         )
for chunk, item in response2:
    print(chunk.content, end="")
