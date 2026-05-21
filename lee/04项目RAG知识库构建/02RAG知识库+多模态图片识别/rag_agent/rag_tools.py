# @Author  : 木森
# @weixin: python771
import requests
from langchain.tools import tool


@tool('知识库检索工具', description='通过输入问题，从知识库检索详细的内容答案，比如查询某个功能详细的需求和api接口详情')
def lightrag_query(query):
    """
    :param query: 要查询的内容
    :return:
    """
    print(f"========开始从知识库检索内容:{query}=========")

    url = "http://localhost:9621/query"
    params = {
        "query": query,
        "mode": "global",
    }
    response = requests.post(url, json=params, stream=True)
    result = response.json()['response']
    print("==========知识库内容检索完成==========")
    return result
