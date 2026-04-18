# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : \aiAutoTest\lee\02提示词工程\03大模型上传图片的提示词构成.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 23:17
# @UpdateTime  : 2026/04/15 23:25
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import base64

dotenv.load_dotenv()

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name=os.getenv("OPENAI_MODEL"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

messages = [
    SystemMessage(content="你是一个资深的软件测试工程师，后续需要你根据用户提交的需求文档或者原型图来分析测试点，生成测试用例")
]

import os
from pathlib import Path

# 获取该文件的逻辑父级，即脚本所在目录的绝对路径
script_dir = Path(__file__).parent
# 获取脚本所在目录的绝对路径
print(f"脚本所在目录的绝对路径：{script_dir}")
# 构建图片路径
image_path = script_dir / "msg" / "image.png"
print(f"图片路径：{image_path}")

with open(image_path, "rb") as f:
    image = f.read()
    image_base64 = base64.b64encode(image).decode("utf-8")


user_input = HumanMessage(content=[
    {"type": "text", "text": "请帮我分析图片中内容"},
    {"type": "image","base64": image_base64, "mime_type": "image/png"}
])


messages.append(user_input)

response = llm.invoke(messages)
print(response.content)
