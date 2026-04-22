
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
import os
from dotenv import load_dotenv

from langchain_community.utilities import SQLDatabase
from langchain.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI



load_dotenv()


llm = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),     
    temperature=0
    )   


def getdbtools():
    username = os.getenv("MYSQL_USERNAME")
    password = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    database = os.getenv("MYSQL_DATABASE")
    DATABASE_URI = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    print(f"数据库连接URI:{DATABASE_URI}")

    db = SQLDatabase.from_uri(DATABASE_URI)  # 初始化SQLDatabase对象。这个对象封装了与数据库的交互能力，能自动读取数据库的表结构（schema）信息，后续 Agent 需要依赖这些元数据来生成正确的 SQL
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)  # 创建 SQLDatabaseToolkit 工具包
    return toolkit.get_tools()  # return工具列表


agent = create_agent(
    tools=getdbtools(),
    model=llm,
    system_prompt=SystemMessage(content="你是一个SQL专家，协助用户查询数据库中的表结构信息，并生成正确的SQL查询语句") 
)


human_message=HumanMessage(content="请帮我查询一下数据库中有哪些表？")


chunk = agent.stream(
    {"messages":[human_message]},
    stream_mode="updates",
    version="v2"  # dict
    )

for item in chunk:
    print(f"============================================================\n{item}")
# for step,data in chunk.items():
#         if step == "model":
#             print('=================【调用大模型执行结果】=====================')
#         elif step == "tools":
#             print('====================【调用工具返回结果】=====================')
#         for block in data['messages'][-1].content_blocks:
#             if block['type'] == "text":
#                 print(block['text'])
#             elif block['type'] == "tool_call":
#                 print(f"计划调用工具:{block['name']},参数为：{block['args']}")




