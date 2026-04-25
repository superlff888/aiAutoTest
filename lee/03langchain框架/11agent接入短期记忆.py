
import os
import dotenv
from langchain_openai import ChatOpenAI

from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage

from langgraph.checkpoint.memory import InMemorySaver


"""
1. 短期记忆（State）、Context、长期记忆都是上下文：
    （1）短期记忆自动储存在state["messages"]中，运行时可通过 runtime.state["messages"] 获取
    （2）context自动储存在runtime.context中，运行时可通过 runtime.context.Context类属性 获取
    （3）长期记忆保存在可通过store.put写入store中
2. 其他上下文见课件
"""
dotenv.load_dotenv()


"""
开启短期记忆之后：
和agent所有的对话都会保存在 运行上下文的 state.messages属性中：[系统提示词，用户消息，AI回复的消息，用户消息，AI回复的消息]

短期记忆只有本次运行agent的时候生效，保存在内存里面，无法持久化存储

"""


class ShortTermMemoryAgent:
    minimax27 = ChatOpenAI(
                    model=os.getenv("OPENAI_MODEL"),
                    base_url=os.getenv("OPENAI_BASE_URL"),
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.9
                    )  

    agent = create_agent(
        minimax27,
        system_prompt=SystemMessage(content="你是一个资深测试工程师"),
        checkpointer=InMemorySaver()
    )
    
    @staticmethod
    def output_messages(response):
        for chunk in response:
            item = chunk['type']
            match item:
                case 'messages':
                    print(chunk["data"][0].content,end='')

    def main(self):
        print('----------------------------开始运行agent------------------------------------')
        user_input = input("\n请输入消息（输入exit退出）：")
        messages= []
        messages.append(user_input)
        response = self.agent.stream(
            {'messages':messages},
            config={"configurable":{"thread_id":"tc-oo1"}},
            stream_mode=["updates", "custom", "messages"],
            version = "v2"
        )

        self.output_messages(response)

if __name__ == "__main__":
    ShortTermMemoryAgent().main()