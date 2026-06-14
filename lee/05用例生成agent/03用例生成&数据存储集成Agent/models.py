# !/usr/bin/env python3,# -*- coding: utf-8 -*-
# --------------------------------------------
# @FilePath    : lee\05用例生成agent\03用例生成+数据存储集成Agent\models.py
# @Author      : Lee大侠
# @Desc        : 这是一个AI测试项目
# @CreateTime  : 2026/04/15 22:19
# @UpdateTime  : 2026/04/15 22:23
# Copyright (c) 2026 Lee大侠. All rights reserved.
# ========================================================


import os
import dotenv
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from langchain_openai.chat_models import ChatOpenAI
dotenv.load_dotenv()

# ============第一步===========全局的配置=========================

# 配置llama-index全局的嵌入模型
Settings.embed_model = OpenAILikeEmbedding(
    model_name=os.getenv("EMBED_MODEL"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)
# 配置llama-index全局的llm
Settings.llm = OpenAILike(
    model=os.getenv("MODEL1"),
    api_base=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
    temperature=0.5,
    context_window=1024 * 100,
    max_tokens=4096,
)


# ===================定义langchian的模型对象===========
# 如果配置的API_KEY 和BASE_URL 使用的使用变量名 OPENAI_API_KEY 和 OPENAI_BASE_URL 在通过ChatOpenAI去初始化模型对象的时候，可以不传参数base_url和api_key
llm_model_ds = ChatOpenAI(
    base_url=os.getenv("DS_BASE_URL"),
    api_key=os.getenv("DS_API_KEY"),    
    model=os.getenv("DS_MODEL"),
    temperature=0.5,
    extra_body={"enable_thinking": False}  
)


# 用例生成场景的模型对象
llm_model = ChatOpenAI(
    # base_url=os.getenv("OPENAI_BASE_URL"),
    # api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.5,
    extra_body={"thinking": {"type": "disabled"}}  
)

# 用例生成场景的模型对象
llm_model_generate = ChatOpenAI(
    # base_url=os.getenv("OPENAI_BASE_URL"),
    # api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.3,
    max_tokens=8192,  # 留足 token 给 5~10 条结构化用例 + 思考标签
    extra_body={"thinking": {"type": "disabled"}}
)

# 用例评审场景的模型对象
llm_model_review = ChatOpenAI(
    # base_url=os.getenv("OPENAI_BASE_URL"),
    # api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.2,
    max_tokens=8192,  # 评审逐条进行，单次输出也需足够空间
    extra_body={"thinking": {"type": "disabled"}}
)

# 覆盖率检查场景的模型对象
llm_model_coverage = ChatOpenAI(
    # base_url=os.getenv("OPENAI_BASE_URL"),
    # api_key=os.getenv("OPENAI_API_KEY"),
    model=os.getenv("OPENAI_MODEL"),
    temperature=0.2,
    max_tokens=8192,  # 覆盖率分析报告含多个 recommend 也需足够空间
    extra_body={"thinking": {"type": "disabled"}}
)


# ===================按场景拆分的别名（语义化，方便未来按场景换模型）===========
# 当前三个别名都指向同一个 llm_model，未来想为「评审」换更便宜的模型、为「生成」换更强的模型时，
# 只需在这里改成不同的 ChatOpenAI 实例即可，业务代码无需改动。



"""
extra_body={"chat_template_kwargs": {"enable_thinking": False}},  # Qwen3 备选
extra_body={"thinking": {"type": "disabled"}},                    # DeepSeek 风格
extra_body={"enable_thinking": False}                             # MiniMax 风格

"""
