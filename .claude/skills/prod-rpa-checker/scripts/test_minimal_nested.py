"""最小化测试: 创建嵌套块 API 能否正常工作"""

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
API = "https://open.feishu.cn/open-apis"


def get_token():
    resp = requests.post(
        f"{API}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def create_doc(token):
    resp = requests.post(
        f"{API}/docx/v1/documents",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        json={"title": "测试_最小嵌套块"},
        timeout=10,
    )
    data = resp.json()
    doc_id = data["data"]["document"]["document_id"]
    resp2 = requests.get(
        f"{API}/docx/v1/documents/{doc_id}/blocks",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 1},
        timeout=10,
    )
    data2 = resp2.json()
    root_id = data2["data"]["items"][0]["block_id"]
    return doc_id, root_id


def test_minimal(token, doc_id, root_id, payload, label):
    url = f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/descendant"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    print(f"\n--- {label} ---")
    print(f"payload: {json.dumps(payload, ensure_ascii=False)[:300]}")
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"status={resp.status_code}")
    try:
        data = resp.json()
        print(f"code={data.get('code')}, msg={data.get('msg')}")
        if data.get("code") == 0:
            print(f"✅ 成功! 文档: https://wbenergy.feishu.cn/docx/{doc_id}")
        else:
            print(f"❌ 失败: {json.dumps(data, ensure_ascii=False)[:500]}")
        return data.get("code") == 0
    except:
        print(f"❌ 非JSON响应: {resp.text[:200]}")
        return False


if __name__ == "__main__":
    token = get_token()
    print("Token OK")

    # Test 1: 简单文本块
    doc_id1, root_id1 = create_doc(token)
    test_minimal(token, doc_id1, root_id1,
                 {"children_id": [root_id1], "descendants": [
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "简单测试"}}]}}
                 ]},
                 "Test1: 单个文本块")

    # Test 2: 标题+文本
    doc_id2, root_id2 = create_doc(token)
    test_minimal(token, doc_id2, root_id2,
                 {"children_id": [root_id2], "descendants": [
                     {"block_type": 3, "heading1": {"elements": [{"text_run": {"content": "标题"}}]}},
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "正文"}}]}},
                 ]},
                 "Test2: 标题+文本")

    # Test 3: 无序列表
    doc_id3, root_id3 = create_doc(token)
    test_minimal(token, doc_id3, root_id3,
                 {"children_id": [root_id3], "descendants": [
                     {"block_type": 12, "bullet": {"elements": [{"text_run": {"content": "列表项"}}]}},
                 ]},
                 "Test3: 无序列表")

    # Test 4: divider
    doc_id4, root_id4 = create_doc(token)
    test_minimal(token, doc_id4, root_id4,
                 {"children_id": [root_id4], "descendants": [
                     {"block_type": 22, "divider": {}},
                 ]},
                 "Test4: 分隔线")

    # Test 5: 简单表格 (2x2)
    doc_id5, root_id5 = create_doc(token)
    test_minimal(token, doc_id5, root_id5,
                 {"children_id": [root_id5], "descendants": [
                     {"block_type": 41, "table": {
                         "cells": ["c1", "c2", "c3", "c4"],
                         "property": {"row_size": 2, "column_size": 2, "column_width": [200, 200], "merge_info": [
                             {"col_span": 1, "row_span": 1}
                         ] * 4}
                     }, "children": ["c1", "c2", "c3", "c4"]},
                     {"block_id": "c1", "block_type": 32, "table_cell": {}, "child_blocks": ["t1"]},
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "A"}}]}},
                     {"block_id": "c2", "block_type": 32, "table_cell": {}, "child_blocks": ["t2"]},
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "B"}}]}},
                     {"block_id": "c3", "block_type": 32, "table_cell": {}, "child_blocks": ["t3"]},
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "1"}}]}},
                     {"block_id": "c4", "block_type": 32, "table_cell": {}, "child_blocks": ["t4"]},
                     {"block_type": 2, "text": {"elements": [{"text_run": {"content": "2"}}]}},
                 ]},
                 "Test5: 简单表格")
