

"""
源码追溯stream()方法的入参InputT：
1. 需要先找到create_agent()函数的定义，查看其返回值类型是什么
2. create_agent()的返回是CompiledStateGraph[AgentState[ResponseT], ContextT, _InputAgentState, _OutputAgentState[ResponseT]]，顺序固定、个数固定、每个位置类型不同
3. 然后我再按住ctrl+左击”CompiledStateGraph“，查看该类的定义，发现定义为：class CompiledStateGraph(
    Pregel[StateT, ContextT, InputT, OutputT],
    Generic[StateT, ContextT, InputT, OutputT],
)，说明CompiledStateGraph继承了Pregel

泛型理解：
父类的泛型与子类泛型应该是一一对应的，且"壳子"里的泛型参数个数和顺序应该和父类一致，所以子类CompiledStateGraph[AgentState[ResponseT], ContextT, _InputAgentState, _OutputAgentState[ResponseT]]中的泛型参数应该是按照父类Pregel[StateT, ContextT, InputT, OutputT]的顺序来对应的，而StateT, ContextT, InputT, OutputT只是占位符，真正的类型是在创建agent时传入的ResponseT, ContextT, _InputAgentState, _OutputAgentState[ResponseT]

可以参照元组来理解：
顺序固定、个数固定、每个位置类型不同
tuple[str, int, bool]	固定长度、固定类型、固定顺序的元组
例如：
t: tuple[str, int, bool] = (123, "hello", True)  # 顺序错了
t: tuple[str, int, bool] = ("a", "b", False)     # 第二个不是 int
t: tuple[str, int, bool] = ("a", 1)              # 长度不够

"""




import dotenv
import os
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage, AIMessage
from langchain.agents import create_agent
from langchain.tools import tool

# 加载环境变量
dotenv.load_dotenv()

# 初始化大模型对象
model = ChatOpenAI(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL")
)

