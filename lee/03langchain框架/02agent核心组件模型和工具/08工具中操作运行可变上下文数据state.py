

import os
from typing import Optional

import dotenv
from langchain.agents import AgentState, create_agent
from langchain.messages import HumanMessage, SystemMessage
from langchain.tools import ToolRuntime, tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from langgraph.config import get_stream_writer
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore


dotenv.load_dotenv()

llm=ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),     
    temperature=0
    ) 


class LeeState(AgentState):
    username: str = "Lee"


class WriterParams(BaseModel):
    content: str = Field(description="要写入文件的内容")
    file_path: str = Field(description="要写入的文件路径")
    # file_path: Optional[str] = Field(None, description="要读取的文件路径（不传则使用默认路径）")


class ReaderParams(BaseModel):
    file_path: str = Field(...,description="要读取的文件路径")  


@tool("写文件的工具", description="写文件的工具，用于将内容写入文件", args_schema=WriterParams)
def write_file(file_path: str, content: str, runtime: ToolRuntime):
    NAME = runtime.state.get("username",{})  # 工具中获取上下文中自定义的字段数据username
    print(f'-----------------------我是{NAME}------------------------')
    messages = runtime.state.get("messages",{})
    print(f"======================================\n历史消息:\n {messages}")  # 用户消息、AI消息
    print("工具正在运行中...")
    writer = get_stream_writer()
    writer(f"正在写入文件：{file_path}")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        writer(f"文件写入完成")

@tool("读文件的工具", description="读文件的工具，用于读取文件内容", args_schema=ReaderParams)
def read_file(file_path: str):
    print("工具正在运行中...")
    writer = get_stream_writer()
    writer(f"正在读取文件：{file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        content_text = f.read()
        writer(f"文件读取完成，内容为：{content_text}")


agent = create_agent(
    model=llm,
    tools=[write_file, read_file],
    state_schema=LeeState,
    checkpointer = InMemorySaver(),
    store = InMemoryStore()
)


user_prompt = HumanMessage(content="请将'Hello, World!'写入hello.txt文件中，然后再读取该文件的内容。")

response = agent.stream(
    {"messages":[user_prompt], "username": "Lee"},
    system_prompt=SystemMessage(content="你是一名全能助手"),
    config={"configurable": {"thread_id": 1000}},
    stream_mode=['custom', 'updates', 'messages'],
    version="v2"
    )

for item in response:
    # print("=====================================================================\nagent response:\n", item)
    if item["type"] == "custom":
        print("=====================================================================\nagent custom:\n", item["data"])
    elif item["type"] == "updates":
        if "model" in item["data"]:
            if hasattr(item["data"]["model"]["messages"], "content") and item["data"]["model"]["messages"].content not in ("null", "None", ""):
                print("=====================================================================\nagent updates:\n", item["data"]["model"]["messages"].content)  # 打印最新的工具调用更新
        else: 
            print("=====================================================================\nagent updates调用工具:\n", item["data"]["tools"]["messages"][0].name)  # 打印最新的工具调用更新
    elif item["type"] == "messages":  # 布尔上下文中 item["data"][0].content 为真值表示 content 不为空
        if hasattr(item["data"][0], "content") and item["data"][0].content and item["data"][0].content not in ("null", "None", "<think>", "</think>"): 
            print("=====================================================================\nagent messages:", item["data"][0].content)  # 打印最新的消息更新
    


