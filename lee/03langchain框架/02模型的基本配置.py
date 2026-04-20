

import os
import dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# 加载.env文件中的环境变量
dotenv.load_dotenv()

LLM = ChatOpenAI(
    model=os.getenv('OPENAI_MODEL'),
    base_url=os.getenv('OPENAI_BASE_URL'),
    api_key=os.getenv('OPENAI_API_KEY'),
    temperature=0.9,  # 越小越确定
    max_retries=6,  # 最大重试次数
    max_tokens=2048  # 输出的最大tokens数量
)


res = LLM.batch([
    "帮我用python写一个pytest+requests的接口测试用例的dome,要求10行以内",
    "请用python写一个爬虫程序，爬取百度首页的源码,10行以内"
    ])

for item in res:
    print(f"流式批处理：\n{item[1].content}\n\n")



