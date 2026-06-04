"""飞书 Wiki 更新模块 — 校验完成后创建新文档并挂载到父 wiki 节点下

流程：创建新文档 → 写入报告 → 创建 wiki 子节点 → 删除旧文档（可选）
"""

import logging
import os
import re
import time
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

FEISHU_OPEN_API = "https://open.feishu.cn/open-apis"

# 飞书 docx block_type 枚举
BT_TEXT = 2
BT_HEADING1 = 3
BT_HEADING2 = 4
BT_HEADING3 = 5
BT_HEADING4 = 6
BT_HEADING5 = 7
BT_HEADING6 = 8
BT_BULLET = 12

BATCH_SIZE = 40  # API 限制每次最多 50 个块


# ---------------------------------------------------------------------------
# 认证：获取 tenant_access_token
# ---------------------------------------------------------------------------

def get_tenant_token(app_id: str, app_secret: str) -> str:
    """获取 tenant_access_token（自建应用）。"""
    resp = requests.post(
        f"{FEISHU_OPEN_API}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 tenant_access_token 失败: {data}")
    return data["tenant_access_token"]


# ---------------------------------------------------------------------------
# Markdown → 飞书文档块
# ---------------------------------------------------------------------------

HEADING_MAP = {
    1: (BT_HEADING1, "heading1"),
    2: (BT_HEADING2, "heading2"),
    3: (BT_HEADING3, "heading3"),
    4: (BT_HEADING4, "heading4"),
    5: (BT_HEADING5, "heading5"),
    6: (BT_HEADING6, "heading6"),
}


def _text_element(content: str) -> dict:
    return {"text_run": {"content": content}}


def _heading_block(level: int, text: str) -> dict:
    bt, key = HEADING_MAP[level]
    return {"block_type": bt, key: {"elements": [_text_element(text)]}}


def _bullet_block(text: str) -> dict:
    return {"block_type": BT_BULLET, "bullet": {"elements": [_text_element(text)]}}


def _is_table_separator(line: str) -> bool:
    stripped = line.strip().strip("|").strip()
    return all(c in "-: " for c in stripped) and "-" in stripped


def _table_as_text(table_lines: list[str]) -> str:
    """将 Markdown 表格转为格式化文本（飞书 API 创建表格需嵌套块，暂不支持）"""
    data_rows = []
    for tl in table_lines:
        if not _is_table_separator(tl):
            cells = [c.strip() for c in tl.strip("|").split("|")]
            data_rows.append(cells)
    if not data_rows:
        return ""

    col_count = max(len(r) for r in data_rows)
    col_widths = [0] * col_count
    for r in data_rows:
        for j, c in enumerate(r):
            col_widths[j] = max(col_widths[j], len(c))

    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in col_widths) + " |"
    lines = []
    for i, r in enumerate(data_rows):
        while len(r) < col_count:
            r.append("")
        lines.append(fmt.format(*r))
        if i == 0:
            sep = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
            lines.append(sep)
    return "\n".join(lines)


def markdown_to_blocks(md_content: str) -> list[dict]:
    """将 Markdown 内容转换为飞书 docx blocks。"""
    blocks = []
    lines = md_content.splitlines()
    current_paragraph: list[str] = []

    def flush_paragraph():
        if current_paragraph:
            text = "\n".join(current_paragraph).strip()
            if text:
                blocks.append({
                    "block_type": BT_TEXT,
                    "text": {"elements": [_text_element(text)]},
                })
            current_paragraph.clear()

    i = 0
    while i < len(lines):
        line = lines[i]

        # 标题
        heading_match = None
        for level in range(1, 7):
            prefix = "#" * level + " "
            if line.startswith(prefix):
                heading_match = (level, line[len(prefix):])
                break
        if heading_match:
            flush_paragraph()
            blocks.append(_heading_block(heading_match[0], heading_match[1]))

        # 无序列表
        elif line.startswith("- ") or line.startswith("* "):
            flush_paragraph()
            blocks.append(_bullet_block(line[2:].strip()))

        # 表格（转为格式化文本块）
        elif line.startswith("|") and line.endswith("|") and not _is_table_separator(line):
            flush_paragraph()
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].startswith("|") and lines[i].endswith("|"):
                table_lines.append(lines[i])
                i += 1
            formatted = _table_as_text(table_lines)
            if formatted:
                blocks.append({
                    "block_type": BT_TEXT,
                    "text": {"elements": [_text_element(formatted)]},
                })
            continue

        # 分隔线
        elif line.strip() in ("---", "***", "___"):
            flush_paragraph()

        # 空行
        elif line.strip() == "":
            flush_paragraph()

        # 普通文本
        else:
            current_paragraph.append(line)

        i += 1

    flush_paragraph()
    return blocks


