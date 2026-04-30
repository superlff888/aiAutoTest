

import os

from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase


def getdbtools(model):
    username = os.getenv("MYSQL_USERNAME")
    password = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST")
    port = os.getenv("MYSQL_PORT")
    database = os.getenv("MYSQL_DATABASE")
    DATABASE_URI = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    print(f"\n数据库连接URI:{DATABASE_URI}\n\n")

    db = SQLDatabase.from_uri(DATABASE_URI)  # 初始化SQLDatabase对象。这个对象封装了与数据库的交互能力，能自动读取数据库的表结构（schema）信息，后续 Agent 需要依赖这些元数据来生成正确的 SQL
    toolkit = SQLDatabaseToolkit(db=db, llm=model)  # 创建 SQLDatabaseToolkit 工具包
    return toolkit.get_tools()  # return工具列表

