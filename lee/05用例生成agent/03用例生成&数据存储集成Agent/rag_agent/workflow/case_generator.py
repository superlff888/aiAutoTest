# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\workflow\case_generator.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""


1、从知识库中去检索功能相关的详细需求信息(agent中以及集成了知识库检索的能力)--->封装为一个tool

2、用例生成的流程(将整个流程使用langgraph封装为一个workflow工作流)：--->封装为一个tool
     获取需求--->大模型生成用例----> 对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->调用大模型补充生成用例---->存储用例(将生成的用例存储到文件，或者数据库)

3、根据需求和已经存在的用例，进行增量补充生成用例(将整个流程使用langgraph封装为一个workflow工作流)：--->封装为一个tool
    获取需求，获取已有的用例  --->调用大模型补充生成用例----->对生成的用例进行逐条评审---> 覆盖率的检测(检测当前生成的用例是否覆盖了需求中所有的测试点，生成一个覆盖率检测的报告)
     --->存储用例(将生成的用例存储到文件，或者数据库)


最后将上面的三个工具接入到agent中。


langgraph的使用：
    1、定义状态(State)    

    2、定义节点

    3、编排节点

"""
import sys
from pathlib import Path

# 把 "03用例生成&数据存储集成Agent/" 目录加入 sys.path
# 用途：让直接运行本脚本（VS Code 三角箭头 / python case_generator.py）也能找到顶层模块 models 和 rag_agent
# parents[2] 含义：从当前文件向上跳 2 层 workflow -> rag_agent -> 03用例生成&数据存储集成Agent
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

from langgraph.constants import START, END
from langgraph.graph import StateGraph
from typing import TypedDict, List

from langgraph.types import Send

from models import llm_model_generate, llm_model_review, llm_model_coverage
from rag_agent.common.hybrid_structured_invoke import hybrid_structured_invoke
from rag_agent.pormpts import generate_case_prompt
from rag_agent.pormpts import case_review_prompt
from rag_agent.pormpts import verify_coverage_prompt

from rag_agent.tools.data_model import CaseList, CoverageResult, ReviewResult

from typing import Annotated
import operator


def parse_coverage_percent(coverage_str: str) -> float:
    """把 LLM 输出的覆盖率字符串解析为 0-100 的浮点数。

    支持格式：'100%' / '100.0%' / '75.0%' / '0%' / 异常时返回 0.0
    """
    if not coverage_str:
        return 0.0
    try:
        return float(str(coverage_str).strip().rstrip('%').strip())
    except (ValueError, AttributeError):
        return 0.0


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
    review_passed_cases: Annotated[List, operator.add] # 并发时自动合并列表
    # 存储AI评审未通过的用例
    review_failed_cases: Annotated[List, operator.add] # 并发时自动合并列表


# 注：GenerateCase / CaseList / ReviewResult / CoverageResult 四个 Pydantic 模型已统一迁移到
# rag_agent.tools.data_model，本文件顶部 import 引用，避免与 tools 层定义重复造成字段不一致。


class GenerateCaseWorkflow:
    """
    用例生成的工作流
    """

    @staticmethod
    def _generate_case(state: State):
        """
        生成用例（路径 A/B 混合 + Pydantic 强校验）
        :return: 生成的用例 dict 列表
        """
        # 获取需求
        requirements = state.get('requirements')
        # 构建用例生成的提示词
        messages = generate_case_prompt.get_generate_case_prompt(requirements)
        # 通过 hybrid_structured_invoke 调用大模型，自动兼容思考型/非思考型，并做 Pydantic 强校验
        try:
            result: CaseList = hybrid_structured_invoke(
                llm_model_generate, messages, CaseList
            )
            cases = [c.model_dump() for c in result.cases]
            print(f"用例生成完毕，当前一共生成了{len(cases)}条用例")
            return {"generated_cases": cases}
        except Exception as e:
            print(f"生成用例失败：{e}")
            return {"generated_cases": []}

    @staticmethod
    def _case_review_router(state: State): # 路由函数，不添加为节点
        """并发对用例进行审核"""
        print("开始对用例进行审核")
        requirements = state.get('requirements')
        # 获取生成的用例
        cases = state.get('generated_cases')
        # Send(目标节点名,传入该节点的 state 数据)
        review_case_list = [Send("用例评审", {"current_review_case": _case, "requirements": requirements}) for _case in
                            cases]
        return review_case_list

    @staticmethod
    def _review_case(state: State):
        """审核单条用例（路径 A/B 混合 + Pydantic 强校验）"""
        # 获取当前要审核的用例
        _case = state.get('current_review_case')
        # 获取原始的需求
        requirements = state.get('requirements')
        # 准备提示词，调用大模型对用例进行评审
        print("开始审核用例：", _case.get('case_name'))
        messages = case_review_prompt.get_review_prompt(requirements, _case)
        try:
            result: ReviewResult = hybrid_structured_invoke(
                llm_model_review, messages, ReviewResult
            )
            result_json = result.model_dump()
        except Exception as e:
            print(f"评审失败，按不通过处理：{e}")
            result_json = {
                "review_result": "不通过",
                "review_desc": "LLM 输出解析失败",
                "failed_dimensions": ["评审失败"],
            }

        # 判断评审是否通过
        if result_json.get('review_result') == "通过":
            print("用例通过审核：", _case.get('case_name'))
            # 需要把AI评审通过的用例保存起来
            _case["review_result"] = "通过"
            _case["review_desc"] = result_json.get('review_desc', '')
            _case["failed_dimensions"] = result_json.get('failed_dimensions', [])
            return {"review_passed_cases": [_case]}
        else:
            print("用例审核未通过：", _case.get('case_name'))
            # 需要把AI评审未通过的用例保存起来
            _case["review_result"] = "未通过"
            _case["review_desc"] = result_json.get('review_desc', '')
            _case["failed_dimensions"] = result_json.get('failed_dimensions', [])
            return {"review_failed_cases": [_case]}

    @staticmethod
    def verify_coverage(state: State):
        """
        用例覆盖率检查（路径 A/B 混合 + Pydantic 强校验）
        """
        print("开始分析用例的覆盖率")
        # 获取评审通过的用例
        review_passed_cases = state.get('review_passed_cases', [])
        # 获取原始的需求说明
        requirements = state.get('requirements')
        # 获取提示词
        messages = verify_coverage_prompt.get_verify_coverage_prompt(requirements, review_passed_cases)
        # 通过 hybrid_structured_invoke 调用大模型进行检查，得到强校验后的结构化结果
        try:
            result: CoverageResult = hybrid_structured_invoke(
                llm_model_coverage, messages, CoverageResult
            )
            result_dict = result.model_dump()
        except Exception as e:
            print(f"覆盖率检查失败：{e}")
            # 兜底：返回 0% 覆盖率 + 空 recommend，让上游路由进入"补充生成"分支
            result_dict = {
                "coverage_report": "LLM 解析失败",
                "coverage": "0.0%",
                "recommend": [],
            }

        print("用例覆盖率分析报告如下：", result_dict.get('coverage_report'))
        print("用例覆盖率检查结果如下：", result_dict.get('coverage'))
        print("需要人工补充的测试点如下：", result_dict.get('recommend'))
        return {"coverage_check_result": result_dict}

    @staticmethod
    def verify_coverage_router(state: State):
        """验证覆盖率的路由"""
        coverage_check_result = state.get('coverage_check_result') or {}
        coverage_value = parse_coverage_percent(coverage_check_result.get('coverage', '0%'))
        # 容忍 99.95% 以上算达标（兼容 LLM 输出 "100%" / "100.0%" 等多种格式，规避浮点精度问题）
        if coverage_value >= 99.95:
            return "保存用例"
        return "补充生成用例"

    @staticmethod
    def supplement_generate_case(state: State):
        """补充生成用例（路径 A/B 混合 + Pydantic 强校验）"""
        # 获取需求
        requirements = state.get('requirements')
        # 获取已经评审通过的用例
        review_passed_cases = state.get('review_passed_cases')
        # 获取覆盖率分析报告中需要补充生成用例的测试点
        coverage_check_result = state.get('coverage_check_result')
        recommend = coverage_check_result.get('recommend')

        # 提示词的构建
        messages = generate_case_prompt.get_supplement_generate_case_prompt(
            requirements=requirements,
            case_list=review_passed_cases,
            test_point=recommend)
        # 通过 hybrid_structured_invoke 补充生成用例（与初次生成走同一套结构化兼容入口）
        try:
            result: CaseList = hybrid_structured_invoke(
                llm_model_generate, messages, CaseList
            )
            cases = [c.model_dump() for c in result.cases]
            print(f"用例生成完毕，当前一共生成了{len(cases)}条用例")
            return {"generated_cases": cases}
        except Exception as e:
            print(f"生成用例失败：{e}")
            return {"generated_cases": []}

    @staticmethod
    def save_case(state: State):
        """保存用例（写入前剥离评审元数据，case.json 只保留纯用例字段）。

        两份产物：
          - case.json：通过评审的用例（strip 评审元数据，保持纯用例形态）
          - case_failed.json：未通过评审的用例（**保留** review_result / review_desc / failed_dimensions，
            便于诊断"为什么 23 条变 13 条"——评审是否误判为重复 / 严苛度过高等）
        """
        print("开始保存用例")
        # 获取评审通过 / 未通过的两批用例
        review_passed_cases = state.get('review_passed_cases', [])
        review_failed_cases = state.get('review_failed_cases', [])
        print(f"评审通过 {len(review_passed_cases)} 条，未通过 {len(review_failed_cases)} 条")

        # 评审元数据键：仅在 case.json 落盘前剥离；case_failed.json 必须保留以便诊断
        REVIEW_META_KEYS = {"review_result", "review_desc", "failed_dimensions"}
        clean_cases = [
            {k: v for k, v in c.items() if k not in REVIEW_META_KEYS}
            for c in review_passed_cases
        ]

        # 打印每条不通过 case 的过滤原因（review_desc + failed_dimensions）——便于直接看
        if review_failed_cases:
            print("\n========== 评审未通过用例（被过滤）详情 ==========")
            for idx, c in enumerate(review_failed_cases, 1):
                print(
                    f"[{idx}] case_id={c.get('case_id', '?')} | "
                    f"case_name={c.get('case_name', '?')}\n"
                    f"    原因: {c.get('review_desc', '(无)')}\n"
                    f"    失败维度: {c.get('failed_dimensions', [])}"
                )
            print("=" * 56)

        # case.json：通过用例（strip 评审元数据）
        case_file = Path(__file__).parent / "case.json"
        with open(case_file, "w", encoding="utf-8") as f:
            json.dump(clean_cases, f, ensure_ascii=False, indent=4)
        print(f"通过用例保存完毕，落地路径：{case_file}（{len(clean_cases)} 条）")

        # case_failed.json：未通过用例（保留 review 元数据）
        if review_failed_cases:
            failed_file = Path(__file__).parent / "case_failed.json"
            with open(failed_file, "w", encoding="utf-8") as f:
                json.dump(review_failed_cases, f, ensure_ascii=False, indent=4)
            print(f"未通过用例保存完毕，落地路径：{failed_file}（{len(review_failed_cases)} 条）")

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
        graph.add_conditional_edges("用例生成", self._case_review_router, ['用例评审'])

        graph.add_edge('用例评审', "用例覆盖率检查")
        graph.add_conditional_edges("用例覆盖率检查", self.verify_coverage_router, ['保存用例', '补充生成用例'])

        graph.add_conditional_edges("补充生成用例", self._case_review_router, ['用例评审'])

        graph.add_edge('保存用例', END)
        # 对graph进行编译
        workflow = graph.compile()

        return workflow

    # ===============下面是补充生成用例的流程==========================
    # 用于需求更新后补充生成用例的流程
    def create_supplement_generate_workflow(self):
        """创建一个补充生成用例的流程"""
        graph = StateGraph(State)
        # 添加节点
        graph.add_node('用例覆盖率检查', self.verify_coverage)
        graph.add_node('用例评审', self._review_case)
        graph.add_node('补充生成用例', self.supplement_generate_case)
        graph.add_node('保存用例', self.save_case)
        # 编排流程
        graph.add_edge(START, '用例覆盖率检查')
        graph.add_conditional_edges("用例覆盖率检查", self.verify_coverage_router, ['保存用例', '补充生成用例'])
        graph.add_conditional_edges("补充生成用例", self._case_review_router, ['用例评审'])
        graph.add_edge('用例评审', "用例覆盖率检查")
        graph.add_edge('保存用例', END)
        # 对graph进行编译
        workflow = graph.compile()
        return workflow


if __name__ == '__main__':
    workflow = GenerateCaseWorkflow().create_generate_case_workflow()

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
        ● 用户名唯一，仅支持 4~20 位字母数字组合
        ● 密码长度不少于 6 位
        ● 邮箱必须符合格式 xxx@xxx.xx
    
    """

    response = workflow.stream(
        {"requirements": requirements},
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
