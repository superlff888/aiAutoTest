# @Author  : 木森
# @weixin: python771

import os

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import dotenv
from langmem import create_manage_memory_tool, create_search_memory_tool

# 加载.env文件中的环境变量
dotenv.load_dotenv()
from langgraph.store.memory import InMemoryStore

# 长期记忆(内存存储)
memory = InMemoryStore()

# 创建一个React Agent，如果定义的state参数，那么在使用的时候，就可以在input输出内容中传递state中定义的字段
agent = create_react_agent(
    model=ChatOpenAI(
        model=os.getenv('MODEL_NAME'),
        base_url=os.getenv('BASE_URL'),
        api_key=os.getenv('API_KEY'),
    ),
    store=memory,  # 配置长期记忆对象
    # 配置langmem提供的长期记忆管理工具
    tools=[  # 随着对话内容的积累，内容会越来越多，智能体无法全部记住，所以智能体不是将所有对话记住，而是做选择性记忆，我们可以主动提示智能体需要记忆的内容，比如“请记住……”；一般的提示词不会记住
        # 创建一个长期记忆管理工具
        create_manage_memory_tool(("user_id1", "thread_id1")),
        # 创建一个长期记忆搜索工具
        create_search_memory_tool(("user_id1", "thread_id1"))
    ]
)
# ====================================会自动记住内容的的案例==========================================

# # 随着对话信息越来越多，智能体会做选择性记忆，因此我们需要主动提示智能体需要记忆的内容，避免存储过多的内容或遗漏所需信息
# response = agent.stream({"messages": [{"role": "user", "content": "请记住我叫木森，今年18岁"}]}, stream_mode="messages")
# for chunk in response:
#     print(chunk[0].content, end='')
#
# print("\n==================第二轮交互=====================")
#
# response2 = agent.stream({"messages": [{"role": "user", "content": "你还记得我叫什么名字吗"}]}, stream_mode="messages")
# for chunk in response2:
#     print(f'{chunk[0].content}', end='')

# =============================提示词未触发长期记忆====================================

response = agent.stream({"messages": [{"role": "system", "content": "今天是8月31号吗？"}]},
                        stream_mode="messages")
for chunk in response:
    print(chunk[0].content, end='')

print("\n==================第二轮交互=====================")

response2 = agent.stream({"messages": [{"role": "user", "content": "今天是几号？"}]}, stream_mode="messages")
for chunk in response2:
    print(chunk[0].content, end='')
