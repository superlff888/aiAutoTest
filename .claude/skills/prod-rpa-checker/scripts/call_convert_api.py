"""调用 convert API，将实际报告 Markdown 转换为飞书 blocks"""

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
API = "https://open.feishu.cn/open-apis"
REPORT_FILE = Path(__file__).parent.parent / "output" / "rpa_check_report_20260604181316.md"


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


def call_convert_api(token):
    """读取报告文件，调用 convert API"""
    with open(REPORT_FILE, "r", encoding="utf-8") as f:
        md_content = f.read()

    print(f"报告文件大小: {len(md_content)} 字符, {len(md_content.splitlines())} 行")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    resp = requests.post(
        f"{API}/docx/v1/documents/blocks/convert",
        headers=headers,
        json={
            "content": md_content,
            "content_type": "markdown",
        },
        timeout=30,
    )

    print(f"\nConvert API 状态码: {resp.status_code}")
    data = resp.json()
    print(f"code: {data.get('code')}")
    print(f"msg: {data.get('msg')}")

    if data.get("code") != 0:
        print(f"\n❌ Convert API 调用失败: {json.dumps(data, ensure_ascii=False)}")
        return None

    blocks = data["data"]["blocks"]
    first_ids = data["data"]["first_level_block_ids"]
    print(f"\n✅ Convert 成功!")
    print(f"返回 blocks 数量: {len(blocks)}")
    print(f"first_level_block_ids: {first_ids}")

    # 统计块类型分布
    type_count = {}
    for b in blocks:
        bt = b.get("block_type")
        type_count[bt] = type_count.get(bt, 0) + 1
    print(f"\n块类型分布: {type_count}")
    print("  block_type 说明: 2=文本, 3=H1, 4=H2, 5=H3, 12=无序列表, 13=有序列表, 31=表格(容器), 32=表格单元格")

    return data["data"]


if __name__ == "__main__":
    print("=== 调用 Convert API（实际报告内容）===\n")
    token = get_token()
    print("Token 获取成功")

    result = call_convert_api(token)

    if result:
        # 输出结果到 JSON 文件，方便后续分析
        output_file = Path(__file__).parent.parent / "doc" / "convert_api_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n响应已保存到: {output_file}")
