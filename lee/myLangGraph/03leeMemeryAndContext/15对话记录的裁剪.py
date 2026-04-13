from langchain_core.tools import BaseTool, tool
import dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
import pymysql


"""

messages = [
    SystemMessage(content="你是一个乐于助人的助手。"),
    HumanMessage(content="你好！请介绍一下法国的首都。"),
    AIMessage(content="法国的首都是巴黎，它是一座浪漫的城市。"),
    HumanMessage(content="太好了！那它有哪些著名的博物馆呢？"),
    AIMessage(content="巴黎最著名的博物馆是卢浮宫，里面藏有蒙娜丽莎。"),
    HumanMessage(content="谢谢你的信息！"),
]


**函数内部可能的工作流程：**
1.  **应用 `end_on`**：找到最后一个 `HumanMessage`（内容是 `"谢谢你的信息！"`），并忽略它之后的所有消息（这个例子中之后没有消息，所以没影响）。
2.  **应用 `strategy="last"`**：从末尾开始计算Token，尽可能保留最近的消息。
    *   它发现保留最后两条问答（`HumanMessage("太好了！那...")`, `AIMessage("巴黎最著名...")`, `HumanMessage("谢谢...")`）加起来已经有22个Token了。
    *   再往前保留一条 `AIMessage("法国的首都是...")` 就会超过25，但因为 `allow_partial=True`，它试图截取这条消息的一部分。
3.  **应用 `text_splitter`**：假设这条消息被分割成 `[“法国的首都是巴黎，”, “它是一座浪漫的城市。”]`。它只需要第2个片段（3个Token）就能凑到25 Token。
4.  **应用 `start_on`**：我们这个例子没设置 `start_on`，跳过。
5.  **应用 `include_system`**：函数检查当前结果。系统消息不在里面。因为它很重要且 `include_system=True`，函数会尝试把索引0的系统消息加回去。
    *   加回去后总Token数变成了 `6（系统） + 22 + 3 = 31`，超过了25。
    *   函数不得不从**当前结果的尾部**再剔除一些Token，以确保总Token数 ≤ 25。它可能会把刚才部分保留的消息片段再截短一些，或者干脆整个丢弃那条部分保留的消息，以保证系统消息和最近的一两条消息能放进去。
    
    
## 工作流程

1. **预处理**：根据`end_on`参数删除结束点之后的消息
2. **修剪核心**：
   - 如果策略是"last"：从后往前累加消息，直到达到token限制
   - 如果策略是"first"：从前往后累加消息，直到达到token限制
3. **后处理**：
   - 根据`start_on`参数删除开始点之前的消息
   - 处理系统消息（如果`include_system=True`）
   - 处理部分消息（如果`allow_partial=True`）
"""

# 加载.env文件中的环境变量
dotenv.load_dotenv()
from langchain_core.messages.utils import trim_messages, count_tokens_approximately


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
            每一步执行完都需要去分析当前的执行进度，以及规划下一步的任务执行
            """
        )
        response = agent.invoke({"messages": input})
        print(response)
        # 修剪节点：对智能体的输出进行裁剪，确保消息内容的总token数不超过限制
        result = trim_messages(
            response["messages"],
            strategy="last",  # 修剪策略：保留最后面的 max_tokens 个Token
            # 可以直接将模型对象传入(token_counter=llm)，函数内部会调用 llm.get_num_tokens_from_messages(some_messages) 来获取精确的 Token 数
            token_counter=count_tokens_approximately,  # 计算token数量的方法：使用官方推荐的近似方法approximate_token_counter进行近似的计数方法；如果设为len，则只计算消息数量而非token数
            max_tokens=1000,  # 修剪后，所有消息的Token总数不能超过这个数字
            # start_on、end_on：规定花园的有效区域
            start_on="human",  # 忽略第一次出现该类型之前的所有消息（找到第一个指定类型的消息，删除它之前的所有消息）
            end_on=("human", "tool"),  # 忽略最后一次出现该类型之后的所有消息（在哪种类型的消息处结束），可以指定消息类型（如"system", "human"）或消息类SystemMessage、HumanMessage，找到最后一个指定类型的消息，删除它之后的所有消息
            #  是否允许部分消息被裁剪
            allow_partial=False,  # 如果 allow_partial=False，这条消息可能因为太长而被整个丢弃。如果 allow_partial=True，那么只会截取这篇作文的最后几句话（如果 strategy="last"）保留下来。
            include_system=True,  # 门口的那块指示牌必须保留 --> 是否保留索引为0的系统消息（主要用于"last"策略）
        )
        print(result)
        return result


if __name__ == '__main__':
    # DBAgent().main("创建一个用户表，需要用户id，用户名，用户密码，用户邮箱，用户手机号，用户地址，用户性别这些字段")
    # DBAgent().main("往用户表里面插入10条数据")

    # DBAgent().main("创建一个学生表，需要学生id，学生名，学生性别，学生年龄，学生手机号，学生邮箱，学生地址，学生生日，学生班级，学生部门这些字段，并往学生表中插入20条数据")
    DBAgent().main("查询学生表和用户表中的数据中条数")