# ---------------------------------------------------------------------------
# 步骤 1：创建新文档
# ---------------------------------------------------------------------------

def create_document(title: str, tenant_token: str) -> str:
    """
    创建飞书云文档。

    :param title: 文档标题
    :param tenant_token: tenant_access_token
    :return: document_id
    """
    resp = requests.post(
        f"{FEISHU_OPEN_API}/docx/v1/documents",
        json={"title": title},
        headers={
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"创建文档失败: {data}")
    doc_id = data["data"]["document"]["document_id"]
    logger.info("创建新文档成功: %s", doc_id)
    return doc_id


# ---------------------------------------------------------------------------
# 步骤 2：写入内容
# ---------------------------------------------------------------------------

def write_content(document_id: str, blocks: list[dict], tenant_token: str,
                  max_retries: int = 3) -> bool:
    """
    将 blocks 写入飞书文档。分批写入，每批最多 BATCH_SIZE 个块。
    """
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }

    # 获取根块 ID
    resp = requests.get(
        f"{FEISHU_OPEN_API}/docx/v1/documents/{document_id}/blocks",
        params={"page_size": 1},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取文档块失败: {data}")

    root_block_id = data["data"]["items"][0]["block_id"]

    # 分批写入
    for batch_start in range(0, len(blocks), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(blocks))
        batch = blocks[batch_start:batch_end]
        batch_ok = False

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    f"{FEISHU_OPEN_API}/docx/v1/documents/{document_id}"
                    f"/blocks/{root_block_id}/children",
                    json={"children": batch},
                    headers=headers,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("code") == 0:
                    logger.info("文档写入块 %d-%d/%d 成功", batch_start, batch_end, len(blocks))
                    batch_ok = True
                    break
                else:
                    logger.warning("文档写入失败 (尝试 %d/%d): %s", attempt, max_retries, data)
            except requests.RequestException as e:
                logger.warning("文档写入请求异常 (尝试 %d/%d): %s", attempt, max_retries, e)

            if attempt < max_retries:
                time.sleep(2 ** attempt)

        if not batch_ok:
            logger.error("文档写入失败，块 %d-%d", batch_start, batch_end)
            return False

    logger.info("文档内容写入完成，共 %d 个 block", len(blocks))
    return True


# ---------------------------------------------------------------------------
# 步骤 3：创建 wiki 子节点
# ---------------------------------------------------------------------------

def create_wiki_child_node(
    space_id: str,
    parent_node_token: str,
    title: str,
    tenant_token: str,
) -> str:
    """
    在指定父 wiki 节点下创建子节点。
    飞书会自动生成一个新的 docx 文档。

    :param space_id: wiki 空间 ID
    :param parent_node_token: 父节点 token
    :param title: 节点标题
    :param tenant_token: tenant_access_token
    :return: new_node_token
    """
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json",
    }

    resp = requests.post(
        f"{FEISHU_OPEN_API}/wiki/v2/spaces/{space_id}/nodes",
        json={
            "parent_node_token": parent_node_token,
            "node_type": "origin",
            "obj_type": "docx",
            "title": title,
        },
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"创建 wiki 子节点失败: {data}")

    new_node_token = data["data"]["node"]["node_token"]
    logger.info("wiki 子节点创建成功: %s", new_node_token)
    return new_node_token


