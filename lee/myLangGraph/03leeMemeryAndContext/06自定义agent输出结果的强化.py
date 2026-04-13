# @Author  : 木森
# @weixin: python771
from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import pymysql

from langgraph.config import get_stream_writer

# 加载.env文件中的环境变量
dotenv.load_dotenv()


# 第一步定义工具函数
@tool('数据库操作', description='连接数据库,执行sql语句，并返回执行的结果')
def mysql_executor(sql: str):
    """
    连接数据库，执行sql语句
    需要先安装pymysql
    :param sql:
    :return:
    """
    writer = get_stream_writer()
    try:
        writer("【数据库操作工具】：开始连接数据库")
        connent = pymysql.connect(host='127.0.0.1',
                                  port=3306,
                                  user='root',
                                  password='mysql',
                                  cursorclass=pymysql.cursors.DictCursor,
                                  db='agent',
                                  autocommit=True,
                                  )
        cursor = connent.cursor()
        writer(f"【数据库操作工具】：执行sql语句:{sql}")
        cursor.execute(sql)
        connent.commit()
    except pymysql.err.OperationalError as e:
        writer(f"【数据库操作工具】：执行出现错误：{e}")
        return 0
    result = cursor.fetchall()
    writer(f"【数据库操作工具】：执行结果为：{result}")
    cursor.close()
    connent.cursor()
    return result


class DBAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv('MODEL'),
            base_url=os.getenv('BASE_URL'),
            api_key=os.getenv('API_KEY'),
        )

    def main(self, input):
        agent = create_react_agent(
            model=self.llm,
            tools=[mysql_executor],
            # # 这个是给智能体进行身份定位，和决策建议的提示词
            prompt="""
            你是一位资深的DBA，现在需要你根据用户的需求，编写对应的sql语句，调用数据库操作的工具，执行sql语句，并返回执行的结果,
            每一步执行完都需要去分析当前的执行进度，以及验证当前步骤是否执行成功，如果执行失败则进行分析执行失败的原因，
            并规划下一步的解决方案，直到任务完成
            """
        )
        # 1、只输出AI的结果
        # response = agent.stream({"messages": input}, stream_mode="messages")
        # for chunk, item in response:
        #     print(chunk.content, end='', flush=True)

        # 2、只输出自定义工具中的输出内容
        # response = agent.stream({"messages": input}, stream_mode="custom")
        # for item in response:
        #     print(item)
        # 3、输出所有内容
        response = agent.stream({"messages": input}, stream_mode=["messages", "custom"])
        for input_type, chunk in response:
            if input_type == "messages":
                # ai的输出内容
                print(chunk[0].content, end="", flush=True)
            elif input_type == "custom":
                # 工具执行的输出内容
                print(chunk)


if __name__ == '__main__':
    # DBAgent().main("创建一个用户表，需要用户id，用户名，用户密码，用户邮箱，用户手机号，用户地址，用户性别这些字段")
    # DBAgent().main("往用户表里面插入10条数据")

    # DBAgent().main("创建一个学生表，需要学生id，学生名，学生性别，学生年龄，学生手机号，学生邮箱，学生地址，学生生日，学生班级，学生部门这些字段，并往学生表中插入20条数据")
    DBAgent().main("查询数据库中，学生表和用户表的表结构,再分别查询学生表和用户表的前10条数据")
