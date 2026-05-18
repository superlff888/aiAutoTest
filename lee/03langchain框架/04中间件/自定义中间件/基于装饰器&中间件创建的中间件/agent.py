# @Author  : 木森
# @weixin: python771
import os
import dotenv

from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver
from midelwerver import before_agent_middleware, after_agent_middleware
from MyMiddlewer import MyAgentMiddleware

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
            middleware=[
                # 装饰器定义的中间件
                before_agent_middleware,
                after_agent_middleware,
                # 类定义的中间件
                MyAgentMiddleware()
            ]
        )

    def handel_agent_output(self, response):
        """处理agent实时输出"""
        for chunk in response:
            if chunk['type'] == "messages":
                print(chunk['data'][0].content, end='')
            elif chunk['type'] == "updates":
                for step, data in chunk['data'].items():
                    if step == "model":
                        print('🤖=================【调用大模型执行结果】========步骤完成=============')
                    elif step == "tools":
                        print('🔧===================【调用工具返回结果】========步骤完成=============')
                    if data:
                        print(data['messages'])
            elif chunk['type'] == 'custom':
                print("✅自定义输出：", chunk['data'])

    def run(self):
        while True:
            user = input(f"\n🔥用户【{self.user_id}】：")
            try:
                # 调用agent
                response = self.agent.stream({"messages": [HumanMessage(content=user)]},
                                             config={"configurable": {"thread_id": self.user_id}},
                                             stream_mode=['updates', 'messages', 'custom'],
                                             version="v2"
                                             )
                # 输出流式执行的结果
                self.handel_agent_output(response)
            except Exception as e:
                raise e
                print("执行出错：", e)


if __name__ == '__main__':
    agent = Agent("musen_001")
    agent.run()
