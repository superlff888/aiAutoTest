

import os 
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate   
from langchain.messages import SystemMessage, HumanMessage, AIMessage


# 加载.env文件中的环境变量
dotenv.load_dotenv()    

llm = ChatOpenAI(
    model=os.getenv('OPENAI_MODEL'),        
    base_url=os.getenv('OPENAI_BASE_URL'),
    api_key=os.getenv('OPENAI_API_KEY')
)


sys_prompt = SystemMessage(content="""
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
       	json格式的用例必须包含如下字段：
       	id,case_name,test_data,test_step
    约束规范：
        1、生成的测试点，不要有重复的内容

"""
              )


user_prompt = HumanMessage(content="""请根据以下需求文档生成测试点，
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

messages = [sys_prompt, user_prompt]


from pydantic import BaseModel, Field


class TestCase(BaseModel):
    id: str = Field(..., description="用例ID")
    case_name: str = Field(..., description="用例名称")
    test_data: dict = Field(..., description="测试数据")
    test_step: list = Field(..., description="测试步骤")    

class CaseModelOutputParser(BaseModel):
    test_cases: list[TestCase] = Field(..., description="测试用例列表")
    case_count: int = Field(..., description="用例总数")
    name: str = Field(..., description="测试的功能")

model_structured = llm.with_structured_output(TestCase)

response = model_structured.invoke(messages)

# res = response.model_dump()

# print(res)



