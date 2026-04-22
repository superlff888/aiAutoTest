


from dataclasses import dataclass
import os
import dotenv
from langchain.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool,ToolRuntime


@dataclass
class UserContext:
    user_id: str  # 用户唯一标识


# 2. 模拟用户数据库
USER_DATABASE = {
    "user123": {"姓名": "张三", "账户类型": "高级会员", "余额": 5000, "邮箱": "zhangsan@example.com"},
    "user456": {"姓名": "李四", "账户类型": "普通会员", "余额": 1200, "邮箱": "lisi@example.com"}
}


@tool("获取用户信息", return_direct=True)
def get_user_info(runtime: ToolRuntime[UserContext]) -> str:
    """根据用户ID查询用户信息"""
    user_id = runtime.context.user_id
    user_info = USER_DATABASE.get(user_id)
    if user_info:
        return f"姓名: {user_info['姓名']}, 账户类型: {user_info['账户类型']}, 余额: {user_info['余额']}, 邮箱: {user_info['邮箱']}"
    else:
        return "未找到用户信息"


if __name__ == "__main__":
    dotenv.load_dotenv()
    llm=ChatOpenAI(
        model=os.getenv("OPENAI_MODEL"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),     
        temperature=0
        )  # 初始化大模型
    
    agent = create_agent(
        tools=[get_user_info],
        model=llm,
        system_prompt=SystemMessage(content="你是一个客服助手，协助用户查询他们的账户信息。用户会提供他们的用户ID，你需要调用工具获取并返回他们的账户信息。")  
    )

    response = agent.invoke(
        {"messages":[HumanMessage(content="请帮我查询一下我的账户信息，我的用户ID是user123")]},
        context=UserContext(user_id="user123")
    )

    print("最终返回给用户的结果：\n", response.get("messages")[-1].content)