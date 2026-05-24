# @Author  : 木森
# @weixin: python771

from typing import List

from rag_agent.tools.data_model import GenerateCase
from rag_agent.workflow.case_generator import GenerateCaseWorkflow
from langchain.tools import tool


@tool("测试用例生成", description="根据需求生成测试用例")
def generate_case(requirements: str) -> str:
    """
    根据需求生成测试用例
    :param requirements: 功能的需求文档
    :return: 生成的用例
    """
    workflow = GenerateCaseWorkflow().create_generate_case_workflow()
    # 调用工作流,生成用例
    state = workflow.invoke({
        "requirements": requirements
    })

    # 获取生成的所有用例
    cases = state.get("review_passed_cases")
    # 获取覆盖率分析报告
    coverage_report = state.get("coverage_check_result")
    return f"生成的用例：{cases} \n 覆盖率分析报告：{coverage_report}"


@tool("补充生成用例", description="根据已有的测试用例，补充生成测试用例")
def generate_case_by_exist(requirements: str, exist_case: List[GenerateCase]) -> str:
    """
    根据已有的测试用例，补充生成测试用例
    :param requirements: 功能的需求文档
    :param exist_case: 已有的测试用例
    :return: 生成的用例
    """
    workflow = GenerateCaseWorkflow().create_supplement_generate_workflow()
    # 获取已存在的用例id
    exist_case_ids = [case.case_id for case in exist_case]

    # 调用工作流,生成用例
    state = workflow.invoke({
        "requirements": requirements,
        "review_passed_cases": exist_case
    })
    # 获取生成的所有用例
    cases = state.get("review_passed_cases")
    # 获取覆盖率分析报告
    coverage_report = cases.get("coverage_check_result")
    # 获取补充的新用例数量
    new_case_count = len(cases) - len(exist_case)
    # 本次新增的用例数据
    new_cases = []
    for case_ in cases:
        # 判断是否是新增的用例
        if case_.get("case_id") in exist_case_ids:
            continue
        else:
            new_cases.append(case_)
    return f"本次补充生成的用例数量为：{new_case_count}，\n 新增的用例数据为：{new_cases} \n 最新的覆盖率分析报告：{coverage_report}"


if __name__ == '__main__':
    requirements = """

             F1.1 用户注册
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
    generate_case_by_exist(requirements, [])
