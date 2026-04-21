

# 创建大模型的调用对象
import os

from langchain_openai import ChatOpenAI


model = ChatOpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    model=os.getenv("MODEL_NAME_R1"),
    max_tokens=10000
)


