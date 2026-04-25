
import os
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import TodoListMiddleware, SummarizationMiddleware

from tools import (load_memory, save_memory, clear_memory,
                   write_file, read_file, write_binary_file,
                   read_binary_file, read_directory)
import dotenv

dotenv.load_dotenv()


@dataclass
class AgentContext:
    user_id: str


class MyOneAgent:
    system_prompt = """
                你是我的个人AI编程助手，后续请根据我的指令去完成相关开发工作
                你具备完善的记忆系统：
                    1、如果是第一次运行，我问你第一个问题，回答之前请先去加载记忆中的相关信息，然后再回复我
                    2、当我让你去记住一些内容，或者规则时，请把相关用户的指令规则保存到记忆系统中，无关的内容不进行保存
                        需要保存到记忆中的内容：
                            1、任务目录
                            2、任务的开发进度
                            3、用户的规则指令

                    3、当我让你修改和删除之前记住的内容或规则时，请根据现有记忆的内容，进行修改
                    4、当我让你清空或者忘记之前的所有规则时，请清空记忆中的内容
                对于用户提出的任务，你要先进行分析和规划执行的步骤，然后调用相关工具或能力去完成用户的目标

                如果有任务不确定的信息或者，你不具备的能力时要和用户沟通并确认解决方案    

                """

    def __init__(self):
        # 创建大模型的调用对象
        self.model = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY")
        )
        # 初始一个agent
        self.agent = create_agent(
            system_prompt=self.system_prompt,
            model=self.model,
            tools=[load_memory, save_memory, clear_memory,
                   write_file, read_file, write_binary_file, read_binary_file, read_directory
                   ],
            # 启动短期记忆
            checkpointer=InMemorySaver(),
            # 设置运行上下文的信息
            context_schema=AgentContext,
            # 配置中间件
            middleware=[
                # 任务列表中间件
                TodoListMiddleware(),
                # 对历史聊天进行压缩的中间件
                SummarizationMiddleware(
                    model=self.model,
                    # 当对话的记录超过max_tokens 设置的值后，会进行对上下文进行压缩
                    max_tokens=1024 * 100,
                    # 压缩完，要保留最近的每次对话记录的次数
                    messages_to_keep=10
                )

            ]
        )

    @staticmethod
    def handle_agent_output(response):
        """处理agent的输出结果"""
        for chunk in response:
            match chunk['type']:
                case "messages":
                    print(chunk['data'][0].content, end='')
                case "updates":
                    for step, data in chunk['data'].items():
                        match step:
                            case "model":
                                print('🤖=================【调用大模型执行结果】========步骤完成=============')
                            case "tools":
                                print('🔧===================【调用工具返回结果】========步骤完成=============')
                        for block in data['messages'][-1].content_blocks:
                            match block['type']:
                                case "text":
                                    print(block['text'])
                                case "tool_call":
                                    print(f"🔧工具:{block['name']},参数为：{block['args']}")
                case 'custom':
                    print("✅自定义输出：", chunk['data'])

    @staticmethod
    def output_messages(response):
        # 显示agent调用的结果
        for chunk in response:
            if chunk['type'] == "messages":
                print(chunk['data'][0].content, end='')

    def agent_call(self, messages: list, user_id: str):
        try:
            # 调用agent
            response = self.agent.stream(
                {"messages": messages},
                config={"configurable": {"thread_id": user_id}},
                stream_mode=['custom', 'updates', 'messages'],
                context=AgentContext(user_id=user_id),
                version='v2',
            )
            self.output_messages(response)
        except Exception as e:
            messages = HumanMessage(content=f"执行出错啦，错误信息：{e}")
            self.agent_call(messages, user_id)

    def main(self, user_id: str):
        print("====================这是我的第一个有记忆的agent==================")
        while True:
            messages = []
            user_input = input(f"\n🔥用户【{user_id}】：")
            messages.append(HumanMessage(content=user_input))
            self.agent_call(messages, user_id)


if __name__ == '__main__':
    agent = MyOneAgent()
    agent.main("lee_001")
