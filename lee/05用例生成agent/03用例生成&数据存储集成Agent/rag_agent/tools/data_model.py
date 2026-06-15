# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\tools\data_model.py
# @Author      : Lee大侠
# @Desc        : 测试用例 Pydantic 数据模型（与 generate_case_prompt 输出字段保持一致，
#                供 workflow 与 hybrid_structured_invoke 共用）
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/06/14
# ========================================================


from typing import List, Optional
from pydantic import BaseModel, Field


class GenerateCase(BaseModel):
    """测试用例数据模型 - 与 generate_case_prompt.py 输出字段保持一致"""
    case_id: str = Field(..., description="用例编号，格式 TC-FUNC-001 依次递增")
    priority: str = Field(..., description="优先级，P0/P1/P2")
    case_name: str = Field(..., description="用例名称，简明描述验证目的")
    setup: List[str] = Field(default_factory=list, description="前置条件")
    test_data: dict = Field(default_factory=dict, description="测试数据")
    # execute_step 和 expected_result 是用例核心字段，正常不应省略。
    # 但 LLM 偶尔会"偷懒"漏掉某些 case 的这两个字段，导致整个 list 校验失败。
    # 这里设默认值 [] 作为兜底——LLM 万一漏掉，单条 case 失败而非整个 workflow 崩溃。
    # （prompt 中另有强约束从源头禁止省略）
    execute_step: List[str] = Field(default_factory=list, description="操作步骤（必填，prompt 中已强约束不可省略；此处 [] 仅作兜底）")
    expected_result: List[str] = Field(default_factory=list, description="预期结果，关键断言（必填，prompt 中已强约束不可省略；此处 [] 仅作兜底）")
    result: Optional[str] = Field(None, description="实际结果，初始为 null")
    # 用例管理的需求编号 - 由调用方注入，LLM 不需要生成
    requirement_id: Optional[str] = Field(None, description="需求编号，调用方注入")


class CaseList(BaseModel):
    """用例列表 - 用于 hybrid_structured_invoke 强校验"""
    cases: List[GenerateCase] = Field(..., description="用例列表")


class CoverageResult(BaseModel):
    """覆盖率检查结果 - 用于 hybrid_structured_invoke 强校验"""
    coverage_report: str = Field(..., description="覆盖率分析说明，150 字以内")
    coverage: str = Field(..., description='百分比格式，如 "100.0%"、"75.0%"，保留一位小数')
    recommend: List[str] = Field(default_factory=list, description="未完全覆盖的测试点清单")


class ReviewResult(BaseModel):
    """用例评审结果 - 用于 hybrid_structured_invoke 强校验"""
    review_result: str = Field(..., description='"通过" 或 "不通过"')
    review_desc: str = Field(..., description="评审结论说明，50 字以内")
    failed_dimensions: List[str] = Field(default_factory=list, description="不通过的维度名称")
