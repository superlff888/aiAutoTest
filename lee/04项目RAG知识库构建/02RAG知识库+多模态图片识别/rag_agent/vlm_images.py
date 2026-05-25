# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\04项目RAG知识库构建\02RAG知识库+多模态图片识别\rag_agent\vlm_images.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from langchain.chat_models import init_chat_model
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


def images_vlm_content(image_path):
    """通过视觉模型识别和理解图片内容"""
    system_prompt = """
    你是一个专业的软件测试工程师，请识别用户传入的图片类型，并识别图片中的内容：
    
    # 图片类型：
        包含但不限于下面几种：原型图，业务流程图、拓扑图，系统架构图
    
    # 识别规范：
        如果是原型图,则重点关注图中的功能和布局
        如果是业务流程图，则重点关注业务流程的状态流转
     
    # 注意点：
        如果是一些项目logo或者图标之类的图片信息，不需要进行解读，直接返回：无参考价值的图片       
    """

    # 读取图片内容，转换为base64
    with open(image_path, "rb") as f:
        b64_image_content = b64encode(f.read()).decode("utf-8")
    response = vl_model.invoke([
        {"role": "system", "content": system_prompt},
        {
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
    ])
    return response.content
