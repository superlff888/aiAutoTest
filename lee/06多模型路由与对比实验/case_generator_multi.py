# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee/06多模型路由与对比实验/case_generator_multi.py
# @Author      : Lee大侠
# @Desc        : 用例生成工作流——多模型路由版本（DeepSeek 主 / M3 RAG）
# @CreateTime  : 2026/06/07
# @UpdateTime  : 2026/06/07
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
多模型路由版的"用例生成工作流"
================================

# 与原版的差异
    原文件：lee/05用例生成agent/02用例生成&评审的代码rag_agent/workflow/case_generator.py
    本文件：完全照搬原工作流结构，**只把 llm_model 替换成 model_router.get_llm_for_task()**
    优点：原文件零修改；想看传统写法随时切回去。

# 路由配置（默认）
    +-------------------+----------------+--------------------------------+
    | 工作流节点        | 任务类型       | 实际使用模型                   |
    +-------------------+----------------+--------------------------------+
    | 用例生成          | CASE_GENERATION | deepseek-v4-pro（推理强）     |
    | 用例评审          | CASE_REVIEW     | deepseek-v4-pro               |
    | 覆盖率检查        | COVERAGE_CHECK  | deepseek-v4-pro               |
    | 补充生成          | CASE_SUPPLEMENT | deepseek-v4-pro               |
    | 需求结构化拆解    | REQUIREMENT_PARSE | MiniMax-M3（中文细腻）     |
    | RAG 检索问答      | RAG_QUERY       | MiniMax-M3（中文语义）        |
    +-------------------+----------------+--------------------------------+

# 跑法
    python case_generator_multi.py                     # 用默认需求跑一次
    python case_generator_multi.py --model deepseek-v4-pro --task all  # 全节点强制某模型
