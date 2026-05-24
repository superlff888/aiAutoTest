# @Author  : 木森
# @weixin: python771

"""


1、从知识库中去检索功能相关的详细需求信息(agent中以及集成了知识库检索的能力)--->封装为一个tool

2、用例生成的流程(将整个流程使用langgraph封装为一个workflow工作流)：--->封装为一个tool
     获取需求--->大模型生成用例----> 对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->存储用例(将生成的用例存储到文件，或者数据库)

3、根据需求和已经存在的用例，进行增量补充生成用例(将整个流程使用langgraph封装为一个workflow工作流)：--->封装为一个tool
    获取需求，获取已有的用例  --->调用大模型补充生成用例----->对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->存储用例(将生成的用例存储到文件，或者数据库)


最后将上面的三个工具接入到agent中。


langgraph的使用：
    1、定义状态(State)

    2、定义节点

    3、编排节点

"""
import json

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing import TypedDict
from models import llm_model
from rag_agent.pormpts import generate_case_prompt
from pydantic import BaseModel, Field


class State(TypedDict):
    """
    定义状态
    """
    # 保存功能的需求文档
    requirements: str
    # 存储生成的用例
    generated_cases: list
    # 当前评审的用例
    current_review_case: str
    # AI评审的结果
    ai_review_result: str
    # 覆盖率检查的结果
    coverage_check_result: str


# 对用例进行结构化提取的pydantic的模型
class GenerateCase(BaseModel):
    case_id: str = Field(..., description="用例编号")
    case_name: str = Field(..., description="用例名称")
    setup: list = Field(..., description="前置条件")
    test_data: dict = Field(..., description="测试数据")
    execute_step: list = Field(..., description="用例执行的步骤")
    except_result: list = Field(..., description="预期结果")
    result: str = Field(None, description="实际结果")
    priority: str = Field(..., description="优先级")


class CaseList(BaseModel):
    """
    用例列表
    """
    cases: list[GenerateCase] = Field(..., description="用例列表")


class GenerateCaseWorkflow:
    """
    用例生成的工作流
    """

    def _generate_case(self, state: State):
        """
        生成用例
        :param requirements: 功能的需求文档
        :return: 生成的用例
        """
        # 获取需求
        requirements = state.get('requirements')
        # 构建用例生成的提示词
        prompt = generate_case_prompt.get_generate_case_prompt(requirements)

        # 大模型绑定用例输出的数据结构
        output_llm_model = llm_model.with_structured_output(CaseList)
        # response = output_llm_model.invoke(prompt)
        # print("生成的测试用例数据结构如下:", response.cases)
        # return {"generated_cases": response.cases}
        # # 调用大模型生成测试用例
        response = llm_model.invoke(prompt)
        print("结果：", response.content)
        # 判断输出的结果中是否包含<think>推理的内容，如果有则去除
        if "<think>" in response.content:
            result = response.content.split("</think>")
            print("推理结果为:", result[0].replace("<think>", ""))
            # 最终生成的用例数据
            print("测试用例:", result[1].replace('```json', '').replace('```', '').strip())
            res = result[1].replace('```json', '').replace('```', '').strip()
            # 把```json  和```去掉 然后转换为json数据
            json_result = json.loads(res)
            print("将json转换为python的数据类型：", json_result)
            # 将json转换为pydantic数据
            cases = [GenerateCase(**case) for case in json_result]
            return {"generated_cases": cases}


    def create_workflow(self):
        """创建工作流"""
        graph = StateGraph(State)

        # 添加节点
        graph.add_node('用例生成', self._generate_case)

        # 编排节点
        graph.add_edge(START, '用例生成')
        graph.add_edge('用例生成', END)

        # 对graph进行编译
        workflow = graph.compile()
        return workflow


if __name__ == '__main__':
    workflow = GenerateCaseWorkflow().create_workflow()
    response = workflow.stream(
        {
            "requirements": """
        
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
        },
        subgraphs=True,
        stream_mode=["messages"],
        version="v2",
    )
    print("===========开始生成用例===========")
    for chunk in response:
        if chunk["type"] == "messages":
            print(chunk["data"][0].content, end='')

"""
注意点：
    在使用大模型生成用例的时候，由于有些模型返回的结果中会有<think>大模型推理的内容</think>
    langchian在对大模型输出结果使用with_structured_output绑定结构化输出结果的时候，会直接将大模型输入的结果通过json模块转换为json数据，然后再转换为Pydantic的模型
    如果大模型返回的结果带有<think>大模型推理的内容</think>,在进行json格式化处理的时候就会报错！

这个错误不是自己写的代码问题，也不是大模型的问题，使用langchain这个框架本身的机制问题

"""
