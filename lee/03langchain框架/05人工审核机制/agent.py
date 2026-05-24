

import os
import dotenv

from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from tools import execute_command,get_database_connect_config
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command
from typing import Iterable
import json

dotenv.load_dotenv()


class Agent:
    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL_QWEN3"),
    )

    def __init__(self, user_id):
        self.user_id = user_id
        self.agent = create_agent(
            model=self.model,
            # 启动短期记忆
            checkpointer=InMemorySaver(),
            tools=[execute_command, get_database_connect_config],
            middleware=[
                HumanInTheLoopMiddleware(  # 中断配置
                    interrupt_on={  
                        # database_handler 工具名称和 tool() 内的 name 必须一致
                        "终端命令执行工具": {
                            "allowed_decisions": ["approve", "reject", "edit"]
                        },
                        "获取数据库连接配置": False  # 这个工具不需要人工审核
                        
                    },
                    description_prefix="⚠️ 终端命令工具执行待人工审核"
                )
            ]
        )

    def handel_agent_output(self, response):
        """处理agent实时输出"""
        if not isinstance(response, Iterable):
            print(response)
            return
        for chunk in response:
            if not chunk.get('type'):
                continue
            if chunk['type'] == "messages":
                print(chunk['data'][0].content, end='')
            elif chunk['type'] == "updates":
                for step, data in chunk['data'].items():
                    if step == "model":
                        print('\n🤖=================【调用大模型执行结果】========步骤完成=============')
                        if data:
                            print(data['messages'][0].content, end='\n')
                    elif step == "tools":
                        print('\n🔧===================【调用工具返回结果】========步骤完成=============')
                    elif step == '__interrupt__':  # 获取到中断时人工审核的操作结果(approve/reject/edit)
                        print("=================当前的操作需要人工审批=================")
                        print("需要审批执行的工具：", data[0].value['action_requests'][0]['name'])
                        print("工具执行参数：", data[0].value['action_requests'][0]['args'])
                        decision = input("请输入是否同意执行(approve/reject/edit，直接回车默认approve)：")  # 简单的人工审批交互
                        if decision == "approve" or decision == "":
                            if decision == "":
                                print("用户未输入，默认同意执行")
                            else:
                                print("用户同意执行")
                            actions = {"type": "approve"}
                        elif decision == "edit":
                            print("请输入修改后的参数（JSON格式）：")
                            try:
                                edited_args = json.loads(input())
                                actions = {"type": "edit", "edited_args": edited_args}
                                print(f"用户修改参数为：{edited_args}")
                            except json.JSONDecodeError:
                                print("JSON格式错误，取消编辑")
                                actions = {"type": "reject"}
                        else:
                            print("用户拒绝执行")
                            actions = {"type": "reject"}
                        # 恢复agent的继续执行的状态
                        return actions
            elif chunk['type'] == 'custom':
                print("✅自定义输出：", chunk['data'], end='\n\n')

    def run(self):
        approval_decision = None
        while True:

            try:
                # 判断是否有中断审批的结果
                if approval_decision:
                    print("==============开始恢复执行==============")
                    response = self.agent.stream(
                        Command(resume={"decisions": [approval_decision]}), 
                        config={"configurable": {"thread_id": self.user_id}},
                        stream_mode=['updates', 'messages', 'custom'],
                        version="v2"
                    )
                else:
                    user = input(f"\n🔥用户【{self.user_id}】：")
                    if user.strip().lower() == "exit":
                        print("👋 程序已退出")
                        break
                    # 调用agent
                    response = self.agent.stream({"messages": [HumanMessage(content=user)]},
                                                 config={"configurable": {"thread_id": self.user_id}},
                                                 stream_mode=['updates', 'messages', 'custom'],
                                                 version="v2"
                                                 )
                # 输出流式执行的结果
                approval_decision = self.handel_agent_output(response)  # 处理agent实时输出时，只有中断事件做了return，其他都是None
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                break
            except Exception as e:
                print("执行出错：", e)
                raise e


if __name__ == '__main__':
    agent = Agent("lee_001")
    agent.run()


"""
agent:
    model模型(负责分析和决策) + 工具（具体干事情的） + 记忆(短期(state)、长期(momery),中间件,人工审批)

mcp:
    - playwright-mcp,
    - agent-browser
skills(技能):
    - 对于特定问题处理的能力(一套标准的处理流程)


"""