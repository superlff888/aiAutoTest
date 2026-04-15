

import os
import dotenv
from langchain_openai import ChatOpenAI


# 加载环境变量文件
dotenv.load_dotenv()


llm = ChatOpenAI(
    model = os.getenv("OPENAI_MODEL"),
    api_key = os.getenv("OPENAI_API_KEY"),
    base_url = os.getenv("OPENAI_BASE_URL")
    )

response = llm.invoke("你好")
print(response.content)

for chunk in llm.stream("你好，你能在测试领域做什么？"):
    print(chunk.content, end="")
