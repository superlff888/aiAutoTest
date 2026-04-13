
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.types import Send

"""
# 并发执行特定节点：
 使用Send去实现：

 比如，输入一个接口文档：
    生成测试点 ：10个测试点
    10个测试点 -->转换为 10条可以执行的用例
    
    （定义个并发节点）将测试点---> 转换为可执行用例的节点  (调用用大模型去实现)

"""
from typing import Annotated
import operator


# 定义状态
class State(TypedDict):
    """状态"""
    user_input: str
    test_cases: list
    check_result: bool
    case: str
    # 如果多个node节点需求去修改某个状态的值，那么可以使用Annotated
    # 如果边节点返回的是列表，Annotated[list, operator.add]进行自动合并这些list
    runnable_api_case: Annotated[list[dict], operator.add]  # Annotated[runnable_api_case数据类型, 操作符]

    # # 如果边节点返回的是字典，Annotated[dict, operator.or_()]进行自动合并
    # runnable_api_case: Annotated[dict, operator.or_()]


# ================定义运行节点函数=================

def generator_test_case_point(state: State):
    """生成测试点"""
    # 实际在使用的时候，是使用大模型去生成的
    print("开始执行生成用例的节点,用户输入的需求是：", state.get("user_input"))
    import random
    if random.randint(0, 5) > 2:
        return {"test_cases": ["测试用例1", "测试用例2"]}
    else:
        return {"test_cases": ["测试用例1", "测试用例2", "测试用例3"]}


def run_test_cases(state: State):
    """执行测试用例"""
    print("开始执行测试用例：", state.get("test_cases"))
    return {"report": "这个是一个测试报告"}


def generator_test_report(state: State, ):
    """生成测试报告"""
    print("执行generator_test_report节点,生成测试报告")
    return {"report": "这个是一个测试报告"}


def generator_runnable_api_case(state: State):
    """根据api接口测试点，并发生成可执行接口用例"""
    print("正在生成可执行的接口用例", state.get("test_cases"))
    result = []
    for case in state.get("test_cases"):
        print("case:", case)
        # “api用例生成”节点 对应 runnable_api函数参数，批量生成可执行测试用例；case必须在State中声明
        result.append(Send("api用例生成", {"case": case}))  # 节点并发执行（指明节点名和节点参数），需要分发到多个相同/不同的节点
    return result


def runnable_api(state: State):
    print("正在根据测试点，生成包含用例名称、接口url等信息的可执行接口用例:", state.get('case'))
    return {
        "runnable_api_case": [{"api_name": state.get('case'), "api_url": "http://127.0.0.1:8000/api/a",
                              "api_method": "POST"}]
    }


# =================工作流创建个编排===================
graph = StateGraph(State)
graph.add_node("生成测试点", generator_test_case_point)
graph.add_node("生成可执行接口用例", generator_runnable_api_case)
graph.add_node("api用例生成", runnable_api)
graph.add_node("执行测试用例", run_test_cases)
graph.add_node("生成测试报告", generator_test_report)

# 设置起点
graph.add_edge(START, "生成测试点")
# 设置一个控制节点执行分支的条件：需要分发到多个相同或不同的节点
graph.add_conditional_edges(
    "生成测试点",
    generator_runnable_api_case,  # 返回[Send(...), Send(...), ...]，该节点函数为处理并行任务的函数
    ["api用例生成"])  # 被并发执行的节点函数名，可省略；并发生成的cases自动合并到State状态的runnable_api_case字段中
graph.add_edge("api用例生成", "执行测试用例")  # 上一步并发执行了"api用例生成"，接下来就需要"执行测试用例"
graph.add_edge("执行测试用例", "生成测试报告")

graph.add_edge("生成测试报告", END)

app = graph.compile()
res = app.invoke({"user_input": "测试项目A"})

print(res)
