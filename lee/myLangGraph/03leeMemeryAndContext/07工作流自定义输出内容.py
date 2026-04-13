# @Author  : 木森
# @weixin: python771
import os
from typing import TypedDict

import dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from dataclasses import dataclass
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.config import get_stream_writer

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 创建一个大模型对象（大模型的部署方式采用的openai协议，就可以使用这种方式去接入大模型）
llm = ChatOpenAI(
    model=os.getenv('MODEL'),
    base_url=os.getenv('BASE_URL'),
    api_key=os.getenv('API_KEY'),
)


# 定义状态
class State(TypedDict):
    """状态"""
    user_input: str
    test_cases: str
    result: str


# 定义运行时的上下文参数：context
@dataclass
class RuntimeContext:
    """运行时上下文参数"""
    test_env: str  # 测试环境
    tester_name: str  # 测试人员名称


def generator_test_case(state: State):
    """生成测试用例"""
    writer = get_stream_writer()
    writer(f"开始执行生成测试用例的节点")
    prompt = """
    请帮我生成用户5条登录的测试用例，登录账号密码的长度限制为8到16位     
    """
    cases = llm.invoke(prompt)
    return {"test_cases": cases}


def run_test_cases(state: State, runtime: Runtime[RuntimeContext]):
    """执行测试用例"""
    writer = get_stream_writer()
    writer(f"开始执行【分析测试用例】的节点")
    cases = state['test_cases']
    prompt = f"""
    请分析当前的五条测试用例，是否有缺陷,
    用例数据如下：{cases}
    """
    result = llm.invoke(prompt)
    return {"result": result}


def generator_test_report(state: State, config: RunnableConfig):
    """生成测试报告"""
    writer = get_stream_writer()
    writer(f"开始【生成测试报告】的节点运行")
    return {"report": "这个是一个测试报告"}


# =================工作流的创建个编排===================
graph = StateGraph(State, context_schema=RuntimeContext)
graph.add_node("生成测试用例", generator_test_case)
graph.add_node("执行测试用例", run_test_cases)
graph.add_node("生成测试报告", generator_test_report)

# 设置起点
# graph.set_entry_point("生成测试用例")
graph.add_edge(START, "生成测试用例")
graph.add_edge("生成测试用例", "执行测试用例")
graph.add_edge("执行测试用例", "生成测试报告")
# graph.set_finish_point("生成测试报告")
graph.add_edge("生成测试报告", END)

app = graph.compile()

response = app.stream({"user_input": "测试项目A"},
                      config={"recursion_limit": 5},
                      context=RuntimeContext(test_env="测试环境A", tester_name="张三"),
                      stream_mode=['messages', 'custom']
                      )

for input_type, chunk in response:
    if input_type == "messages":
        # ai的输出内容
        print(chunk[0].content, end="", flush=True)
    elif input_type == "custom":
        # 工具执行的输出内容
        print(chunk)
