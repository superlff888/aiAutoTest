# @Author  : 木森
# @weixin: python771
import json
import os

from langchain.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
import dotenv
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

dotenv.load_dotenv()


# 定义状态(保存整个agent或者工作中执行过程数据===>agent里面的短期记忆)
class State(BaseModel):
    """定义状态"""
    messages: list = Field(default=[], description="保存agent执行过程中聊天记录")
    # 传入的需求
    requirement_decs: str = Field(default="", description="传入的需求说明")
    # 生成的测试点
    test_point: str = Field(default="", description="生成的测试点列表")

    # 生成的用例列表
    case_list: list = Field(default=list, description="生成的用例列表")


class CaseGeneratorWorkflow:
    """
    用例生成工作流
    1、基于需求提取测试点(把需求中涉及到的测试点全部提取出来)  --->大模型去提取
    2、加载历史已经存在的测试用例(工具去加载--->json文件)
    3、基于测试点和 已经存在的用例，对之前没有覆盖到的测试测试点 补充生成测试用例
    4、将补充的测试点，持久化存储(将补充的用例写入到json文件)
    5、输出补充生成的测试用例
    """

    def __init__(self):
        # 初始化大模型
        model = ChatOpenAI(model=os.getenv("MODEL"))
        # 给模型绑定工具
        self.model = model

    # 基于需求提取测试点
    def extract_test_point(self, state: State):
        """基于需求提取测试点"""
        print("==================基于需求提取测试点======================")
        system_prompt = """
        你是一个经验丰富的测试工程师，接下来需要你根据用户传入的需求，去系统全面的分析需求中所涉及到的测试点
        工作原则：
            1、所有的测试点都必须有事实依据，不得推测，或者杜撰文档中没有提及和明确说明的内容
        """
        user_message = f"""
        需求描述：
        {state.requirement_decs}
        """
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        ai_messages = self.model.invoke(messages)
        # 把AI执行的结果添加到聊天记录中
        messages.append(ai_messages)
        return {"messages": messages}

    # 加载历史已经存在的测试用例
    def load_history_case(self, state: State):
        """加载历史已经存在的测试用例"""
        print("==================加载历史已经存在的测试用例======================")
        # 从文件中去加载已经存在的测试用例
        with open("test_cases.json", "r", encoding="utf-8") as f:
            case_list = json.load(f).get("test_cases", [])

        return {"case_list": case_list}

    # 补充生成测试点
    def supplement_test_point(self, state: State):
        """补充生成测试点"""
        print("==================补充生成测试点======================")
        users_prompt = f"""
        基于需求文档中的测试点,去分析当前的测试用例是否覆盖到了所有的测试点，如果没有覆盖到，则补充生成对应的测试点，
        目前已有的用例输入如下：
        {state.case_list}
        """
        messages = state.messages
        messages.append(HumanMessage(content=users_prompt))
        ai_messages = self.model.invoke(messages)
        messages.append(ai_messages)
        return {"messages": messages}

    # 保存测试用例的节点
    def save_test_case(self, state: State):
        """保存测试用例的节点"""
        print("==================保存输出节点======================")

    def create_workflow(self):
        """创建工作流"""
        # 初始化graph对象
        graph = StateGraph(State)
        # 添加节点
        graph.add_node("需求测试点提取", self.extract_test_point)
        graph.add_node("历史用例加载", self.load_history_case)
        graph.add_node("补充生成测试点", self.supplement_test_point)
        # 编排节点执行的流程
        graph.add_edge(START, "需求测试点提取")
        graph.add_edge("需求测试点提取", "历史用例加载")
        graph.add_edge("历史用例加载", "补充生成测试点")
        graph.add_edge("补充生成测试点", END)
        # 对graph进行编译
        workflow = graph.compile()
        return workflow


if __name__ == '__main__':
    workflow = CaseGeneratorWorkflow().create_workflow()

    decs = """
    📌 F1.1 用户注册
        🧩 功能背景
        新用户通过注册方式创建账户，支持邮箱/用户名+密码的注册方式。
        🚶 主流程
        1. 用户打开注册页，填写注册信息
        2. 系统校验格式与唯一性（用户名、邮箱）
        3. 提交注册，后台创建账户，初始状态为“正常”
        4. 注册成功后自动登录并跳转首页
        ⚠️ 异常流程
        ● 邮箱/用户名已被注册：提示“已存在”
        ● 两次密码不一致：提示用户重新输入
        📌 状态规则
        ● 新用户状态为 “正常”
        ● 注册时间记录为创建时间，头像为默认图
        📌 业务规则
        ● 用户名唯一，支持 4~20 位字母数字组合
        ● 密码长度不少于 6 位
        ● 邮箱必须符合格式 xxx@xxx.xx
    
    """

    response = workflow.stream({"requirement_decs": decs},
                               stream_mode=['updates', 'messages', 'custom'],
                               version="v2"
                               )

    for chunk in response:
        if chunk['type'] == "messages":
            print(chunk['data'][0].content, end='')
