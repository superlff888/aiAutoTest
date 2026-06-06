"""飞书 Wiki 更新模块 — 使用 Convert API + 创建嵌套块 API 实现原生 Markdown 写入"""

import logging
import os
import re
import json
import requests
import time

logger = logging.getLogger(__name__)

FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"

def get_tenant_token(app_id: str, app_secret: str) -> str:
    resp = requests.post(
        f"{FEISHU_OPEN_API}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    return data["tenant_access_token"]

def call_convert_api(markdown_content: str, tenant_token: str) -> dict:
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    resp = requests.post(
        f"{FEISHU_OPEN_API}/docx/v1/documents/blocks/convert",
        headers=headers,
        json={"content": markdown_content, "content_type": "markdown"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Convert 失败: {data}")
    logger.info("Convert 成功，blocks: %d", len(data["data"]["blocks"]))
    return data["data"]

def prepare_batches(convert_data, batch_size=1000):
    """
    准备请求批次（按顶层块子树分组切分，保证引用完整性）：

    清理规则：
    1. 移除每个块的 parent_id（创建嵌套块 API 不需要）
    2. 移除 table.cells（创建嵌套块 API 不需要）
    3. 移除 table.property.merge_info（关键！API 不接受此字段）
    4. 确保每个块有 children 字段

    分批策略：
    5. 按 first_level_block_ids 构建子树，计算每个顶层块的子树大小
    6. 按子树大小累积到 batch_size 附近时切分（大块优先）
    7. 每个批次的 children_id = 该批次的顶层块 ID 列表
       descendants = 这些顶层块及其所有子块的完整集合
       保证 children_id 数量 == descendants 中顶层块数量
    8. 飞书 API 限制 descendants 最大 1000 个

    ~~历史失败策略~~：
    2026-06-06 验证：按 descendants 数组顺序切分（900/批），children_id 全量传入
    → code 1770041 open schema mismatch。不再尝试。
    """
    blocks = convert_data["blocks"]
    first_level_ids = convert_data["first_level_block_ids"]
    block_map = {b["block_id"]: b for b in blocks}

    # 清理每个块
    cleaned_map = {}
    for b in blocks:
        b_copy = {k: v for k, v in b.items() if k != "parent_id"}
        if "table" in b_copy:
            t = b_copy["table"]
            if isinstance(t, dict):
                t.pop("cells", None)
                if "property" in t:
                    t["property"].pop("merge_info", None)
                    b_copy["table"] = {"property": t["property"]}
                else:
                    b_copy["table"] = {}
        if "children" not in b_copy:
            b_copy["children"] = []
        cleaned_map[b["block_id"]] = b_copy

    # 计算子树大小
    def subtree_size(block_id):
        block = cleaned_map.get(block_id)
        if not block:
            return 0
        size = 1
        for cid in block.get("children", []):
            size += subtree_size(cid)
        return size

    # 收集子树所有块 ID（深度优先，保持原始顺序）
    def collect_subtree_ids(block_id):
        block = cleaned_map.get(block_id)
        if not block:
            return []
        ids = [block_id]
        for cid in block.get("children", []):
            ids.extend(collect_subtree_ids(cid))
        return ids

    # 计算子树大小，保持原始顺序（排序会导致文档渲染顺序错乱）
    trees = []
    for fid in first_level_ids:
        s = subtree_size(fid)
        trees.append((fid, s))
    # 注意：不再按子树大小排序！保持 convert API 返回的原始顺序

    # 按子树分组切分
    batches = []
    current_descendants = []
    current_children = []
    current_size = 0

    for fid, size in trees:
        if current_size + size > batch_size and current_descendants:
            batches.append({
                "index": 0,
                "children_id": current_children,
                "descendants": current_descendants,
            })
            current_descendants = []
            current_children = []
            current_size = 0

        ids = collect_subtree_ids(fid)
        for bid in ids:
            current_descendants.append(cleaned_map[bid])
        current_children.append(fid)
        current_size += size

    if current_descendants:
        batches.append({
            "index": 0,
            "children_id": current_children,
            "descendants": current_descendants,
        })

    logger.info("准备完成，共 %d 个批次 (batch_size=%d)", len(batches), batch_size)
    for i, b in enumerate(batches):
        logger.info("  批次 %d: %d children, %d descendants",
                     i + 1, len(b["children_id"]), len(b["descendants"]))

    # ====== 批次验证（异常场景校验，不修改任何数据） ======
    for i, b in enumerate(batches):
        batch_ids = {d["block_id"] for d in b["descendants"]}
        # 1. block_id 唯一性
        all_bid = [d["block_id"] for d in b["descendants"]]
        dupes = [x for x in all_bid if all_bid.count(x) > 1]
        assert not dupes, f"批次 {i+1} 存在重复 block_id: {set(dupes)}"

        # 2. children 引用完整性
        orphan_refs = 0
        for d in b["descendants"]:
            for cid in d.get("children", []):
                if cid not in batch_ids:
                    orphan_refs += 1
        assert orphan_refs == 0, f"批次 {i+1} 有 {orphan_refs} 个 children 引用不在本批 descendants 中"

        # 3. descendants 数量 ≤ 1000
        assert len(b["descendants"]) <= 1000, f"批次 {i+1} 超出 API 上限: {len(b['descendants'])}"

    logger.info("批次验证通过: block_id 唯一、children 引用完整、数量 ≤ 1000")
    return batches

def write_content_via_descendant(document_id, root_block_id, batches, tenant_token):
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    url = f"{FEISHU_OPEN_API}/docx/v1/documents/{document_id}/blocks/{root_block_id}/descendant"

    for i, batch_payload in enumerate(batches):
        try:
            logger.info("发送批次 %d/%d (%d blocks)", i + 1, len(batches), len(batch_payload["descendants"]))
            resp = requests.post(url, headers=headers, json=batch_payload, timeout=120)
            resp.raise_for_status()
            res_data = resp.json()
            if res_data.get("code") != 0:
                logger.error("写入失败: %s", res_data)
                return False
            logger.info("批次成功")
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP 错误: %s, Body: %s", e, resp.text[:500])
            return False
        except Exception as e:
            logger.error("异常: %s", e)
            return False
        time.sleep(1) # 避免限流

    return True

def create_wiki_child_node(space_id, parent_node_token, title, tenant_token):
    headers = {"Authorization": f"Bearer {tenant_token}", "Content-Type": "application/json; charset=utf-8"}
    resp = requests.post(f"{FEISHU_OPEN_API}/wiki/v2/spaces/{space_id}/nodes",
        json={"parent_node_token": parent_node_token, "node_type": "origin", "obj_type": "docx", "title": title},
        headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]["node"]["node_token"]

def _get_wiki_node_obj_token(node_token, tenant_token):
    resp = requests.get(f"{FEISHU_OPEN_API}/wiki/v2/spaces/get_node", params={"token": node_token},
        headers={"Authorization": f"Bearer {tenant_token}"}, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"]["node"].get("obj_token")

def _get_root_block_id(document_id, tenant_token):
    headers = {"Authorization": f"Bearer {tenant_token}"}
    resp = requests.get(f"{FEISHU_OPEN_API}/docx/v1/documents/{document_id}/blocks",
        headers=headers, params={"page_size": 1}, timeout=10)
    try:
        resp.raise_for_status()
        return resp.json()["data"]["items"][0]["block_id"]
    except Exception:
        return document_id

def _get_wiki_node_info(node_token: str, tenant_token: str) -> dict | None:
    """获取 Wiki 节点完整信息（包含 obj_token、obj_type 等）。"""
    resp = requests.get(
        f"{FEISHU_OPEN_API}/wiki/v2/spaces/get_node",
        params={"token": node_token},
        headers={"Authorization": f"Bearer {tenant_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["data"]["node"]


def _get_drive_file_token(obj_token: str, obj_type: str, tenant_token: str) -> str | None:
    """通过文档 obj_token 获取 drive_file_token（用于删除操作）。"""
    resp = requests.get(
        f"{FEISHU_OPEN_API}/drive/v1/files",
        params={"type": obj_type, "token": obj_token},
        headers={"Authorization": f"Bearer {tenant_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") == 0:
        # API 返回的文件对象在不同版本中字段名可能不同，尝试多种可能
        file_obj = data.get("data", {}).get("file", data.get("data", {}))
        file_token = file_obj.get("file_token") or file_obj.get("token")
        if file_token:
            return file_token
        logger.warning("无法解析 drive_file_token, response: %s", json.dumps(data, ensure_ascii=False)[:200])
    return None


def delete_old_document(obj_token: str, tenant_token: str, space_id: str = None) -> bool:
    """通过 Wiki API 删除旧的知识库节点文档。

    注意：必须使用 obj_token（文档对象 token），而非 node_token（URL 短 token）。
    API: DELETE /wiki/v2/spaces/{space_id}/nodes/{obj_token}
    Body: {"obj_type": "docx"}
    """
    if not space_id:
        logger.warning("删除旧文档失败: 缺少 space_id")
        return False

    try:
        resp = requests.delete(
            f"{FEISHU_OPEN_API}/wiki/v2/spaces/{space_id}/nodes/{obj_token}",
            headers={"Authorization": f"Bearer {tenant_token}", "Content-Type": "application/json; charset=utf-8"},
            json={"obj_type": "docx"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            logger.warning("删除旧文档失败 (obj_token=%s): %s", obj_token, data)
            return False
        logger.info("旧文档已删除 (obj_token=%s)", obj_token)
        return True
    except Exception as e:
        logger.warning("删除旧文档异常 (obj_token=%s): %s", obj_token, e)
        return False


FEISHU_DOMAIN = os.getenv("FEISHU_DOMAIN", "wbenergy.feishu.cn")


def update_wiki_content(report_file, tenant_token, space_id, parent_node_token, report_history=None):
    with open(report_file, "r", encoding="utf-8") as f:
        md_content = f.read()
    date_match = re.search(r"(\d{14})", report_file)
    title = f"RPA数据采集校验报告{date_match.group(1)}" if date_match else "RPA数据采集校验报告"

    new_node_token = create_wiki_child_node(space_id, parent_node_token, title, tenant_token)
    actual_doc_id = _get_wiki_node_obj_token(new_node_token, tenant_token)
    if not actual_doc_id:
        return None, None, None

    root_block_id = _get_root_block_id(actual_doc_id, tenant_token)

    try:
        convert_data = call_convert_api(md_content, tenant_token)
        batches = prepare_batches(convert_data)
        if not write_content_via_descendant(actual_doc_id, root_block_id, batches, tenant_token):
            return None, actual_doc_id, title
    except Exception as e:
        logger.exception("异常: %s", e)
        return None, actual_doc_id, title

    wiki_url = f"https://{FEISHU_DOMAIN}/wiki/{new_node_token}"
    return wiki_url, actual_doc_id, title
