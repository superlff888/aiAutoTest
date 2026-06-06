# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\02用例生成+评审的代码rag_agent\rag_agent\workflow\case_generator.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""


1、从知识库中去检索功能相关的详细需求信息(agent中以及集成了知识库检索的能力)--->封装为一个tool

2、用例生成的流程(将整个流程使用langgraph封装为一个workflow工作流)--->封装为一个tool：
     获取需求--->大模型生成用例---> 对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->调用大模型补充生成用例--->存储用例(将生成的用例存储到文件，或者数据库)

3、根据需求和已经存在的用例，进行增量补充生成用例(将整个流程使用langgraph封装为一个workflow工作流)--->封装为一个tool：
    获取需求，获取已有的用例 --->调用大模型补充生成用例--->对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->存储用例(将生成的用例存储到文件，或者数据库)


最后将上面的三个工具接入到agent中。


langgraph的使用：
    1、定义状态(State)

    2、定义节点

    3、编排节点

"""
import json
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing import TypedDict, List

from langgraph.types import Send

from models import llm_model
from common.model_output_to_json import format_result_to_json
from pormpts import generate_case_prompt
from pormpts import case_review_prompt
from pormpts import verify_coverage_prompt

from pydantic import BaseModel, Field

from typing import Annotated
import operator


class State(TypedDict):
    """
    定义状态
    """
    # 保存功能的需求文档
    requirements: str
    # 存储生成的用例
    generated_cases: list
    # 当前评审的用例
    current_review_case: dict
    # 覆盖率检查的结果
    coverage_check_result: dict
    # 存储AI评审通过的用例
    review_passed_cases: Annotated[List, operator.add]  # 并发时自动合并列表

    # 存储AI评审未通过的用例
    review_failed_cases: Annotated[List, operator.add]  # 并发时自动合并列表


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

    @staticmethod
    def _generate_case(state: State):
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
        # output_llm_model = llm_model.with_structured_output(CaseList)
        # response = output_llm_model.invoke(prompt)
        # print("生成的测试用例数据结构如下:", response.cases)
        # return {"generated_cases": response.cases}

        # # 调用大模型生成测试用例
        try:
            response = llm_model.invoke(prompt)
            result = response.content
            print("结果：", result)
            try:
                cases = format_result_to_json(result)
            except:
                cases = []
            print(f"用例生成完毕，当前一共生成了{len(cases)}条用例")
            return {"generated_cases": cases}
        except Exception as e:
            print(f"生成用例失败：{e}")
            return {"generated_cases": []}

    @staticmethod
    def _case_review_router(state: State):  # 路由函数，不添加为节点
        """并发对用例进行审核"""
        print("开始对用例进行审核")
        requirements = state.get('requirements')
        # 获取生成的用例
        cases = state.get('generated_cases') or []
        if not cases:
            print("没有可评审的用例，跳过评审环节")
            return []
        # Send(目标节点名,传入该节点的 state 数据)
        review_case_list = [Send("用例评审", {"current_review_case": _case, "requirements": requirements}) for _case in
                            cases]
        return review_case_list

    @staticmethod
    def _review_case(state: State):
        """审核单条用例"""
        # 获取当前要审核的用例
        _case = state.get('current_review_case')
        # 获取原始的需求
        requirements = state.get('requirements')
        # 准备提示词，调用大模型对用例进行评审
        print("开始审核用例：", _case.get('case_name'))
        prompt = case_review_prompt.get_review_prompt(requirements, _case)
        response = llm_model.invoke(prompt)
        result_json = format_result_to_json(response.content)
        # 判断评审是否通过
        if result_json.get('review_result') == "通过":
            print("用例通过审核：", _case.get('case_name'))
            # 需要把AI评审通过的用例保存起来
            _case["review_result"] = "通过"
            _case["review_decs"] = result_json.get('review_decs')
            return {"review_passed_cases": [_case]}
        else:
            print("用例审核未通过：", _case.get('case_name'))
            # 需要把AI评审未通过的用例保存起来
            _case["review_result"] = "未通过"
            _case["review_decs"] = result_json.get('review_decs')
            return {"review_failed_cases": [_case]}

    @staticmethod
    def verify_coverage(state: State):
        """
        用例覆盖率检查
        """
        print("开始分析用例的覆盖率")
        # 获取评审通过的用例
        review_passed_cases = state.get('review_passed_cases')
        # 获取原始的需求说明
        requirements = state.get('requirements')
        # 设计提示词
        prompt = verify_coverage_prompt.get_verify_coverage_prompt(requirements, review_passed_cases)
        # 调用大模型进行检查
        response = llm_model.invoke(prompt)
        result = format_result_to_json(response.content)
        print("用例覆盖率分析报告如下：", result.get('coverage_report'))
        print("用例覆盖率检查结果如下：", result.get('coverage'))
        print("需要人工补充的测试点如下：", result.get('recomment'))
        return {"coverage_check_result": result}

    @staticmethod
    def verify_coverage_router(state: State):
        """验证覆盖率的路由"""
        coverage_check_result = state.get('coverage_check_result')
        # 判断覆盖率是否达到100%
        if coverage_check_result.get('coverage') == "100%":
            return "保存用例"
        else:
            return "补充生成用例"

    @staticmethod
    def supplement_generate_case(state: State):
        """补充生成用例"""
        # 获取需求
        requirements = state.get('requirements')
        # 获取已经评审通过的用例
        review_passed_cases = state.get('review_passed_cases')
        # 获取覆盖率分析报告中需要补充生成用例的测试点
        coverage_check_result = state.get('coverage_check_result')
        recomment = coverage_check_result.get('recomment')

        # 提示词的构建
        prompt = generate_case_prompt.get_supplement_generate_case_prompt(
            requirements=requirements,
            case_list=review_passed_cases,
            test_point=recomment)
        # 开始补充生成用例
        try:
            response = llm_model.invoke(prompt)
            result = response.content
            print("结果：", result)
            cases = format_result_to_json(result)
            print(f"用例生成完毕，当前一共生成了{len(cases)}条用例")
            return {"generated_cases": cases}
        except Exception as e:
            print(f"生成用例失败：{e}")
            return {"generated_cases": []}

    @staticmethod
    def save_case(state: State):
        """保存用例"""
        print("开始保存用例")
        # 获取评审通过的所有测试用例
        review_passed_cases = state.get('review_passed_cases')
        print(f"一共生成了{len(review_passed_cases)}条用例")
        with open("case.json", "w") as f:
            json.dump(review_passed_cases, f)
        print("用例保存完毕")

    # 用于需求初次生成测试用例的流程
    def create_generate_case_workflow(self):
        """
        创建工作流:用于需求初次生成测试用例
        :return:
        """
        graph = StateGraph(State)

        # 添加节点
        graph.add_node('用例生成', self._generate_case)
        graph.add_node('用例评审', self._review_case)
        graph.add_node('用例覆盖率检查', self.verify_coverage)
        graph.add_node('补充生成用例', self.supplement_generate_case)
        graph.add_node('保存用例', self.save_case)

        # 编排节点
        graph.add_edge(START, '用例生成')
        # add_conditional_edges 唯一支持返回 List[Send]；['用例评审'] 第三个参数只是声明"这个路由可能的目标节点"
        graph.add_conditional_edges("用例生成", self._case_review_router, ['用例评审'])

        graph.add_edge('用例评审', "用例覆盖率检查")
        graph.add_conditional_edges("用例覆盖率检查", self.verify_coverage_router, ['保存用例', '补充生成用例'])

        # add_conditional_edges 唯一支持返回 List[Send]（5条用例 ── 路由机器人 ──→ 复制5份，每份都扔进「评审」车间）
        graph.add_conditional_edges("补充生成用例", self._case_review_router, ['用例评审'])

        graph.add_edge('保存用例', END)
        # 对graph进行编译
        workflow = graph.compile()

        return workflow

    # 用于需求更新后补充生成用例的流程
    def create_supplement_generate_workflow(self):
        """创建一个补充生成用例的流程"""
        # 获取需求

        # 获取已经存在的用例，进行补充生成



if __name__ == '__main__':
    workflow = GenerateCaseWorkflow().create_generate_case_workflow()
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



"""
1.需求预处理阶段
人工/AI解析原始需求 → AI需求结构化拆解（显性+隐性测试点提取、歧义标注、缺失需求备注）→ 结构化需求文档入库
↓
2.基准用例生成
大模型依据【结构化需求+项目用例规范模板+历史优质用例知识库】生成首轮用例
↓
3.双层用例评审（AI规则评审+抽样人工评审）
①规则引擎自动化评审（格式、字段、规范、禁用场景校验，硬规则拦截不合格用例）
②AI语义评审（逻辑、场景合理性）
③低覆盖率/高风险模块：人工抽样复审，驳回问题用例退回重生成
↓
4.多维度覆盖率校验（输出标准化报告）
四重覆盖检测：
①需求测试点覆盖率 ②业务分支覆盖率 ③参数边界/等价类覆盖率 ④异常场景覆盖率
生成报告：缺失测试点清单、未覆盖原因、建议补充场景
↓
5.阈值化用例迭代补充
配置终止阈值（例：需求覆盖率≥98%停止自动补充）
未达标→大模型针对性补缺（依据缺失清单定向生成，非全量重写）→补充后重回评审+覆盖检测循环；
达标→进入下一环节，剩余未覆盖项人工备注归档
↓
6.用例标准化入库
AI去重（语义+字段双维度去重）→自动标注优先级/模块/标签→格式规整→入库/落地文件→同步用例版本快照
↓
【可选后置：用例效果沉淀】
优质落地用例回流知识库，作为后续大模型生成参考，持续优化模型生成质量


"""