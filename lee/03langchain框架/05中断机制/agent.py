# @Author  : 木森
# @weixin: python771
import os
import dotenv

from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from tools import execute_command
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command
from typing import Iterable

dotenv.load_dotenv()


class Agent:
    model = ChatOpenAI(
        model=os.getenv("MODEL"),
    )

    def __init__(self, user_id):
        self.user_id = user_id
        self.agent = create_agent(
            model=self.model,
            # 启动短期记忆
            checkpointer=InMemorySaver(),
            tools=[execute_command],
            middleware=[
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        # 工具名称：True| False
                        "终端命令执行工具": True
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
                        print('🤖=================【调用大模型执行结果】========步骤完成=============')
                        if data:
                            print(data['messages'][0].content)
                    elif step == "tools":
                        print('🔧===================【调用工具返回结果】========步骤完成=============')
                        print(data)
                    elif step == '__interrupt__':
                        print("=================当前的操作需要人工审批=================")
                        print("需要审批执行的工具：", data[0].value['action_requests'][0]['name'])
                        print("工具执行参数：", data[0].value['action_requests'][0]['args'])
                        result = input("请输入是否同意执行(yes/no)：")
                        if result == "yes":
                            print("用户同意执行")
                            actions = {"type": "approve"}
                        else:
                            print("用户拒绝执行")
                            actions = {"type": "reject"}
                        # 恢复agent的继续执行的状态
                        return actions
            elif chunk['type'] == 'custom':
                print("✅自定义输出：", chunk['data'])

    def run(self):
        result = None
        while True:

            try:
                # 判断是否有中断审批的结果
                if result:
                    print("==============开始恢复执行==============")
                    response = self.agent.stream(
                        Command(resume={"decisions": [result]}),
                        config={"configurable": {"thread_id": self.user_id}},
                        stream_mode=['updates', 'messages', 'custom'],
                        version="v2"
                    )
                else:
                    user = input(f"\n🔥用户【{self.user_id}】：")
                    # 调用agent
                    response = self.agent.stream({"messages": [HumanMessage(content=user)]},
                                                 config={"configurable": {"thread_id": self.user_id}},
                                                 stream_mode=['updates', 'messages', 'custom'],
                                                 version="v2"
                                                 )
                # 输出流式执行的结果
                result = self.handel_agent_output(response)  # 处理agent实时输出时，只有中断事件做了return，其他都是None
            except Exception as e:
                raise e
                print("执行出错：", e)


if __name__ == '__main__':
    agent = Agent("musen_001")
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