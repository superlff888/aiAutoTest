"""验证飞书文档导入 API (docs:document:import) 是否支持 Markdown 原生解析"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
WIKI_SPACE_ID = "7316788734647599106"
PARENT_NODE_TOKEN = "APocwMagEigGtmkgLKVcHr2Dned"
FEISHU_DOMAIN = "wbenergy.feishu.cn"

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


def test_import_markdown(token: str) -> str | None:
    """通过 /drive/v1/files/import 导入 Markdown，验证飞书是否能原生解析。"""
    md = """# 测试标题

**加粗文本** 和 *斜体* 和 `行内代码`

| 列1 | 列2 |
|-----|-----|
| A | 1 |
| B | 2 |

- 列表项1
- 列表项2
"""
    # 方式1: multipart/form-data 上传
    resp = requests.post(
        f"{API}/drive/v1/files/import",
        headers={"Authorization": f"Bearer {token}"},
        files={
            "file": ("test.md", md.encode("utf-8"), "text/markdown"),
        },
        params={
            "file_name": "测试报告_Markdown导入验证",
            "type": "docx",
        },
        timeout=30,
    )
    print(f"\n[Import API] status={resp.status_code}")
    print(f"[Import API] response={resp.text[:500]}")

    data = resp.json()
    if data.get("code") == 0:
        file_token = data["data"]["file_token"]
        print(f"✅ 导入成功, file_token={file_token}")
        return file_token
    else:
        print(f"❌ 导入失败: {data}")
        return None


def verify_rendering(token: str, doc_id: str):
    """读取文档 blocks，验证 Markdown 是否被正确解析。"""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{API}/docx/v1/documents/{doc_id}/blocks",
        headers=headers,
        params={"page_size": 50},
        timeout=10,
    )
    data = resp.json()
    if data.get("code") != 0:
        print(f"❌ 获取 blocks 失败: {data}")
        return

    items = data["data"]["items"]
    print(f"\n[文档结构] 共 {len(items)} 个 block:")
    for b in items:
        bt = b.get("block_type")
        print(f"  block_type={bt}, data_keys={list(b.keys())}")
        # 如果是表格，打印行列信息
        if bt == 32 and "table" in b:
            prop = b["table"].get("property", {})
            print(f"    → 表格: {prop.get('row_size')}行 x {prop.get('column_size')}列")
        # 如果是标题，打印文本
        for key in ("heading1", "heading2", "heading3"):
            if key in b:
                texts = [e.get("text_run", {}).get("content", "") for e in b[key].get("elements", [])]
                print(f"    → 标题: {' '.join(texts)}")


def create_wiki_node_for_doc(token: str, file_token: str):
    """将已导入的文档挂载到 wiki 子节点。"""
    # 先通过 file_token 获取 obj_type
    resp = requests.get(
        f"{API}/drive/v1/files/{file_token}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    print(f"\n[File Info] {resp.text[:300]}")

    # 创建 wiki 子节点
    resp = requests.post(
        f"{API}/wiki/v2/spaces/{WIKI_SPACE_ID}/nodes",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "parent_node_token": PARENT_NODE_TOKEN,
            "node_type": "origin",
            "obj_type": "docx",
            "obj_token": file_token,
            "title": "测试报告_Markdown导入验证",
        },
        timeout=10,
    )
    data = resp.json()
    print(f"\n[Wiki Node] {resp.text[:500]}")

    if data.get("code") == 0:
        node_token = data["data"]["node"]["node_token"]
        url = f"https://{FEISHU_DOMAIN}/wiki/{node_token}"
        print(f"✅ Wiki 子节点创建成功: {url}")
    else:
        print("⚠️ Wiki 节点创建失败（可能文档已自动关联），尝试通过 doc_id 直接访问")


if __name__ == "__main__":
    print("=== 飞书 Markdown 导入 API 验证 ===")
    token = get_token()
    print("✅ Token 获取成功")

    file_token = test_import_markdown(token)
    if file_token:
        print("\n--- 验证 Markdown 解析结果 ---")
        verify_rendering(token, file_token)

        print("\n--- 尝试挂载到 Wiki ---")
        create_wiki_node_for_doc(token, file_token)
