# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\common\hybrid_structured_invoke.py
# @Author      : Lee大侠
# @Desc        : 混合结构化调用入口（v2 反转优先级）
#                主路径: invoke + format_result + Pydantic model_validate（兼容含/不含 <think> 标签）
#                兜底:   LangChain with_structured_output（tool calling 协议）
#
#                v1 的策略是「含 think 走 A、不含 think 走 B」；实测在国产兼容服务上 with_structured_output
#                经常失败需要二次兜底，导致每次调用都走 2 次 LLM。v2 改为默认走 format_result 主路径，
#                失败才降级到 with_structured_output，正常情况只调用 1 次 LLM。
# @CreateTime  : 2026/06/14
# ========================================================


import logging
from typing import Type, TypeVar, get_origin

from pydantic import BaseModel, ValidationError

from rag_agent.common.model_output_to_json import format_result

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _has_thinking_tags(content: str) -> bool:
    """是否带 <think>...</think> 标签。
    保留作为诊断 helper（v2 主路径不再依赖此判断分流，format_result 自身已能剥标签）。"""
    if not content or not isinstance(content, str):
        return False
    return "<think>" in content and "</think>" in content


def _is_valid_parsed(parsed) -> bool:
    """健壮性检查: 解析结果是否合法（dict 或 list）"""
    return isinstance(parsed, (dict, list))


def _maybe_wrap_list_for_schema(parsed, schema: Type[BaseModel]):
    """
    形态适配：当 parsed 是 list、schema 是仅含一个 list 字段的"容器型 BaseModel"时，
    自动包装为 {field_name: parsed} 再交给 model_validate。

    场景：prompt 引导 LLM 输出裸 JSON 数组 [{...},{...}]，但 schema 是 {cases: list[...]}
    这种"容器型"封装。两者形态不一致会导致 ValidationError，本函数负责对齐。

    对于不符合"单 list 字段容器"模式的 schema 一律原样透传（不做隐式行为）。
    """
    if not isinstance(parsed, list):
        return parsed
    if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
        return parsed
    fields = schema.model_fields
    if len(fields) != 1:
        return parsed
    field_name, field_info = next(iter(fields.items()))
    # 字段注解的 origin 为 list（如 list[GenerateCase]）才认为是容器型
    if get_origin(field_info.annotation) is list:
        logger.debug(f"[hybrid] 自动包装 list 为 {{'{field_name}': [...]}}")
        return {field_name: parsed}
    return parsed


def hybrid_structured_invoke(
    llm,
    messages: list,
    schema: Type[T],
) -> T:
    """
    兼容性优先的结构化调用入口（v2 反转优先级）

    主路径（默认走）:
        llm.invoke(messages) → format_result(content) → schema.model_validate(dict)
        - format_result 自动剥 <think> 标签和 ```json``` 标记
        - 含/不含思考标签都能处理
        - 单次 LLM 调用

    兜底（主路径失败才走）:
        llm.with_structured_output(schema).invoke(messages)
        - 走 LangChain tool calling 协议，再调一次 LLM
        - 适合主路径解析失败时（如模型返回非 JSON 自然语言）

    :param llm: LangChain chat model
    :param messages: list of BaseMessage
    :param schema: 目标 Pydantic 模型类
    :return: schema 的实例
    :raises: ValueError 当主路径和兜底都失败时
    """
    # ===== 主路径: invoke + format_result + model_validate =====
    try:
        response = llm.invoke(messages)
        raw_content = response.content or ""
    except Exception as e:
        # invoke 本身失败（网络/API key 等），降级到 with_structured_output 还是会失败，直接抛
        raise ValueError(f"LLM 调用失败: {type(e).__name__}: {e}")

    has_thinking = _has_thinking_tags(raw_content)
    logger.debug(f"[hybrid] 主路径 raw_len={len(raw_content)}, has_thinking={has_thinking}")

    try:
        # 步骤 1: format_result 剥 <think> + ```json``` 标记 + 解析为 dict/list
        parsed = format_result(raw_content)
        # 健壮性检查: parsed 必须是 dict 或 list
        if not _is_valid_parsed(parsed):
            raise ValueError(
                f"format_result 解析结果类型不合法: {type(parsed).__name__}"
            )
        # 形态适配: 若 parsed 是 list 且 schema 是单 list 字段容器, 自动包装
        parsed = _maybe_wrap_list_for_schema(parsed, schema)
        # 步骤 2: Pydantic 强校验
        return schema.model_validate(parsed)
    except (ValidationError, ValueError) as e:
        # 主路径失败：把 LLM 实际返回内容截断打到终端，便于定位是"返回空 / 仅思考标签 / JSON 残缺"
        raw = raw_content or ""
        preview_head = raw[:500].replace("\n", "\\n")
        preview_tail = raw[-500:].replace("\n", "\\n")
        print(
            f"[hybrid] 主路径失败, 降级到 with_structured_output。\n"
            f"  异常: {type(e).__name__}: {e}\n"
            f"  raw_content 长度: {len(raw)}\n"
            f"  raw_content 前 500 字符: {preview_head}\n"
            f"  raw_content 末尾 500 字符: {preview_tail}"
        )
        return _invoke_via_structured_output(llm, messages, schema)


def _invoke_via_structured_output(llm, messages: list, schema: Type[T]) -> T:
    """
    通过 LangChain 原生 with_structured_output 调用（兜底路径）。
    失败时不再二次兜底（主路径已经做过 format_result+model_validate），直接抛 ValueError。
    """
    try:
        structured_llm = llm.with_structured_output(schema)
        return structured_llm.invoke(messages)
    except Exception as e:
        raise ValueError(
            f"hybrid_structured_invoke 全部路径失败。"
            f"主路径 format_result+model_validate 已失败，with_structured_output 兜底也失败: "
            f"{type(e).__name__}: {e}"
        )
