# @Author  : 木森
# @weixin: python771
from rag_agent.workflow.case_generator import GenerateCaseWorkflow
from langchain.tools import tool


@tool("测试用例生成",description="根据需求生成测试用例")
def generate_case(requirements: str) -> str:
    """
    根据需求生成测试用例
    :param requirements: 功能的需求文档
    :return: 生成的用例
    """
    workflow = GenerateCaseWorkflow().create_workflow()
    # 调用工作流,生成用例
    response = workflow.invoke({
        "requirements": requirements
    })
    return response

