from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import pymysql

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
    try:
        connent = pymysql.connect(host='127.0.0.1',
                                  port=3306,
                                  user='root',
                                  password='mysql',
                                  cursorclass=pymysql.cursors.DictCursor,
                                  db='agent',
                                  autocommit=True,
                                  )
        cursor = connent.cursor()
        cursor.execute(sql)
        connent.commit()
    except pymysql.err.OperationalError as e:
        return 0
    result = cursor.fetchall()
    cursor.close()
    connent.cursor()
    return result


class DBAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv('MODEL_NAME'),
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
            每一步执行完都需要去分析当前的执行进度，以及规划下一步的任务执行
            """
        )
        response = agent.stream({"messages": input})
        for item in response:
            print(item)


if __name__ == '__main__':
    # DBAgent().main("创建一个用户表，需要用户id，用户名，用户密码，用户邮箱，用户手机号，用户地址，用户性别这些字段")
    # DBAgent().main("往用户表里面插入10条数据")

    DBAgent().main("创建一个学生表，需要学生id，学生名，学生性别，学生年龄，学生手机号，学生邮箱，学生地址，学生生日，学生班级，学生部门这些字段，并往学生表中插入20条数据")

