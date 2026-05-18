# @Author  : 木森
# @weixin: python771
import json
import os

from langchain.agents import AgentState
from langgraph.runtime import Runtime
from langchain.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain.agents.middleware import (AgentMiddleware,
                                         before_agent,
                                         after_agent,
                                         before_model,
                                         after_model,
                                         wrap_tool_call,
                                         wrap_model_call,
                                         dynamic_prompt
                                         )


@before_agent
def before_agent_middleware(state: AgentState, runtime: Runtime):
    """在agent执行之前执行"""
    print("========agent初始化的状态====")
    print(state)

    # 判断是否有历史聊天记录
    if os.path.exists("message.json"):
        # 加载agent的历史聊天记录
        with open("message.json", "r", encoding="utf-8") as f:
            message_list = json.load(f)
            for msg in state['messages']:
                message_list.append(msg)
            # # 保存到agent的状态中(短期记忆)
            state['messages'] = message_list
    runtime.stream_writer({"type": "status", "message": "初始化Agent的状态", })
    runtime.stream_writer({"type": "status", "message": "Agent ready!"})


@after_agent
def after_agent_middleware(state: AgentState, runtime: Runtime):
    """在agent执行之后执行"""
    print("========agent执行完毕的状态====")
    print(state)
    # 将 massage中的历史聊天记录保存到数据库或者文件中
    message_list = []
    for message in state['messages']:
        if isinstance(message, HumanMessage):
            message_list.append({"role": 'user', "content": message.content})
        elif isinstance(message, AIMessage):
            message_list.append({"role": 'assistant', "content": message.content})
        elif isinstance(message, SystemMessage):
            message_list.append({"role": 'system', "content": message.content})
        elif isinstance(message, ToolMessage):
            message_list.append({"role": 'tool', "content": message.content})
    # 将agnet的聊天记录保存的json文件
    with open("message.json", "w", encoding="utf-8") as f:
        json.dump(message_list, f, ensure_ascii=False)

    runtime.stream_writer({"type": "status", "message": "Agent执行完毕"})
