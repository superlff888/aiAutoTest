#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leePromptTemplate.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/20 16:07
# @Desc    : 变量插入
#            场景：根据角色、风格、测试对象生成建议描述
# ========================================================
import os

import dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# 创建一个个提示词模板



# 提示词模板: 这种写法更pythonic，直接在字符串中使用{变量名}占位符，LangChain会自动解析并提取变量名，无需显式声明input_variables。
prompt1 = PromptTemplate.from_template(
    """
    你是一个{role}，请用{style}风格输出针对以下测试需求的建议：
    测试需求：{requirement}
    """
)


# 提示词模板:这种显式构造的写法只在一种场景下有意义：你需要严格校验输入变量，或者 input_variables 的顺序需要与模板中出现的顺序不同（这种情况极少）。
prompt2 = PromptTemplate(  # 注意：PromptTemplate.from_template()本质是调用 PromptTemplate.__init__()，效果相同
    input_variables=["role", "style", "requirement"],  # input_variables声明了需要在提示词模板中插入的所有动态数据
    template="""你是一个{role}，请用{style}风格输出针对以下测试需求的建议：
    测试需求：{requirement}""",
)
print(prompt2)

messages2 = prompt1.format( # format将变量替换为str具体值，生成完整提示词内容。
    role="资深测试工程师",
    style="专业、简洁",
    requirement="用户注册功能需要验证邮箱的唯一性"
)
# print(f"提示词为：\n{messages2}")

dotenv.load_dotenv()
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)
if __name__ == '__main__':

    # prompt2.format() 将变量替换为具体值，生成完整提示词内容
    # response = llm.astream(prompt1.format(role="资深测试工程师", style="专业、简洁",requirement="用户注册功能需要验证邮箱的唯一性"))
    response2 = llm.stream(messages2)

    for chunk in response2:
        print(chunk.content, end='')


'''
实际项目中最常见的写法
长提示词通常写在单独的文件中（.txt 或 .yaml），不直接写在代码里：

# prompts.py 或单独文件
SYSTEM_PROMPT = """
你是一个{role}。
职责：{responsibilities}
约束：{constraints}
"""

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)


'''