def _get_wiki_node_obj_token(node_token: str, tenant_token: str) -> str | None:
    """
    通过 wiki 节点 token 获取底层文档 ID（obj_token）。
    """
    resp = requests.get(
        f"{FEISHU_OPEN_API}/wiki/v2/spaces/get_node",
        params={"token": node_token},
        headers={"Authorization": f"Bearer {tenant_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        return None
    return data["data"]["node"].get("obj_token")


def _update_document_title(document_id: str, title: str, tenant_token: str) -> None:
    """
    更新飞书文档标题。
    API: PATCH /docx/v1/documents/{document_id}
    """
    resp = requests.patch(
        f"{FEISHU_OPEN_API}/docx/v1/documents/{document_id}",
        json={"title": title},
        headers={
            "Authorization": f"Bearer {tenant_token}",
            "Content-Type": "application/json",
        },
        timeout=10,
    )
    try:
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") == 0:
            logger.info("文档标题已更新: %s", title)
        else:
            logger.warning("文档标题更新失败: %s", data)
    except Exception:
        logger.warning("文档标题更新请求异常: %s", resp.text[:200])
# ---------------------------------------------------------------------------

def delete_old_document(document_id: str, tenant_token: str) -> bool:
    """
    将文档移入回收站（软删除）。

    API: DELETE /drive/v1/files/{file_token}?type=docx
    需要 drive:drive 或 space:document:delete 权限。
    失败时不阻断流程，仅记录日志。
    """
    if not document_id:
        return False

    resp = requests.delete(
        f"{FEISHU_OPEN_API}/drive/v1/files/{document_id}",
        params={"type": "docx"},
        headers={"Authorization": f"Bearer {tenant_token}"},
        timeout=10,
    )

    # 处理非 JSON 响应
    content_type = resp.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        logger.warning(
            "删除旧文档 API 不可用 (status=%d)。"
            "需要开通 drive:drive 权限才能自动清理旧文档。",
            resp.status_code,
        )
        return False

    data = resp.json()
    if data.get("code") == 0:
        logger.info("旧文档已移入回收站: %s", document_id)
        return True
    else:
        logger.warning("旧文档删除失败: %s", data)
        return False


# ---------------------------------------------------------------------------
# 主流程：更新 wiki 内容
# ---------------------------------------------------------------------------

def update_wiki_content(
    report_file: str,
    tenant_token: str,
    space_id: str,
    parent_node_token: str,
    max_retries: int = 3,
) -> tuple[str | None, str | None, str | None]:
    """
    将 Markdown 报告更新到飞书 wiki 页面（作为父节点的子页面）。

    流程：创建 wiki 子节点 → 获取自动生成的 doc_id → 写入内容 → 更新标题

    :param report_file: 本地 .md 报告文件路径
    :param tenant_token: tenant_access_token
    :param space_id: wiki 空间 ID
    :param parent_node_token: 父 wiki 节点 token
    :param max_retries: 最大重试次数
    :return: (新 wiki URL, 新文档 ID, 文档标题)，失败时返回 (None, None, None)
    """
    # 0. 读取报告
    with open(report_file, "r", encoding="utf-8") as f:
        md_content = f.read()

    # 提取日期时间作为标题（支持 20260604180111 格式）
    date_match = re.search(r"(\d{14})", report_file)
    if date_match:
        title = f"RPA数据采集校验报告{date_match.group(1)}"
    else:
        title = "RPA数据采集校验报告"

    # 1. 转换为 blocks
    blocks = markdown_to_blocks(md_content)
    logger.info("Markdown 转换完成, %d blocks", len(blocks))

    # 2. 创建 wiki 子节点（飞书自动生成新文档）
    new_node_token = create_wiki_child_node(
        space_id, parent_node_token, title, tenant_token
    )

    # 3. 获取 wiki 节点自动生成的文档 ID
    actual_doc_id = _get_wiki_node_obj_token(new_node_token, tenant_token)
    if not actual_doc_id:
        logger.error("无法获取 wiki 节点对应的文档 ID")
        return None, None, None

    logger.info("wiki 子节点: %s → doc_id: %s", new_node_token, actual_doc_id)

    # 4. 写入内容到实际文档
    if not write_content(actual_doc_id, blocks, tenant_token, max_retries):
        logger.error("文档内容写入失败")
        return None, actual_doc_id, title

    # 5. 更新文档标题（wiki 创建的文档标题默认为空，需要手动设置）
    _update_document_title(actual_doc_id, title, tenant_token)

    # 飞书域名前缀（可从环境变量 FEISHU_DOMAIN 覆盖，默认 wbenergy）
    feishu_domain = os.getenv("FEISHU_DOMAIN", "wbenergy.feishu.cn")
    new_wiki_url = f"https://{feishu_domain}/wiki/{new_node_token}"

    logger.info("wiki 内容更新完成: %s", new_wiki_url)
    return new_wiki_url, actual_doc_id, title
