

# 创建大模型的调用对象
import os
import dotenv
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_openai import ChatOpenAI

dotenv.load_dotenv()

model = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    max_tokens=10000
)


@tool("写文件的工具函数", description="这个工具函数可以将内容写入文件，输入参数是文件路径和内容")
def write(file_path: str, content: str):
    """将内容写入文件"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


@tool("读文件的工具函数", description="这个工具函数可以读取文件内容，输入参数是文件路径")
def read(file_path: str) -> str:
    """从文件中读取内容"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
    

agent = create_agent(model=model, tools=[write, read])

user_prompt = "请帮我创建一个文件，文件名是test.txt，文件内容是Hello, World！"


response = agent.stream({"messages": [{"type": "human", "content": user_prompt}]}) 
for chunk in response:
    print(f"==========================================================================\n{chunk}")  # 实时输出模型的响应内容