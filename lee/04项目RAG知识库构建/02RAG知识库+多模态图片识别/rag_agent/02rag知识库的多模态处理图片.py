# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\02RAG知识库+多模态图片识别\rag_agent\02rag知识库的多模态处理图片.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


"""
问题点：原型图、业务流程图等图片内容如何放到知识库中进行集成检索？

思路和步骤：
    1、提取图片？
        图片在PDF或者docx文档中,或者是在线的网页文档(在线的文档)中
            在线的文档中的图片，可以直接下载下来

        PDF或者docx中的图片，可以先通过MinerU解析，讲文档转换为MD，并把图片分离出来



    2、通过多模态大模型理解图片内容，将图片和图片内容构建关联,保存到json文件
        [
            {
                “image_path”:"图片路径1"，
                “image_content”:"图片的内容"
            },
            {
                “image_path”:"图片路径2"，
                “image_content”:"图片的内容"
            },
            {
                “image_path”:"图片路径3"，
                “image_content”:"图片的内容"
            }
        ]


    3、把解析出来图片内容文档，加入到知识库中

"""

import os
import dotenv
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from rag_agent.rag_tools import lightrag_query
from base64 import b64encode

dotenv.load_dotenv()

# 初始模型配置
vl_model = init_chat_model(
    model_provider="openai",
    model=os.getenv("MODEL2"),
    api_key=os.getenv("API_KEY"),
    base_url=os.getenv("BASE_URL"),
    temperature=0.5,
)
# 图片路径
image_path = "../images/da57b25bc7e21bfab456b28f132959f96eaa4b2106adbc69bdbc7e297059b8db.jpg"
image_path2 = "../images/AI平台架构图.png"
# 读取图片内容，转换为base64
with open(image_path2, "rb") as f:
    b64_image_content = b64encode(f.read()).decode("utf-8")
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "请理解下面图片中的内容"},
        {
            "type": "image",
            "base64": b64_image_content,
            "mime_type": "image/jpeg",
        },
    ]
}
response = vl_model.stream([message])
for chunk in response:
    print(chunk.content, end='')
