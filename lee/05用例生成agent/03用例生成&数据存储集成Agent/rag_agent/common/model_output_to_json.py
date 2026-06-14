# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\rag_agent\common\model_output_to_json.py
# @Author      : Lee大侠
# @Desc        : LLM 输出解析工具（供 hybrid_structured_invoke 调用）
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/06/14
# ========================================================


"""
为了兼容各个厂商大模型调用输出的结果进行格式化处理，封装下面这个结果处理的函数。
主要是考虑到有些模型厂商输出的结果带有 <think></think> 标签，在进行 json 格式化处理时会报错。
"""
import json


def format_result(result: str) -> dict | list:
    """
    解析 LLM 输出为 Python 对象
    兼容：<think>...</think> 标签、```json``` 标记、纯 JSON 字符串

    :param result: LLM 返回的原始字符串
    :return: 解析后的 dict 或 list
    :raises ValueError: 输入非法、解析失败或解析结果类型非 dict/list 时
    """
    # 1) 输入类型检查
    if not result or not isinstance(result, str):
        raise ValueError(f"format_result 输入必须是非空字符串, 当前类型: {type(result).__name__}")

    # 2) 剥思考标签：只取 </think> 之后的内容
    if "<think>" in result and "</think>" in result:
        result = result.split("</think>", 1)[1]

    # 3) 剥 markdown 标记
    result = result.replace('```json', '').replace('```', '').strip()

    # 4) JSON 解析（可能是 dict 或 list）
    parsed = json.loads(result)

    # 5) 输出类型检查
    if not isinstance(parsed, (dict, list)):
        raise ValueError(
            f"format_result 解析结果非 dict/list, 当前: {type(parsed).__name__}"
        )
    return parsed
