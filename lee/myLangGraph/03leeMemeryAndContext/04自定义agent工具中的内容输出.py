# @Author  : 木森
# @weixin: python771
from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
import pymysql
from threading import Lock
from langgraph.config import get_stream_writer

# 加载.env文件中的环境变量
dotenv.load_dotenv()


class DBSingleton:
    """数据库连接单例类"""
    _instance = None  # 类变量，用于存储唯一的实例
    _lock = Lock()    # 线程锁，确保多线程环境下的安全

    def __new__(cls):
        with cls._lock:  # 加锁，确保线程安全
            if cls._instance is None:  # 如果还没有创建实例
                # 创建新实例：调用父类的__new__方法创建实例
                cls._instance = super(DBSingleton, cls).__new__(cls)
                # 初始化这个实例（设置数据库连接）
                cls._instance._initialize_connection()
            return cls._instance  # 返回唯一的实例

    def _initialize_connection(self):
        """初始化数据库连接"""
        try:
            self.connection = pymysql.connect(
                host='127.0.0.1',
                port=3306,
                user='root',
                password='mysql',
                cursorclass=pymysql.cursors.DictCursor,
                db='agent',
                autocommit=True,
            )
            self.is_connected = True
        except pymysql.Error as e:
            self.is_connected = False
            print(f"数据库连接失败: {e}")

    def get_connection(self):
        """获取数据库连接"""
        if not self.is_connected:
            self._initialize_connection()
        return self.connection

    def close_connection(self):
        """关闭数据库连接"""
        if self.is_connected and self.connection:
            self.connection.close()
            self.is_connected = False

    def execute_query(self, sql):
        """执行SQL查询并返回结果"""
        if not self.is_connected:
            self._initialize_connection()
            if not self.is_connected:
                return None

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                return result
        except pymysql.Error as e:
            print(f"SQL执行错误: {e}")
            # 如果连接出现问题，尝试重新连接
            if "MySQL server has gone away" in str(e):
                self.close_connection()
                self._initialize_connection()
                if self.is_connected:
                    return self.execute_query(sql)  # 重试一次
            return None

# 创建全局数据库单例实例
db_singleton = DBSingleton()


# 第一步定义工具函数
@tool('数据库操作', description='连接数据库,执行sql语句，并返回执行的结果')
def mysql_executor(sql: str):
    """
    连接数据库，执行sql语句
    使用单例模式管理数据库连接，确保只有一个连接实例
    :param sql:
    :return:
    """
    writer = get_stream_writer()  # 流写入器对象，用于在智能体执行过程中记录和输出各种状态信息

    try:
        writer("【数据库操作工具】：使用单例数据库连接") # 记录并输出信息
        result = db_singleton.execute_query(sql)

        if result is None:
            writer("【数据库操作工具】：数据库操作失败")
            return "数据库操作失败，请检查数据库连接和SQL语句"

        writer(f"【数据库操作工具】：执行sql语句:{sql}")
        writer(f"【数据库操作工具】：sql语句执行成功！")
        writer(f"【数据库操作工具】：执行结果为：{result}")
        return result
    except Exception as e:
        writer(f"【数据库操作工具】：发生未知错误: {e}")
        return f"发生未知错误: {e}"


class DBAgent:

    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv('MODEL_NAME'),
            base_url=os.getenv('BASE_URL'),
            api_key=os.getenv('API_KEY'),
        )

    def main(self, input):
        agent = create_agent(
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

        # 2、只输出 自定义工具中 的输出内容
        response = agent.stream({"messages": input}, stream_mode="custom")
        for item in response:
            print(item)

        # # 3、输出所有内容
        # response = agent.stream({"messages": input}, stream_mode=["messages", "custom"])
        # for chunk, item in response:
        #     print(chunk)

    def __del__(self):
        """析构函数，确保程序结束时关闭数据库连接"""
        db_singleton.close_connection()
if __name__ == '__main__':
    # DBAgent().main("创建一个用户表，需要用户id，用户名，用户密码，用户邮箱，用户手机号，用户地址，用户性别这些字段")
    # DBAgent().main("往用户表里面插入10条数据")

    # DBAgent().main("创建一个学生表，需要学生id，学生名，学生性别，学生年龄，学生手机号，学生邮箱，学生地址，学生生日，学生班级，学生部门这些字段，并往学生表中插入20条数据")
    DBAgent().main("查询数据库中，学生表和用户表的表结构,再分别查询学生表和用户表的前10条数据")