"""

from __future__ import annotations

import json
import os
import sys
import argparse
from typing import TypedDict, List, Annotated, Optional
import operator

# —— 让脚本能直接 import 兄弟目录的 model_router.py ——
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# —— 复用原项目的 prompt / 通用工具（路径相对原项目根）——
# 提示：原文件在 05用例生成agent/02用例生成&评审的代码rag_agent/ 下
#  本文件平级于原项目根，通过相对路径拼接
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ORIG_AGENT_DIR = os.path.join(
    PROJECT_ROOT,
    "lee", "05用例生成agent", "02用例生成&评审的代码rag_agent",
)
if ORIG_AGENT_DIR not in sys.path:
    sys.path.insert(0, ORIG_AGENT_DIR)

# —— 引入模型路由（核心）——
from model_router import (
    get_llm_for_task,
    get_profile,
    list_routing,
    set_routing,
    reset_routing,
    get_usage_summary,
    export_usage_history,
    TaskType,
)

# —— 复用原项目的 prompt / 通用工具 ——
try:
    from pormpts import generate_case_prompt
    from pormpts import case_review_prompt
    from pormpts import verify_coverage_prompt
    from common.model_output_to_json import format_result_to_json
    log_import = "OK：复用原项目 prompt + common"
except Exception as e:
    # 如果路径拼不上，兜底用本地极简 prompt（不推荐，但保证脚本可跑）
    log_import = f"FAILED：{e}；fallback 到本地极简 prompt"
    from langchain.messages import SystemMessage, HumanMessage

    class generate_case_prompt:  # type: ignore[no-redef]
        @staticmethod
        def get_generate_case_prompt(requirements: str):
            return [SystemMessage(content="你是测试工程师，输出严格 JSON 数组，每条用例包含 case_id/priority/case_name/setup/test_data/execute_step/expected_result/result。"),
                    HumanMessage(content=f"请为以下需求生成测试用例：\n{requirements}")]
        @staticmethod
        def get_supplement_generate_case_prompt(requirements, case_list, test_point):
            return [SystemMessage(content="你是测试工程师，输出严格 JSON 数组，针对缺失的测试点补充生成用例。"),
                    HumanMessage(content=f"需求：\n{requirements}\n\n已有用例：\n{case_list}\n\n缺失测试点：\n{test_point}")]

    class case_review_prompt:  # type: ignore[no-redef]
        @staticmethod
        def get_review_prompt(requirements, _case):
            return [SystemMessage(content="你是测试评审专家，输出严格 JSON：{review_result:通过/不通过, review_decs:原因}"),
                    HumanMessage(content=f"需求：\n{requirements}\n\n用例：\n{_case}")]

    class verify_coverage_prompt:  # type: ignore[no-redef]
        @staticmethod
        def get_verify_coverage_prompt(requirements, case_list):
            return [SystemMessage(content="你是测试覆盖率专家，输出严格 JSON：{coverage_report, coverage, recomment[]}"),
                    HumanMessage(content=f"需求：\n{requirements}\n\n用例：\n{case_list}")]

    def format_result_to_json(result: str):
        if "<think>" in result:
            result = result.split("</think>")[-1]
        return json.loads(result.replace("```json", "").replace("```", "").strip())

print(f"[import] {log_import}")


# ============================状态定义==========================
class State(TypedDict):
    """完全照搬原 case_generator.py 的 State 定义。"""
    requirements: str
    generated_cases: list
    current_review_case: dict
    coverage_check_result: dict
    review_passed_cases: Annotated[List, operator.add]
    review_failed_cases: Annotated[List, operator.add]


# ============================Pydantic 模型==========================
from pydantic import BaseModel, Field


class GenerateCase(BaseModel):
    case_id: str
    case_name: str
    setup: list
    test_data: dict
    execute_step: list
    except_result: list
    result: Optional[str] = None
    priority: str


class CaseList(BaseModel):
    cases: list[GenerateCase]


# ============================工作流==========================
class GenerateCaseWorkflowMulti:
    """
    用例生成工作流（多模型路由版）。
    节点方法照搬原版；唯一变化：每个节点用 model_router 取模型，而不是全局 llm_model。
    """

    # ---------------- 节点 1：生成用例 ----------------
    @staticmethod
    def _generate_case(state: State):
        requirements = state.get("requirements")
        prompt = generate_case_prompt.get_generate_case_prompt(requirements)
        # ★ 关键差异：按任务类型自动选模型（默认 deepseek-v4-pro）
        llm = get_llm_for_task(TaskType.CASE_GENERATION)
        print(f"[路由] 用例生成 -> {llm.model_name}")
        try:
            response = llm.invoke(prompt)
            result = response.content
            cases = format_result_to_json(result) if isinstance(result, str) else result
            print(f"用例生成完毕，共 {len(cases) if isinstance(cases, list) else 0} 条")
            return {"generated_cases": cases if isinstance(cases, list) else []}
        except Exception as e:
            print(f"生成用例失败：{e}")
            return {"generated_cases": []}

    # ---------------- 节点 2：单条用例评审 ----------------
    @staticmethod
    def _review_case(state: State):
        _case = state.get("current_review_case")
        requirements = state.get("requirements")
        prompt = case_review_prompt.get_review_prompt(requirements, _case)
        llm = get_llm_for_task(TaskType.CASE_REVIEW)
        try:
            response = llm.invoke(prompt)
            result_json = format_result_to_json(response.content)
            if result_json.get("review_result") == "通过":
                _case["review_result"] = "通过"
                _case["review_decs"] = result_json.get("review_decs", "")
                return {"review_passed_cases": [_case]}
            else:
                _case["review_result"] = "未通过"
                _case["review_decs"] = result_json.get("review_decs", "")
                return {"review_failed_cases": [_case]}
        except Exception as e:
            print(f"评审失败：{e}")
            _case["review_result"] = "异常"
            _case["review_decs"] = str(e)
            return {"review_failed_cases": [_case]}

    # ---------------- 路由：用例生成 -> 并发评审 ----------------
    @staticmethod
    def _case_review_router(state: State):
        from langgraph.types import Send
        cases = state.get("generated_cases") or []
        if not cases:
            print("没有可评审的用例，跳过评审")
            return []
        return [Send("用例评审", {"current_review_case": c, "requirements": state.get("requirements")}) for c in cases]

    # ---------------- 节点 3：覆盖率检查 ----------------
    @staticmethod
    def verify_coverage(state: State):
        review_passed_cases = state.get("review_passed_cases") or []
        requirements = state.get("requirements")
        prompt = verify_coverage_prompt.get_verify_coverage_prompt(requirements, review_passed_cases)
        llm = get_llm_for_task(TaskType.COVERAGE_CHECK)
        print(f"[路由] 覆盖率检查 -> {llm.model_name}")
        try:
            response = llm.invoke(prompt)
            result = format_result_to_json(response.content)
            print(f"覆盖率：{result.get('coverage')}；建议补充：{result.get('recomment')}")
            return {"coverage_check_result": result}
        except Exception as e:
            print(f"覆盖率检查失败：{e}")
            return {"coverage_check_result": {"coverage": "0%", "recomment": [], "coverage_report": str(e)}}

    @staticmethod
    def verify_coverage_router(state: State):
        ccr = state.get("coverage_check_result") or {}
        if ccr.get("coverage") == "100%":
            return "保存用例"
        return "补充生成用例"

    # ---------------- 节点 4：补充生成 ----------------
    @staticmethod
    def supplement_generate_case(state: State):
        requirements = state.get("requirements")
        passed = state.get("review_passed_cases") or []
        ccr = state.get("coverage_check_result") or {}
        recomment = ccr.get("recomment", [])
        prompt = generate_case_prompt.get_supplement_generate_case_prompt(requirements, passed, recomment)
        llm = get_llm_for_task(TaskType.CASE_SUPPLEMENT)
        print(f"[路由] 补充生成 -> {llm.model_name}")
        try:
            response = llm.invoke(prompt)
            cases = format_result_to_json(response.content) if isinstance(response.content, str) else response.content
            print(f"补充生成完毕，新增 {len(cases) if isinstance(cases, list) else 0} 条")
            return {"generated_cases": cases if isinstance(cases, list) else []}
        except Exception as e:
            print(f"补充生成失败：{e}")
            return {"generated_cases": []}

    # ---------------- 节点 5：保存用例 ----------------
    @staticmethod
    def save_case(state: State):
        passed = state.get("review_passed_cases") or []
        print(f"最终保留 {len(passed)} 条用例，写入 outputs/cases_multi.json")
        out_path = os.path.join(SCRIPT_DIR, "outputs", "cases_multi.json")
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(passed, f, ensure_ascii=False, indent=2)
        return {}

    # ---------------- 编排 ----------------
    def create_workflow(self):
        from langgraph.constants import START, END
        from langgraph.graph import StateGraph

        g = StateGraph(State)
        g.add_node("用例生成", self._generate_case)
        g.add_node("用例评审", self._review_case)
        g.add_node("用例覆盖率检查", self.verify_coverage)
        g.add_node("补充生成用例", self.supplement_generate_case)
        g.add_node("保存用例", self.save_case)

        g.add_edge(START, "用例生成")
        g.add_conditional_edges("用例生成", self._case_review_router, ["用例评审"])
        g.add_edge("用例评审", "用例覆盖率检查")
        g.add_conditional_edges("用例覆盖率检查", self.verify_coverage_router,
                                ["保存用例", "补充生成用例"])
        g.add_conditional_edges("补充生成用例", self._case_review_router, ["用例评审"])
        g.add_edge("保存用例", END)
        return g.compile()


# ============================Demo 需求==========================
DEFAULT_REQUIREMENT = """
F1.1 用户注册
🧩 功能背景
新用户通过注册方式创建账户，支持邮箱/用户名+密码的注册方式。
🚶 主流程
1. 用户打开注册页，填写注册信息
2. 系统校验格式与唯一性（用户名、邮箱）
3. 提交注册，后台创建账户，初始状态为"正常"
4. 注册成功后自动登录并跳转首页
⚠️ 异常流程
● 邮箱/用户名已被注册：提示"已存在"
● 两次密码不一致：提示用户重新输入
📌 状态规则
● 新用户状态为 "正常"
● 注册时间记录为创建时间，头像为默认图
📌 业务规则
● 用户名唯一，支持 4~20 位字母数字组合
● 密码长度不少于 6 位
● 邮箱必须符合格式 xxx@xxx.xx
"""


# ============================主入口==========================
def main():
    parser = argparse.ArgumentParser(description="多模型路由版用例生成")
    parser.add_argument("--model", type=str, default=None,
                        help="强制把全节点切到某模型，如 deepseek-v4-pro 或 MiniMax-M3")
    parser.add_argument("--task", type=str, default="all",
                        help="只改某个任务类型的路由，配合 --model 使用，如 CASE_GENERATION")
    parser.add_argument("--list-routing", action="store_true", help="打印当前路由表")
    parser.add_argument("--export-usage", type=str, default=None, help="导出本次用量历史")
    args = parser.parse_args()

    if args.list_routing:
        print("当前路由表：")
        print(json.dumps(list_routing(), ensure_ascii=False, indent=2))
        return

    # 可选：动态改路由
    if args.model:
        if args.task == "all":
            for t in TaskType:
                set_routing(t, args.model)
            print(f"[路由覆盖] 全节点 -> {args.model}")
        else:
            t = TaskType(args.task)
            set_routing(t, args.model)
            print(f"[路由覆盖] {t.value} -> {args.model}")

    print("\n当前生效路由：")
    print(json.dumps(list_routing(), ensure_ascii=False, indent=2))

    # 跑工作流
    workflow = GenerateCaseWorkflowMulti().create_workflow()
    print("\n=========== 开始生成用例（多模型路由版） ===========")
    for chunk in workflow.stream({"requirements": DEFAULT_REQUIREMENT},
                                  stream_mode=["messages"], version="v2"):
        try:
            if chunk["type"] == "messages":
                print(chunk["data"][0].content, end="", flush=True)
        except Exception:
            pass

    # 打印用量
    print("\n\n=========== 本次用量汇总 ===========")
    print(json.dumps(get_usage_summary(), ensure_ascii=False, indent=2))

    if args.export_usage:
        export_usage_history(args.export_usage)


if __name__ == "__main__":
    main()
