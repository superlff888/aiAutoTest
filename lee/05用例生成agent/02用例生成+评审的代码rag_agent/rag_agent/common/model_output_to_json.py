# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\02用例生成+评审的代码rag_agent\rag_agent\common\model_output_to_json.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
为了兼容各个厂商大模型调用输出的结果进行格式化处理，
封装下面这个结果处理的函数，主要是考虑到有些模型厂商输出的结果带有<think></think>标签，在进行json格式化处理的时候会报错！
"""
import json


def format_result_to_json(result: str):
    # 判断输出的结果中是否包含<think>推理的内容，如果有则去除
    if "<think>" in result:
        result = result.split("</think>")
        print("推理结果为:", result[0].replace("<think>", ""))
        # 最终生成的用例数据
        print("测试用例:", result[1].replace('```json', '').replace('```', '').strip())
        result = result[1].replace('```json', '').replace('```', '').strip()
    # 把```json  和```去掉 然后转换为json数据
    json_result = json.loads(result)
    print("将json转换为python的数据类型：", json_result)
    return json_result