system_prompt = """
你是一位有10年经验的资深软件测试工程师，精通测试需求分析，以“功能正常+边界+异常”为主线思维指导生成测试点。
    样本示例：
    用户输入：
    
	需求文档：
       #####  功能背景
        新用户通过注册方式创建账户，支持邮箱/用户名+密码的注册方式。
        #####  主流程
        1. 用户打开注册页，填写注册信息
        2. 系统校验格式与唯一性（用户名、邮箱）
        3. 提交注册，后台创建账户，初始状态为“正常”
        4. 注册成功后自动登录并跳转首页
        ##### 异常流程
        - 邮箱/用户名已被注册：提示“已存在”
        - 两次密码不一致：提示用户重新输入
        ##### 业务规则
        - 用户名唯一，支持 4~20 位字母数字组合
        - 密码长度不少于 6 位
    	- 邮箱必须符合格式 `xxx@xxx.xx`
    输出：
       	| 用例编号   | 用例名称           | 前置步骤     | 测试步骤                                                     | 输入数据                                                     | 预期结果                                                | 实际结果 | 备注     |
        | ---------- | ------------------ | ------------ | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------- | -------- | -------- |
        | TC_REG_001 | 邮箱注册成功       | 无           | 1. 打开注册页面 2. 输入合法邮箱 `test123@example.com` 3. 输入合法密码 `Pass123` 4. 确认密码输入 `Pass123` 5. 点击“注册”按钮 | 邮箱：test123@example.com 密码：Pass123 确认密码：Pass123    | 注册成功，自动跳转至首页，用户保持登录状态              |          | 正向用例 |
        | TC_REG_002 | 用户名注册成功     | 无           | 1. 打开注册页面 2. 输入合法用户名 `user123` 3. 输入合法密码 `Abcd1234` 4. 确认密码输入一致 5. 点击“注册”按钮 | 用户名：user123 密码：Abcd1234 确认密码：Abcd1234            | 注册成功，自动跳转至首页，用户保持登录状态              |          | 正向用例 |
        | TC_REG_003 | 密码符合要求       | 无           | 1. 打开注册页面 2. 输入用户名或邮箱 3. 输入密码 `Pass123`（长度 ≥6） 4. 输入相同确认密码 5. 点击“注册” | 用户名：user567 密码：Pass123 确认密码：Pass123              | 表单验证通过，允许提交，注册成功跳转首页                |          | 正向用例 |
        | TC_REG_004 | 注册后自动登录跳转 | 无           | 1. 打开注册页面 2. 输入合法注册信息并完成注册 3. 注册完成后观察页面跳转和登录状态 | 任意有效注册信息                                             | 注册成功后跳转至首页，用户已处于登录状态                |          | 正向用例 |
        | TC_REG_005 | 邮箱格式错误       | 无           | 1. 打开注册页面 2. 输入非法邮箱 `test.example.com` 3. 输入合法密码 4. 点击“注册” | 邮箱：test.example.com 密码：Pass123 确认密码：Pass123       | 提示“邮箱格式错误”，不允许提交                          |          | 反向用例 |
        | TC_REG_006 | 邮箱已被注册       | 邮箱已注册   | 1. 打开注册页面 2. 输入已注册邮箱 `exist@example.com` 3. 输入密码 4. 点击“注册” | 邮箱：exist@example.com 密码：Pass123 确认密码：Pass123      | 提示“邮箱已存在”，不允许注册                            |          | 反向用例 |
        | TC_REG_007 | 用户名格式错误     | 无           | 1. 打开注册页面 2. 输入非法用户名（如 `user@123`） 3. 输入密码 4. 点击“注册” | 用户名：user@123 或 us 或 超过20位的用户名 密码：Pass123 确认密码：Pass123 | 提示“仅支持字母数字”或“用户名需4-20位”，注册失败        |          | 反向用例 |
        | TC_REG_008 | 用户名已被注册     | 用户名已注册 | 1. 打开注册页面 2. 输入已注册用户名 `existUser` 3. 输入密码 4. 点击“注册” | 用户名：existUser 密码：Pass123 确认密码：Pass123            | 提示“用户名已存在”，注册失败                            |          | 反向用例 |
        | TC_REG_009 | 密码长度不足       | 无           | 1. 打开注册页面 2. 输入用户名 3. 输入短密码 `12345`（5位） 4. 点击“注册” | 用户名：userX 密码：12345 确认密码：12345                    | 提示“密码至少6位”，注册失败                             |          | 反向用例 |
        | TC_REG_010 | 两次密码不一致     | 无           | 1. 打开注册页面 2. 输入用户名 3. 输入密码 `Pass123` 4. 输入确认密码 `Pass456` 5. 点击“注册” | 用户名：userY 密码：Pass123 确认密码：Pass456                | 提示“密码不一致”，注册失败                              |          | 反向用例 |
        | TC_REG_011 | 必填字段为空       | 无           | 1. 打开注册页面 2. 留空邮箱/用户名或密码或确认密码 3. 点击“注册”按钮 | 任意字段为空                                                 | 提示“请填写完整信息”，不允许注册                        |          | 反向用例 |
        | TC_REG_012 | 注册后状态异常     | 无           | 1. 打开注册页面 2. 使用合法信息注册成功 3. 登录后进入个人中心检查状态 | 任意注册信息                                                 | 用户状态应为“正常”；如非正常（未激活/锁定）应记录为缺陷 |          | 反向用例 |
    约束规范：
        1、生成的测试点，不要有重复的内容
"""


# 定义一个给大模型调用的工具(本质是一个函数)
@tool("写文件的工具", description="写文件的工具，用于将内容写入文件")
def write_file(file_path: str, content: str):
    with open(file_path, "w") as f:
        f.write(content)


# 定义一个读取文件的工具
@tool("读文件的工具", description="读文件的工具，用于读取文件内容")
def read_file(file_path: str):
    with open(file_path, "r") as f:
        return f.read()


# 创建第一个agent智能体
agent = create_agent(
    # 给agent配置使用的大模型对象
    model=model,
    # 给agent添加工具
    tools=[write_file, read_file],
    system_prompt=system_prompt
)

# ================和agent的第一轮对话=============
user_prompt = HumanMessage(content="""
请根据以下需求文档生成测试点，并写入到xmind文件中
📌 F1.3 用户信息修改
🧩 功能背景
	用户可修改昵称、密码、头像、性别等基础信息。
🚶 主流程
    1. 用户进入“个人中心”
    2. 修改某字段并保存
    3. 系统校验内容合法性（如昵称长度、头像格式）
    4. 修改成功后刷新显示
⚠ 异常流程
    用户未登录：提示登录后操作
    输入非法字符：提示不符合规范
📌 业务规则
    昵称长度大于3 小于20，支持中英文
    性别只能为“男 / 女 / 保密”
    头像图片限制大小（2M以内），格式为 png/jpg/jpeg
""")

# 运行agent和agent进行对话交互
response = agent.stream(input={
    "messages": [user_prompt]
})

for chunk in response:
    print(chunk)



"""
理解stream()方法的入参input: InputT
class Person(TypedDict):
    name: str
    age: int

# 传参时就是一个普通字典
p: Person = {"name": "张三", "age": 25}  # ← 就是字典，不是实例化对象
"""