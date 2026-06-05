import io, sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os, json, requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
API = "https://open.feishu.cn/open-apis"

token_resp = requests.post(f"{API}/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10).json()
print(f"Token resp: {token_resp}")
token = token_resp.get("tenant_access_token") or token_resp.get("token")
if not token:
    raise RuntimeError(f"获取 token 失败: {token_resp}")

# Create doc
resp = requests.post(f"{API}/docx/v1/documents",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
    json={"title": "min_test"}, timeout=10)
doc_id = resp.json()["data"]["document"]["document_id"]

resp2 = requests.get(f"{API}/docx/v1/documents/{doc_id}/blocks",
    headers={"Authorization": f"Bearer {token}"}, params={"page_size": 1}, timeout=10)
root_id = resp2.json()["data"]["items"][0]["block_id"]

url = f"{API}/docx/v1/documents/{doc_id}/blocks/{root_id}/descendant"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}

# Test with exact official example format
payload = {
    "index": 0,
    "children_id": ["headingid_1"],
    "descendants": [
        {
            "block_id": "headingid_1",
            "block_type": 3,
            "heading1": {"elements": [{"text_run": {"content": "测试"}}]},
            "children": []
        }
    ]
}
print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
r = requests.post(url, headers=headers, json=payload, timeout=30)
print(f"status={r.status_code}")
print(f"resp={r.text[:500]}")
