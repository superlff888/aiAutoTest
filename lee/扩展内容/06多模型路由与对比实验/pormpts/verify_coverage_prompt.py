# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\02用例生成+评审的代码rag_agent\rag_agent\pormpts\verify_coverage_prompt.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


from langchain.messages import SystemMessage, HumanMessage

PROMPT = """
你是一位资深的测试专家，接下需要你根据用户提供的需求文档 和测试用例，来分析用户提供的测试用例是否覆盖到了文档中所有的测试点
    
## 分析的流程：
    1、分析当前的需求文档中的测试点有哪些？不得推测或者猜测文档中没有明确的测试点
    
    2、分析当前用例已经覆盖了哪些测试点？有哪些测试点没有覆盖到
    
    3、计算覆盖率（已覆盖的测试点占总测试点的比例）
    
    4、生成覆盖率报告，如果覆盖率没有达到100%，则需要补充生成的建议

        
## 输出的结果必须为严格合法的JSON对象格式的数据，不要输出任何Markdown标记（如json）或解释性文字：
    输出字段：
      coverage_report:"覆盖率报告说明，200字以内"
      coverage:"覆盖率,百分比显示"    
      recomment:需要补充生成的测试用例的测试点

    输出示例1：
        {
            "coverage_report":"经过分析当前的用例覆盖了所有的测试点",
            "coverage":"100%",
            "recomment":[]
        }
        
    输出示例2：
        {
            "coverage_report":"经过分析当前的用例当前的需求文档一共有X个测试点，已经覆盖了A个,还有xx等测试点未覆盖",
            "coverage":"90%",
            "recomment":["注册时输入已注册的账号","注册时两次密码不一致"]
        }
"""


def get_verify_coverage_prompt(requirements, case_list) -> list:
    """获取用例的覆盖率验证提示词"""
    prompt = f"""
    请分析下面的测试用例是否覆盖了需求文档中所有的测试点，并输出检测结果
    ## 需求文档：
    {requirements}  
    ## 用例数据：
    {case_list}
    """
    return [
        SystemMessage(content=PROMPT),
        HumanMessage(content=prompt)
    ]


"""

优化：应该提取测试点，然后验证测试点是否被覆盖，而不是直接让模型分析用例覆盖率，这样会更准确一些

"""