

from langchain.tools import tool
import os
import dotenv
from pydantic import BaseModel, Field

# 将.env文件加载到环境变量中
dotenv.load_dotenv()
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from langgraph.config import get_stream_writer

# 创建大模型的调用对象
model = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    max_tokens=10000
)


class WriterParam(BaseModel):
    file_path: str = Field(..., description="要写入的文件路径")
    content: str = Field(..., description="要写入的内容")


@tool("write_to_file", description="将内容写入指定文件")
def write_to_file(file_path: str, content: str):
    writer = get_stream_writer()  # 获取写入器,这个写入器会将日志输出到控制台
    writer(f"正在将内容写入文件: {file_path}")  # writer回调函数
    with open(file_path, 'a', encoding='utf-8') as f:
        f.write(content + '\n')
    return f"内容已写入到 {file_path}"  

agent = create_agent(
    tools=[write_to_file],
    model=model,
    system_prompt=SystemMessage(content="你是一个文件写入助手，协助用户将内容写入指定的文件中")
)   

human_message = HumanMessage(content="请将'Hello, World!'写入到当前目录下的hello.txt文件中。")  
response = agent.stream(
    {"messages":[human_message]},
    stream_mode=["custom", "updates"],
    version="v2"
    )

for chunk in response:
    print(chunk)





"""
七个 stream_mode 的区别：

1. values — 每次输出的是完整的当前状态。就像每写一步都给你看一遍"现在的局面全貌"，数据会越来越大。

2. updates — 每次只输出这一步新增/改变的内容。相当于只看"刚才发生了什么变化"，更精简。

3. checkpoints — 输出的是检查点信息（用于断点续传/恢复）。主要是内部持久化用的，一般用户不太需要关心。

4. tasks — 输出的是即将要执行的任务信息。告诉你"下一步打算干什么"，适合做进度提示。

5. debug — 输出的是调试信息，包含每一步的执行细节、时间、错误等。排错的时候用，信息量最大最杂。

6. messages — 输出的是对话消息流，包括 LLM 的 token 流、工具调用等。适合做实时展示，比如打字机效果。

7. custom — 输出的是你自己通过 get_stream_writer() 写入的自定义内容


"""