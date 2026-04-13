# @Author  : 木森
# @weixin: python771
# @Author  : 木森
# @weixin: python771
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.constants import START, END


# 定义状态
class State(TypedDict):
    """状态"""
    user_input: str
    test_cases: list
    check_result: bool


# ================定义运行节点函数=================

def generator_test_case(state: State):
    """生成测试用例"""
    # 实际在使用的时候，是使用llm大模型去生成的
    print("开始执行生成用例的节点,用户输入的需求是：", state.get("user_input"))
    import random
    if random.randint(0, 5) > 2:
        return {"test_cases": ["测试用例1", "测试用例2"]}
    else:
        return {"test_cases": ["测试用例1", "测试用例2", "测试用例3"]}


def check_test_case_router(state: State):
    """检查测试用例是否可用"""
    print("校验测试用例是否可用,当前的用例为：", state.get("test_cases"))
    # 校验逻辑后续讲项目的时候完善,校验用例的数量是否大于3
    if len(state.get("test_cases")) >= 3:
        # return "执行测试用例"
        return True
    else:
        # return "生成测试用例"
        return False


def run_test_cases(state: State):
    """执行测试用例"""
    print("开始执行测试用例：", state.get("test_cases"))
    return {"report": "这个是一个测试报告"}


def generator_test_report(state: State, ):
    """生成测试报告"""
    print("执行generator_test_report节点,生成测试报告")
    return {"report": "这个是一个测试报告"}


# =================工作流的创建个编排===================
graph = StateGraph(State)
graph.add_node("生成测试用例", generator_test_case)
graph.add_node("检查测试用例", check_test_case_router)
graph.add_node("执行测试用例", run_test_cases)
graph.add_node("生成测试报告", generator_test_report)

# 设置起点
graph.add_edge(START, "生成测试用例")
# 设置一个控制节点执行分支的循环条件
graph.add_conditional_edges("生成测试用例", check_test_case_router, {
    True: "执行测试用例", # 满足条件后，进入下一步 "执行测试用例"
    False: "生成测试用例"  # 测试用例数量小于3，则重新指向“生成测试用例”，达到循环效果
})
graph.add_edge("执行测试用例", "生成测试报告")
graph.add_edge("生成测试报告", END)

app = graph.compile()
res = app.invoke({"user_input": "测试项目A"})

print(res)
