# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\common\hybrid_structured_invoke.py
# @Author      : Lee大侠
# @Desc        : 兼容思考型模型的混合结构化调用入口
#                路径A: 思考型 → format_result + Pydantic model_validate
#                路径B: 非思考型 → LangChain with_structured_output
#                兜底: 任一失败自动降级
# @CreateTime  : 2026/06/14
# ========================================================


import logging
from typing import Type, TypeVar, get_origin

from pydantic import BaseModel, ValidationError

from rag_agent.common.model_output_to_json import format_result

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _has_thinking_tags(content: str) -> bool:
    """健壮性检查 1: 是否带 <think>...</think> 标签"""
    if not content or not isinstance(content, str):
        return False
    return "<think>" in content and "</think>" in content


def _is_valid_parsed(parsed) -> bool:
    """健壮性检查 2: 解析结果是否合法（dict 或 list）"""
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
    兼容思考型模型的混合结构化调用

    路径 A (思考型模型 - 带 <think> 标签):
        llm.invoke(messages) → format_result(content) → schema.model_validate(dict)

    路径 B (非思考型模型 - 无 <think> 标签):
        llm.with_structured_output(schema).invoke(messages)
        (LangChain 内部走 tool calling, 自动按 schema 解析)

    两种路径都得到 Pydantic 强校验。
    路径 A 失败时降级到路径 B；路径 B 失败时降级到二次兜底。

    :param llm: LangChain chat model
    :param messages: list of BaseMessage
    :param schema: 目标 Pydantic 模型类
    :return: schema 的实例
    :raises: ValueError 当全部路径都失败时
    """
    # ===== 1. 先 invoke 拿 raw content (统一入口) =====
    try:
        response = llm.invoke(messages)
        raw_content = response.content or ""
    except Exception as e:
        raise ValueError(f"LLM 调用失败: {type(e).__name__}: {e}")

    # ===== 2. 健壮性检查: 是否带思考标签 =====
    has_thinking = _has_thinking_tags(raw_content)
    logger.debug(f"[hybrid] has_thinking={has_thinking}, raw_len={len(raw_content)}")

    # ===== 3a. 路径 A: 思考型模型 =====
    if has_thinking:
        try:
            # 步骤 1: format_result 剥 <think> + 解析为 dict
            parsed = format_result(raw_content)
            # 健壮性检查 2: parsed 必须是 dict 或 list
            if not _is_valid_parsed(parsed):
                raise ValueError(
                    f"format_result 解析结果类型不合法: {type(parsed).__name__}"
                )
            # 形态适配：若 parsed 是 list 且 schema 是单 list 字段容器，自动包装
            parsed = _maybe_wrap_list_for_schema(parsed, schema)
            # 步骤 2: Pydantic 强校验
            return schema.model_validate(parsed)
        except (ValidationError, ValueError) as e:
            logger.warning(f"[hybrid] 路径 A 失败, 降级到路径 B: {e}")
            return _invoke_via_structured_output(llm, messages, schema)

    # ===== 3b. 路径 B: 非思考型模型 =====
    else:
        return _invoke_via_structured_output(llm, messages, schema)


def _invoke_via_structured_output(llm, messages: list, schema: Type[T]) -> T:
    """
    通过 LangChain 原生 with_structured_output 调用
    这是路径 B, 也是路径 A 失败后的兜底
    """
    try:
        structured_llm = llm.with_structured_output(schema)
        return structured_llm.invoke(messages)
    except Exception as e:
        logger.warning(
            f"[hybrid] with_structured_output 失败, 兜底到 format_result+model_validate: {e}"
        )
        # 二次兜底: 手动 invoke + format_result + model_validate
        try:
            response = llm.invoke(messages)
            parsed = format_result(response.content or "")
            if not _is_valid_parsed(parsed):
                raise ValueError(f"兜底解析结果类型不合法: {type(parsed).__name__}")
            # 形态适配：与路径 A 保持一致，裸 list 自动包装
            parsed = _maybe_wrap_list_for_schema(parsed, schema)
            return schema.model_validate(parsed)
        except Exception as e2:
            raise ValueError(
                f"hybrid_structured_invoke 全部路径失败。"
                f"最后错误: {type(e2).__name__}: {e2}"
            )
