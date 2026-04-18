#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeFewShotPromptTemplate.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151010
# @Date    : 2025/7/20 17:34
# @Desc    : 样本模板
#            场景：输入 Bug 文本 → 输出 Bug 类型
# ========================================================
import dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate


dotenv.load_dotenv()
llm = ChatOpenAI(
    model_name=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)
# 样本示例
examples = [
    {"input": "点击登录按钮无反应", "output": "功能缺失"},
    {"input": "加载页面卡顿超过10秒", "output": "性能问题"}
]


example_prompt_2 = PromptTemplate.from_template(
    "Bug描述：{input}\nBug类型：{output}"
)

# 创建一个FewShotPromptTemplate对象。此对象接收少量示例和少量示例的格式化程序
few_shot_prompt = FewShotPromptTemplate(
    # 样本示例
    examples=examples,
    # 输出样板格式
    example_prompt=example_prompt_2,
    # 提示词最前的一句话
    prefix="请根据以下示例判断Bug类型：",
    # 提示词最后面的一句话
    suffix="Bug描述：{user_input}\nBug类型：", # 正好作为大模型输出内容的提示语言
    # （声明）用户输入的变量
    input_variables=["user_input"]
)

response = llm.stream(few_shot_prompt.format(user_input = "用户头像无法上传", output="123"))
for chunk in response:
    print(chunk.content, end='')


