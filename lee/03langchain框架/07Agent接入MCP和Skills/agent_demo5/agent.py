# @Author  : 木森
# @weixin: python771
import os
from uuid import main

import dotenv
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

dotenv.load_dotenv()


class DeepAgent:

    def __init__(self, user_id):
        self.user_id = user_id

    def create_agent(self):
        self.agent = create_deep_agent(
            system_prompt="""
                你是一个智能助手，请根据用户的需求，进行回答！并协调调用子智能体来完成用户的任务！
            """,
            # 配置模型
            model=ChatOpenAI(model=os.getenv("MODEL")),
            # 配置工具
            tools=[],
            # 配置短期记忆
            checkpointer=InMemorySaver(),
            # 配置agent可以访问的文件目录的根路径
            backend=LocalShellBackend(root_dir=".", virtual_mode=True),
            # 配置长期记忆
            memory=['/memory/AGENT.md'],
            # 配置技能
            skills=['/skills/'],
            # 配置子智能体
            subagents=[
                {
                    "name": "代码审查的智能体",
                    "description": "用于对开发的代码进行审查",
                    "system_prompt": """
                    你是一个代码审查的智能体，负责审查开发的代码是否存在bug,逻辑是否合理，代码是否符合规范！
                    """,
                    "tools": []
                },

                {
                    "name": "代码生成器的智能体",
                    "description": "用于生成代码",
                    "system_prompt": """
                    你是一个代码生成器的智能体，负责生成代码，请勿生成错误代码！
                    """,
                    "tools": []
                }
            ]
        )

    def main(self):
        self.create_agent()
        while True:
            user = input(f"\n🔥用户【{self.user_id}】：")
            # 调用agent
            response = self.agent.stream(
                {"messages": [HumanMessage(content=user)]},
                config={"configurable": {"thread_id": self.user_id}},
                stream_mode=['updates', 'messages', 'custom'],
                version="v2"
            )
            for chunk in response:
                if chunk['type'] == "messages":
                    print(chunk['data'][0].content, end='')


if __name__ == '__main__':
    agent = DeepAgent("musen-001")
    agent.main()
