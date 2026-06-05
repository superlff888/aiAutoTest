"""测试：批量创建块能否使用 convert 返回的 block_id"""

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
    """获取 tenant_access_token"""
    resp = requests.post(
        f"{API}/auth/v3/tenant_access_token/internal",
        json={"app_id": APP_ID, "app_secret": APP_SECRET},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def step1_create_blank_doc(token):
    """创建空白文档，获取 document_id 和 root_block_id"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    resp = requests.post(
        f"{API}/docx/v1/documents",
        headers=headers,
        json={"title": "测试_批量创建块"},
        timeout=10,
    )
    data = resp.json()
    print(f"=== Step 1: 创建空白文档 ===")
    print(f"status={resp.status_code}, resp={json.dumps(data, ensure_ascii=False)[:300]}")
    if data.get("code") != 0:
        print("创建文档失败，退出")
        return None, None
    doc_id = data["data"]["document"]["document_id"]
    print(f"document_id = {doc_id}")

    # 获取 root_block_id
    resp2 = requests.get(
        f"{API}/docx/v1/documents/{doc_id}/blocks",
        headers=headers,
        params={"page_size": 1},
        timeout=10,
    )
    data2 = resp2.json()
    if data2.get("code") != 0:
        print(f"获取文档块失败: {data2}")
        return doc_id, None
    root_id = data2["data"]["items"][0]["block_id"]
    print(f"root_block_id = {root_id}")
    return doc_id, root_id


def step2_convert(token):
    """调用 convert API 获取 blocks"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    md_content = """# 测试标题

**加粗** 和 *斜体*

| 列1 | 列2 |
|-----|-----|
| A | 1 |

- 列表1"""

    resp = requests.post(
        f"{API}/docx/v1/documents/blocks/convert",
        headers=headers,
        json={
            "content": md_content,
            "content_type": "markdown",
        },
        timeout=10,
    )
    data = resp.json()
    print(f"\n=== Step 2: Convert API ===")
    print(f"status={resp.status_code}, code={data.get('code')}")
    if data.get("code") != 0:
        print(f"Convert 失败: {data}")
        return None, None
    blocks = data["data"]["blocks"]
    first_ids = data["data"]["first_level_block_ids"]
    print(f"返回 {len(blocks)} 个 blocks, {len(first_ids)} 个 first_level_block_ids")
    print(f"first_level_block_ids = {first_ids}")
    return blocks, first_ids


def step3_create_blocks(token, doc_id, root_id, blocks, first_ids):
    """
    尝试1：直接将 convert 返回的 blocks 传给批量创建块 API
    （不修改任何字段，原封不动）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    # 构建请求体：包含所有 blocks
    # 批量创建块 API 的 children 参数是一个 blocks 数组
    payload = {"children": blocks}

    print(f"\n=== Step 3: 批量创建块（尝试1：直接使用 convert blocks）===")
    print(f"请求体大小: {len(json.dumps(payload, ensure_ascii=False))} 字符")
    print(f"children 数量: {len(blocks)}")

    resp = requests.post(
        f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/children",
        headers=headers,
        json=payload,
        timeout=60,
    )
    data = resp.json()
    print(f"status={resp.status_code}")
    print(f"response={json.dumps(data, ensure_ascii=False)[:2000]}")

    if data.get("code") == 0:
        print("\n尝试1 成功！")
        return True
    else:
        print(f"\n尝试1 失败: {data.get('msg', '')}")
        return False


def step3_create_blocks_tree(token, doc_id, root_id, blocks, first_ids):
    """
    尝试2：按 first_level_block_ids 顺序，分批创建
    （将 blocks 按 first_level 顺序排列后传入）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    print(f"\n=== Step 3: 批量创建块（尝试2：按 first_level 排序后创建）===")

    # 按 first_level_block_ids 顺序排列 blocks
    block_map = {b["block_id"]: b for b in blocks}
    ordered = [block_map[bid] for bid in first_ids if bid in block_map]
    payload = {"children": ordered}

    print(f"children 数量: {len(ordered)}")

    resp = requests.post(
        f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/children",
        headers=headers,
        json=payload,
        timeout=60,
    )
    data = resp.json()
    print(f"status={resp.status_code}")
    print(f"response={json.dumps(data, ensure_ascii=False)[:2000]}")

    if data.get("code") == 0:
        print("\n尝试2 成功！")
        return True
    else:
        print(f"\n尝试2 失败: {data.get('msg', '')}")
        return False


def step3_create_one_by_one(token, doc_id, root_id, blocks, first_ids):
    """
    尝试3：逐个创建 first_level 块（每个块单独调用 API）
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    print(f"\n=== Step 3: 批量创建块（尝试3：逐个创建 first_level 块）===")

    block_map = {b["block_id"]: b for b in blocks}
    for i, bid in enumerate(first_ids):
        block = block_map[bid]
        # 每次只创建一个块
        payload = {"children": [block]}
        print(f"  创建块 {i+1}/{len(first_ids)}: type={block['block_type']}, id={bid}")

        resp = requests.post(
            f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/children",
            headers=headers,
            json=payload,
            timeout=30,
        )
        data = resp.json()
        if data.get("code") == 0:
            print(f"    成功")
        else:
            print(f"    失败: {data.get('msg', '')} - {json.dumps(data, ensure_ascii=False)[:200]}")
            # 表格（type 31）可能因为子块不存在而失败，打印详情
            if block["block_type"] == 31:
                print(f"    表格块，children 引用: {block.get('children', [])}")

    return True


if __name__ == "__main__":
    print("=== 飞书批量创建块 API 测试 ===\n")
    token = get_token()
    print("Token 获取成功\n")

    # Step 1: 创建空白文档
    doc_id, root_id = step1_create_blank_doc(token)
    if not doc_id or not root_id:
        print("无法获取 document_id 或 root_block_id，退出")
        exit(1)

    # Step 2: Convert API
    blocks, first_ids = step2_convert(token)
    if not blocks:
        print("Convert 失败，退出")
        exit(1)

    print(f"\n=== 文档信息 ===")
    print(f"document_id  = {doc_id}")
    print(f"root_block_id = {root_id}")
    print(f"请在飞书中打开文档查看结果: https://wbenergy.feishu.cn/docx/{doc_id}")

    # Step 3: 测试不同方式
    # 每次测试用新文档，避免互相干扰
    print(f"\n--- 尝试1：直接使用 convert 返回的所有 blocks ---")
    step3_create_blocks(token, doc_id, root_id, blocks, first_ids)

    print(f"\n--- 尝试2：按 first_level 排序后创建 ---")
    # 创建新文档用于尝试2
    doc_id2, root_id2 = step1_create_blank_doc(token)
    step3_create_blocks_tree(token, doc_id2, root_id2, blocks, first_ids)

    step3_create_blocks_tree(token, doc_id2, root_id2, blocks, first_ids)

    print(f"\n--- 尝试3：逐个创建 first_level 块 ---")
    # 创建新文档用于尝试3
    doc_id3, root_id3 = step1_create_blank_doc(token)
    step3_create_one_by_one(token, doc_id3, root_id3, blocks, first_ids)

    print(f"\n=== 测试完成 ===")
    print(f"请在飞书中查看以下文档:")
    print(f"  尝试1: https://wbenergy.feishu.cn/docx/{doc_id}")
    print(f"  尝试2: https://wbenergy.feishu.cn/docx/{doc_id2}")
    print(f"  尝试3: https://wbenergy.feishu.cn/docx/{doc_id3}")
