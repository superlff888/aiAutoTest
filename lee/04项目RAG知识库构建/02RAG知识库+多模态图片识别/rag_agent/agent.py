# @Author  : 木森
# @weixin: python771
import os
import dotenv
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from rag_agent.rag_tools import lightrag_query

dotenv.load_dotenv()

# 初始模型配置
model = init_chat_model(
    model_provider="openai",
    model=os.getenv("MODEL2"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    temperature=0.5,
)

# 快速创建一个agent
agent = create_deep_agent(
    model=model,
    # 通过工具接入知识库系统
    tools=[lightrag_query],
    system_prompt="""
    你是一个专业的用例设计助手，可以根据用户的要求，从知识库中查询相关需求的详细文档信息，然后进行用例设计
    """
)

# 使用agent进行问答
response = agent.stream({
    "messages": [{
        "role": "user",
        "content": "给订单查询功能 设计详细的测试用例"
    }]
},
    stream_mode=["updates", "messages"],
    version="v2",
)

for chunk in response:
    if chunk["type"] == "messages":
        print(chunk["data"][0].content,end='')

