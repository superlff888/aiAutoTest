# @Author  : 木森
# @weixin: python771
"""

节点函数可以接受以下三种类型的参数
1. state：图形的状态
    继承TypeDict的类
2. config：包含配置信息和跟踪信息（如RunnableConfig thread_id tags）
3. runtime：包含运行时上下文和其他信息（如 Runtime store stream_writer）
"""
from typing import TypedDict

from langgraph.graph import StateGraph
from langgraph.constants import START, END
from dataclasses import dataclass
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime


# 定义状态
class State(TypedDict):
    """状态"""
    user_input: str
    test_cases: list


# 定义运行时的上下文参数
@dataclass
class RuntimeContext:
    """运行时上下文参数"""
    test_env: str  # 测试环境
    tester_name: str  # 测试人员名称


# ================定义运行节点函数=================

def generate_test_case(state: State):
    """生成测试用例"""
    print(f"用户输入的需求是:{state.get('user_input')},开始进行测试用例生成")
    # 这里核心的功能实现需要调用llm进行生成，暂时跳过
    print("测试用例已经生成", )
    return {"test_cases": ["测试用例1", "测试用例2"]}

# RuntimeContext实例；Runtime[RuntimeContext] 对应 RuntimeContext 类
def run_test_cases(state: State, runtime: Runtime[RuntimeContext]):
    """
    执行测试用例
    ::runtime: 这表示参数 runtime 应该是一个 RuntimeContext 类本身。调用时你传的是： RuntimeContext类的名字，而不是它的实例

    """
    print("正在执行测试用例：", state['test_cases'])
    print("当前执行的测试环境", runtime.context.test_env)
    print("执行人", runtime.context.tester_name)
    return {"report": "这个是一个测试报告"}

# RunnableConfig配置对象
def generator_test_report(state: State, config: RunnableConfig):
    """生成测试报告"""
    print(f"执行generator_test_report节点#{config.get("configurable").get("thread_id")}")
    return {"report": f"这个是一个测试报告#{config.get("configurable").get("thread_id")}"}


# =================工作流的创建个编排===================
graph = StateGraph(state_schema=State, context_schema=RuntimeContext)  # 创建工作流的时候加入上下文
graph.add_node('生成测试用例', generate_test_case)
graph.add_node('执行测试用例', run_test_cases)
graph.add_node("生成测试报告", generator_test_report)

# 设置起点
# graph.set_entry_point("生成测试用例")
graph.add_edge(START, "生成测试用例")

graph.add_edge("生成测试用例", "执行测试用例")
graph.add_edge("执行测试用例", "生成测试报告")
# graph.set_finish_point("生成测试报告")
graph.add_edge("生成测试报告", END)

# 编译工作流
app = graph.compile()
res = app.invoke({"user_input": "测试项目A"},
                 config={"configurable":{"thread_id": "BUG#123"}},
                 context={"test_env":"测试环境", "tester_name":"测试人员"}
                 )

# 我自己的拓展
# res = app.invoke({"user_input": "测试项目A"},
#                  config=RunnableConfig(configurable={"thread_id": "BUG#123"}),
#                  context=RuntimeContext(test_env="测试环境", tester_name="测试人员")
#                  )

print(res)
print(type(RuntimeContext(test_env="测试环境", tester_name="测试人员")))
print(type(RunnableConfig(configurable={"thread_id": "BUG#123"})))
