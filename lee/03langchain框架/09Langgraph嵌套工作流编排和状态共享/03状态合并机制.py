from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph


# 定义状态：使用 Annotated 声明 cases 字段的合并规则（通过 + 操作符合并列表）
class OverallState(TypedDict):
    cases: Annotated[list[str], operator.add]  # 关键点：并发时自动合并列表
    cases2: Annotated[dict, operator.or_]  # 并发时自动合并字典
# 模拟并行任务节点
def task_a(state: OverallState) -> dict:
    return {"cases": ["结果A"]}

def task_b(state: OverallState) -> dict:
    return {"cases": ["结果B"]}

# 构建并行流程图
builder = StateGraph(OverallState)
builder.add_node("task_a", task_a)
builder.add_node("task_b", task_b)
builder.add_edge("task_a", "task_b")  # 实际场景中可能是并行分支

workflow = builder.compile()
result = workflow.invoke({"cases": []})
print(result)  # 输出: {'cases': ['结果A', '结果B']}