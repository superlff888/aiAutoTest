import os, json
from dotenv import load_dotenv
load_dotenv()
import requests

import sys
sys.path.insert(0, '.claude/skills/prod-rpa-checker/scripts')
from wiki_updater import (markdown_to_blocks, get_tenant_token,
                           get_wiki_document_id, FEISHU_OPEN_API)

report = '.claude/skills/prod-rpa-checker/output/rpa_check_report_20260604_105457.md'
with open(report, 'r', encoding='utf-8') as f:
    md = f.read()

blocks = markdown_to_blocks(md)
print(f"Total blocks: {len(blocks)}")

app_id = os.getenv('FEISHU_APP_ID')
app_secret = os.getenv('FEISHU_APP_SECRET')
tenant_token = get_tenant_token(app_id, app_secret)
doc_id = get_wiki_document_id('APocwMagEigGtmkgLKVcHr2Dned', tenant_token)

r = requests.get(
    f'{FEISHU_OPEN_API}/docx/v1/documents/{doc_id}/blocks',
    params={'page_size': 1},
    headers={'Authorization': f'Bearer {tenant_token}'},
    timeout=10
)
root_id = r.json()['data']['items'][0]['block_id']

hdrs = {
    'Authorization': f'Bearer {tenant_token}',
    'Content-Type': 'application/json',
}


def test_range(start, end):
    subset = blocks[start:end]
    r = requests.post(
        f'{FEISHU_OPEN_API}/docx/v1/documents/{doc_id}/blocks/{root_id}/children',
        json={'children': subset},
        headers=hdrs, timeout=30
    )
    d = r.json()
    return d.get('code') == 0, d


# Test all at once
ok, d = test_range(0, len(blocks))
if ok:
    print("All blocks succeed!")
else:
    print("All blocks failed, finding bad chunk...")
    for chunk_start in range(0, len(blocks), 10):
        chunk_end = min(chunk_start + 10, len(blocks))
        ok, d = test_range(chunk_start, chunk_end)
        if not ok:
            print(f"Bad chunk: blocks {chunk_start}-{chunk_end - 1}")
            for i in range(chunk_start, chunk_end):
                ok2, d2 = test_range(i, i + 1)
                if not ok2:
                    print(f"  Bad block #{i}: type={blocks[i].get('block_type')}, keys={list(blocks[i].keys())}")
                    print(f"  Content: {json.dumps(blocks[i], ensure_ascii=False)[:300]}")
                    print(f"  Error: {d2}")
