# @Author  : 木森
# @weixin: python771
from langchain_core.messages import SystemMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from langchain.tools import tool
from langchain_openai import ChatOpenAI
import os
import dotenv
from langchain.messages import HumanMessage, AIMessage, ToolMessage

dotenv.load_dotenv()


# 定义状态(保存整个agent或者工作中执行过程的数据===>agent里面的短期记忆)
class State(BaseModel):
    """定义状态"""
    messages: list = Field(default=[], description="保存agent执行过程中聊天记录")


@tool(description="进行加法运算的工具")
def add(a: int, b: int) -> str:
    """
    进行算术运算
    :param a: 数值a
    :param b: 数值b
    :return: int
    """
    print("=====进行乘法运算的工具============")
    return str(a * b)


@tool(description="用例生成的工具")
def generate_testcase(decs: str) -> str:
    """
    生成用例
    :param decs: 测试点说明
    :return: str
    """
    print("=====用例生成的工具============")
    return "用例生成成功，用例内容为：登录成功的用例，输入正确的账号密码，点击登录按钮，成功跳转到首页"


class Agent:
    """自定义agent的实现"""

    def __init__(self, system_prompt: str):
        self.tools = [add, generate_testcase]
        # 初始化大模型
        model = ChatOpenAI(model=os.getenv("MODEL"))
        # 给模型绑定工具
        self.model = model.bind_tools(self.tools)
        self.system_prompt = system_prompt

    def init_agent(self, state: State):
        """初始化agent"""
        # 初始化agent状态,设置系统系提示词
        message = state.messages
        message.append(SystemMessage(content=self.system_prompt))
        # 读取所有的mcp服务工具，绑定到模型上

        # 读取长期记忆，加到系统提示词中

        # 读取skills列表中的所有技能，把skills的说明添加到系统提示词中

        return {"messages": message}

    def get_tools_by_name(self, name: str):
        """根据工具名称获取工具"""
        for tool in self.tools:
            if tool.name == name:
                return tool

    # 定义节点
    def llm_node(self, state: State):
        """调用大模型的节点"""
        # 获取用户输入的消息内容
        messages = state.messages
        # 调用大模型
        ai_messages = self.model.invoke(messages)
        # 把AI执行的结果添加到聊天记录中
        messages.append(ai_messages)
        # 更新状态中的messages(更新短期记忆中的内容)
        return {"messages": messages}

    def call_tools_node(self, state: State):
        """执行工具的节点"""
        print("==================工具调用节点======================")
        messages = state.messages
        ai_massages = state.messages[-1]
        tool_calls = ai_massages.tool_calls
        for tool_call in tool_calls:
            # 获取工具调用的id
            tool_call_id = tool_call.get("id")
            # 获取工具的名称
            tool_name = tool_call.get("name")
            # 获取调用该工具的参数
            tool_args = tool_call.get("args")
            # 找到工具执行的函数
            tool = self.get_tools_by_name(tool_name)
            result = tool.invoke(tool_args)
            # 构建一个工具调用的消息
            tool_message = ToolMessage(tool_call_id=tool_call_id, content=str(result))
            messages.append(tool_message)
        return {"messages": messages}

    def out_put_node(self, state: State):
        """输出结果节点"""
        print("==================结果输出节点======================")
        print(state.messages)

    def router_func(self, state: State):
        """路由函数"""
        # 判断是否有工具调用
        ai_massages = state.messages[-1]
        if ai_massages.tool_calls:
            # 有工具调用
            return "工具调用节点"
        else:
            # 没有工具调用
            return "输出结果节点"

    # 编排agent中节点执行的流程
    def create_agent(self):
        """编排agent中节点执行的流程"""
        # 创建一个graph
        graph = StateGraph(State)

        # 在graph对象中添加执行的节点
        graph.add_node("初始化节点", self.init_agent)
        graph.add_node("模型调用节点", self.llm_node)
        graph.add_node("工具调用节点", self.call_tools_node)
        graph.add_node("输出结果节点", self.out_put_node)

        # 对agent执行的流程进行连接(编排)
        graph.add_edge(START, "初始化节点")
        graph.add_edge("初始化节点", "模型调用节点")
        graph.add_conditional_edges("模型调用节点", self.router_func)
        graph.add_edge("工具调用节点", "模型调用节点")
        graph.add_edge("输出结果节点", END)
        # 对langgraph对象进行编译
        agent = graph.compile()
        return agent


if __name__ == '__main__':
    # 创建一个agent对象
    system_prompt = """
    你是一个通过的ai agent，对于用户的任务，优先去检查是否有匹配的工具，来完成任务，有对应的工具则优先调用工具来完成任务
    """
    agent = Agent(system_prompt=system_prompt).create_agent()
    response = agent.stream({"messages": [HumanMessage(content="请使用工具计算1+2的结果,再帮我用工具写个测试用例")]},
                            stream_mode=['updates', 'messages', 'custom'],
                            version="v2"
                            )

    for chunk in response:
        if chunk['type'] == "messages":
            print(chunk['data'][0].content, end='')
