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


def _try_complete_truncated_json(truncated: str, error_pos: int) -> str:
    """尝试补全截断/缺闭合的 JSON。

    适用场景：LLM 输出的 JSON 在末尾缺 ] / }（典型如多条用例生成的数组在最后一条后忘闭合）。
    策略：
      1) 截到 json.loads 报错位置之前
      2) 用栈追踪 head 中所有未闭合的 [ 和 {
      3) 若最后一个 token 是未闭合的字符串（in_string=True），先闭合 "
      4) 若末尾残留 ',' 或 ':'，先去掉
      5) 反向补全 ] / }

    :param truncated: 原始 JSON 字符串（已剥 <think> 和 ```json``` 标记）
    :param error_pos: json.loads 抛 JSONDecodeError 时的 pos
    :return: 补全后的 JSON 字符串（仍可能解析失败，由调用方二次校验）
    """
    # 1) 截到错误位置之前
    head = truncated[:error_pos].rstrip()

    # 2) 末尾残留 ',' / ':' / ',]' / ',}' 等不完整 token：去掉
    while head and head[-1] in (',', ':'):
        head = head[:-1].rstrip()

    # 3) 用栈追踪 head 中未闭合的 [ {
    stack = []
    in_string = False
    escape = False
    for c in head:
        if escape:
            escape = False
        elif c == '\\':
            escape = True
        elif c == '"':
            in_string = not in_string
        elif not in_string:
            if c == '[':
                stack.append(']')
            elif c == '{':
                stack.append('}')
            elif c in ']}' and stack and stack[-1] == c:
                stack.pop()

    # 4) 字符串未闭合：先闭合 "
    if in_string:
        head += '"'

    # 5) 反向补全 ] }
    if stack:
        head += ''.join(reversed(stack))

    return head


def format_result(result: str) -> dict | list:
    """
    解析 LLM 输出为 Python 对象
    兼容：<think>...</think> 标签、```json``` 标记、纯 JSON 字符串、末尾缺闭合的 JSON

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

    # 3.5) 剥完标签/markdown 后如果为空，常见于 LLM 只返回了 <think>...</think> 而忘了输出 JSON
    if not result:
        raise ValueError(
            "format_result 解析失败：LLM 输出剥除 <think> 标签和 ```json``` 标记后为空。"
            "可能原因：1) LLM 仅返回了思考内容未输出 JSON；"
            "2) LLM 返回内容被截断；"
            "3) 思考标签未闭合。"
        )

    # 4) JSON 解析（可能是 dict 或 list）。先尝试正常解析，失败再尝试"末尾缺闭合"补全。
    try:
        parsed = json.loads(result)
    except json.JSONDecodeError as first_err:
        # 尝试自动补全（典型场景：LLM 输出多条 case 数组，最后一条 case 的 } 后忘加 ] 闭合）
        try:
            completed = _try_complete_truncated_json(result, first_err.pos)
            parsed = json.loads(completed)
        except Exception:
            # 补全后仍失败：抛原始错误，保留完整上下文
            raise ValueError(
                f"format_result JSON 解析失败（自动补全后仍失败）。"
                f"原始错误: {first_err}。"
                f"错误位置前后 100 字符: ...{result[max(0, first_err.pos-50):first_err.pos+50]}..."
            ) from first_err

    # 5) 输出类型检查
    if not isinstance(parsed, (dict, list)):
        raise ValueError(
            f"format_result 解析结果非 dict/list, 当前: {type(parsed).__name__}"
        )
    return parsed
