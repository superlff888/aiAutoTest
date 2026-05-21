# @Author  : 木森
# @weixin: python771

"""
lightrag 提供了详细的接入api,如果要接入知识库，只需要通过调用api即可实现知识库的内容检索
"""
import json

import requests


def lightrag_query(query):
    """接入lightrag系统的方式"""
    url = "http://localhost:9621/query"
    params = {
        "query": query,
        "mode": "global",
    }
    response = requests.post(url, json=params, stream=True)
    print(response.json()['response'])


def lightrag_query_stream(query):
    """接入lightrag系统的方式"""

    url = "http://localhost:9621/query/stream"
    params = {
        "query": query,
        "mode": "global",
        "stream": True
    }
    response = requests.post(url, json=params, stream=True)

    for chunk in response.iter_lines():
        if chunk:
            print(json.loads(chunk)['response'])


if __name__ == '__main__':
    lightrag_query("订单列表分页查询 的详细要求和接口是什么")
