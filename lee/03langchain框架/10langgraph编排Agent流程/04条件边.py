# @Author  : 木森
# @weixin: python771
"""
条件分支
需求：
    用户给出一段文字(需求说明，或者是接口文档 或者其他的)
        需求说明  ----> json格式的用例，csv 格式的用例
        接口文档  ----> 接口用例数据 yaml 或者json
        其他的   ----> None

    让我们的graph调用大模型去分辨需求，执行对应的业务流


"""
from typing import TypedDict
from langchain_openai import ChatOpenAI
import os, dotenv
from langgraph.constants import START, END

from langgraph.graph import StateGraph

dotenv.load_dotenv('G:\AI\上课代码\LangchainProjectDemo\DeepSeek\.env')

llm = ChatOpenAI(
    model_name="Pro/deepseek-ai/DeepSeek-V3",
    openai_api_key=os.getenv('API_KEY'),
    openai_api_base="https://api.siliconflow.cn/v1",
)


#  1、定义State
class State(TypedDict):
    user_input: str  # 用户输入的数据
    csv_data: str  # csv格式的数据
    json_data: str  # json格式的数据
    other_data: str  # 其他格式的数据
    run_flow: str  # 运行对应的业务流


# 2、定义工作节点
def select_run_flow(state: State) -> dict:
    """
    自动选择运行的业务流
    """
    prompt = f"""
    你是一个AI智能体，你的任务是判断用户输入一段需求说明，还是接口的文档信息，
    输入内容如下：{state["user_input"]}
    如果是接口的文档信息 则输出返回数字1，如果是需求说明则输出返回数字2，其他的内容则输出返回数字0
    """
    result = llm.invoke(prompt)
    if '1' in result.content:
        return {"run_flow": "generator_api_case"}
    elif '2' in result.content:
        return {"run_flow": "generator_test_case"}
    else:
        return {"run_flow": "work3"}


def generator_api_case(state: State) -> dict:
    prompt = f"""
    您是一个工作10年的测试工程师，您需要根据用户输入的接口文档，生成对应的测试用例，先考虑正常功能执行的用例，
    然后考虑异常场景的用例，最后考虑边界场景的用例，最后考虑性能场景的用例，最后考虑兼容性
    输入内容如下：{state["user_input"]}
    输出结果要是是json格式的用例数据
    """
    result = llm.invoke(prompt)
    return {'json_data': result.content}


def generator_test_case(state: State) -> dict:
    prompt = f"""
        您是一个工作10年的测试工程师，您需要根据用户需求文档生成对应的测试用例，先考虑正常功能执行的用例，
        然后考虑异常场景的用例，最后考虑边界场景的用例，最后考虑性能场景的用例，最后考虑兼容性
        输入内容如下：{state["user_input"]}
        输入格式的要求是csv格式的用例数据
        """
    result = llm.invoke(prompt)
    return {'csv_data': result.content}


def work3(state: State) -> dict:
    return {'other_data': "输入的内容不是接口文档，也不是需求说明"}


# 定义一个路由
def router(state: State) -> str:
    # node节点名和返回值相同时，add_conditional_edges才不需要映射，例如：return "api_case"
    if state["run_flow"] == "generator_api_case":
        return "generator_api_case"  
    # func功能函数名和返回值相同时，add_conditional_edges需要映射，方便后续改节点名不用动 router函数，例如：return "generator_test_case" 需要映射到 test_case 节点
    elif state["run_flow"] == "generator_test_case":
        return "generator_test_case"  
    else:
        return "work3"


# 创建一个graph
graph = StateGraph(State)
# 往graph中添加节点--> 节点名称(字符串)和节点执行的函数
graph.add_node("select1", select_run_flow)
graph.add_node("api_case", generator_api_case)
graph.add_node("test_case", generator_test_case)
graph.add_node("work3", work3)

# 进行节点编排:图中引用节点用的是节点名称(字符串)，不是函数本身
graph.add_edge(START, "select1")
# 设置一个边条件(流程分支判断)--> router 的返回值会匹配到字典里的 key，然后走到对应的 value 节点,例如：router返回"generator_api_case" → 跳到 api_case 节点
graph.add_conditional_edges('select1', router, {
    "generator_api_case": "api_case",  # 图中引用节点用的是字符串名称，不是函数本身,所以映射到节点名称
    "generator_test_case": "test_case",  
    "work3": "work3"
})

graph.add_edge("api_case", END)
graph.add_edge("test_case", END)
graph.add_edge("work3", END)

# 编译graph
app = graph.compile()
print(app.get_graph().draw_mermaid())


# 实际调用入口
if __name__ == "__main__":
    user_text = input("请输入需求说明或接口文档：\n")
    result = app.invoke({"user_input": user_text})
    print("\n=== 生成结果 ===")
    if result.get("json_data"):
        print("【JSON格式 - 接口测试用例】")
        print(result["json_data"])
    elif result.get("csv_data"):
        print("【CSV格式 - 功能测试用例】")
        print(result["csv_data"])
    else:
        print(result.get("other_data", "未知结果"))