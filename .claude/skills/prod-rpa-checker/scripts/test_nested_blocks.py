"""测试: convert → 转换 → 创建嵌套块"""

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
API = "https://open.feishu.cn/open-apis"

CONVERT_RESULT = Path(__file__).parent.parent / "doc" / "convert_api_result.json"


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


def load_convert_result():
    with open(CONVERT_RESULT, "r", encoding="utf-8") as f:
        return json.load(f)


def transform_blocks(data):
    """将 convert 返回的 blocks 转为创建嵌套块 API 要求的格式

    参考官方示例格式:
    {
        "index": 0,
        "children_id": [first_level_block_ids],
        "descendants": [所有块]  // 每个块必须有 block_id + children 字段
    }

    关键：convert API 和创建嵌套块 API 使用同一套 block_type 枚举，不需要转换。
    """
    blocks = data["blocks"]
    first_ids = data["first_level_block_ids"]

    descendants = []
    for block in blocks:
        # 确保每个块都有 children 字段，移除 parent_id
        descendant = {k: v for k, v in block.items() if k != "parent_id"}
        if "children" not in descendant:
            descendant["children"] = []
        descendants.append(descendant)

    return {
        "index": 0,
        "children_id": first_ids,
        "descendants": descendants,
    }


def create_blank_doc(token):
    resp = requests.post(
        f"{API}/docx/v1/documents",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
        json={"title": "测试_创建嵌套块_convert转换"},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        print(f"创建文档失败: {data}")
        return None, None
    doc_id = data["data"]["document"]["document_id"]

    # 获取 root_block_id
    resp2 = requests.get(
        f"{API}/docx/v1/documents/{doc_id}/blocks",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 1},
        timeout=10,
    )
    data2 = resp2.json()
    root_id = data2["data"]["items"][0]["block_id"]
    return doc_id, root_id


def create_nested_blocks(token, doc_id, root_id, payload):
    """调用创建嵌套块 API: POST /docx/v1/documents/{doc_id}/blocks/{block_id}/descendants"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    print(f"请求体大小: {len(json.dumps(payload, ensure_ascii=False))} 字符")
    print(f"descendants 数量: {len(payload['descendants'])}")

    resp = requests.post(
        f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/descendants",
        headers=headers,
        json=payload,
        timeout=120,
    )

    print(f"status={resp.status_code}")

    # 先打印原始响应文本
    raw_text = resp.text[:3000]
    print(f"response(前3000字符)={raw_text}")

    try:
        data = resp.json()
        print(f"code={data.get('code')}, msg={data.get('msg')}")
        return data
    except Exception:
        print(f"响应不是 JSON 格式")
        return None


if __name__ == "__main__":
    print("=== convert → 转换 → 创建嵌套块 API 测试 ===\n")

    # Step 1: 加载 convert 结果
    print("--- Step 1: 加载 convert_api_result.json ---")
    data = load_convert_result()
    print(f"加载成功: {len(data['blocks'])} blocks, {len(data['first_level_block_ids'])} first_level")

    # Step 2: 转换为嵌套结构
    print("\n--- Step 2: 转换为嵌套结构 ---")
    nested = transform_blocks(data)
    print(f"转换完成: {len(nested['descendants'])} 个 descendants")

    # 统计
    type_count = {}
    for c in nested["descendants"]:
        bt = c.get("block_type")
        type_count[bt] = type_count.get(bt, 0) + 1
    print(f"块类型分布: {type_count}")

    # Step 3: 保存请求体到文件（方便查看）
    output_file = Path(__file__).parent.parent / "doc" / "nested_blocks_request.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)
    print(f"请求体已保存到: {output_file}")

    # Step 4: 创建空白文档
    print("\n--- Step 3: 创建空白文档 ---")
    token = get_token()
    doc_id, root_id = create_blank_doc(token)
    if not doc_id:
        print("无法创建文档，退出")
        exit(1)
    print(f"document_id={doc_id}")
    print(f"root_block_id={root_id}")
    print(f"文档链接: https://wbenergy.feishu.cn/docx/{doc_id}")

    # Step 5: 调用创建嵌套块 API: POST /docx/v1/documents/{doc_id}/blocks/{block_id}/descendant
    # 注意: 请求体需要 children_id + descendants 格式
    print(f"\n--- Step 4: 调用创建嵌套块 API ---")

    # API 要求的格式: {"children_id": [root_block_id], "descendants": [...]}
    payload = {
        "children_id": [root_id],
        "descendants": nested["descendants"],
    }

    print(f"请求体大小: {len(json.dumps(payload, ensure_ascii=False))} 字符")
    print(f"descendants 数量: {len(payload['descendants'])}")

    url = f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/descendant"
    print(f"端点: {url}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    resp = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
    )

    print(f"status={resp.status_code}")
    raw_text = resp.text[:5000]
    print(f"response(前5000字符)={raw_text}")

    try:
        data = resp.json()
        print(f"code={data.get('code')}, msg={data.get('msg')}")
        if data.get("code") == 0:
            print(f"\n✅ 创建嵌套块成功!")
            print(f"请在飞书中查看文档: https://wbenergy.feishu.cn/docx/{doc_id}")
            print(f"请确认表格是否为原生表格、标题是否正确显示")
        else:
            print(f"\n❌ 创建嵌套块失败")
            print(f"错误详情: {json.dumps(data, ensure_ascii=False)[:2000]}")
    except Exception:
        print(f"\n❌ 响应不是 JSON 格式")
