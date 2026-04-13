#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ========================================================
# @File    : leeChatPromptTemplate.py
# @Project : PythonProject
# @Author  : Lee大侠
# @WeChat  : 15715151020
# @Date    : 2025/7/20 19:46
# @Desc    : 多轮对话模板 ~ MessagesPlaceholder 动态插入消息列表
#             [
#              系统消息,
#              MessagesPlaceholder("chat_history"),  # 动态历史：代码执行中会被历史对话列表数据替换
#              当前用户问题
#             ]
# ========================================================
import os
import dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

# 1. 创建包含消息占位符的对话提示模板
prompt = ChatPromptTemplate.from_messages([  # 参数为列表
    # 系统指令（固定不变）,给系统指定一个旅行助手的角色
    # ("system", "你是一个乐于助人的旅行助手，用中文回答用户问题"),
    SystemMessage("你是一个乐于助人的旅行助手，用中文回答用户问题").content,
    # 消息占位符 - 这里将插入完整的对话历史
    # MessagesPlaceholder的位置被 chat_history 列表里的所有历史消息替换
    MessagesPlaceholder(variable_name="chat_history"),  # variable_name声明了变量chat_history

    # 当前用户的最新问题（动态变量）
    # ("human", "{user_input}")
    HumanMessage("{user_input}").content
])

# 2. 模拟对话历史（实际应用中会从数据库或内存中获取）
chat_history = [
    HumanMessage(content="我想去北京旅游"),  # 用户第一条消息
    AIMessage(content="北京是个很棒的选择！您对什么景点感兴趣？"),  # AI回复
    HumanMessage(content="我想参观故宫和长城"),  # 用户第二条消息
    AIMessage(content="好的呀，尽管问我")  # AI回复
]

# 3. 当前用户的新问题
current_question = HumanMessage(content="这两个景点需要提前多久预订门票？").content

# 4. 实际使用示例（连接LLM）
dotenv.load_dotenv()
llm = ChatOpenAI(
    model_name=os.getenv("MODEL_NAME_V3"),
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

# 5.创建处理对话历史的调用链
chain = prompt | llm

print("大模型回复：\n")
# 模拟连续对话  stream：流式输出
response = chain.invoke({
    "chat_history": chat_history,
    "user_input": current_question
})
print("response数据类型:", type(response))
print(f"response原始数据:{response}")
print("最新回复:\n", response.content)

# 6. 更新对话历史（实际应用中会保存到数据库）
chat_history.extend([
    HumanMessage(content=current_question),
    AIMessage(content=response.content)
])

# 下一轮对话示例
next_question = "故宫附近有什么推荐的酒店？"
# 第二次使用调用链时，chat对话模式的提示词模板已经更新（更新后的对话历史 chat_history 和新的用户问题 next_question）
# 即还是原来的调用链，只是提示词模板发生了变化
next_response = chain.invoke(  # 链式调用（Runnable），且需要传入字典类型参数
    # 1. 含最新历史对话列表数据的消息模板 a = prompt.invoke({"chat_history": chat_history,"user_input": next_question})
    # 2. 含最新历史对话列表数据的消息模板 llm.invoke(a)
    {
        "chat_history": chat_history,  # 历史chat已包含新对话
        "user_input": next_question
    }
)

print("\n============================ 第二轮对话 ==================================\n")
print("问题:", next_question)
print("回复:", next_response.content)



"""
【角色】你是一位顶尖的电子产品营销文案写手。
【任务】为我公司的新款 HydraTech 智能保温杯撰写一段吸引人的产品特点描述。
【约束】描述需面向都市白领群体，突出健康提醒、长效保温、设计简约三大核心卖点，语言简洁有力，充满科技感。
【格式】最终输出为一段不超过 150 字的文案，并额外用 - 列出三个最突出的技术参数。
"""