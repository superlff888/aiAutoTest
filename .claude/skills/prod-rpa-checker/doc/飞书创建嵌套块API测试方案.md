# 飞书"创建嵌套块" API 测试方案

> 编写日期：2026-06-05
> 更新日期：2026-06-06
> 目的：验证通过 convert API + 创建嵌套块 API，能否将 Markdown 报告以原生格式（含表格、粗体等）写入飞书文档

### 0. 前置条件

运行前确保以下配置已就绪：

| 配置 | 位置 | 说明 |
|---|---|---|
| `FEISHU_APP_ID` | `.env` | 飞书开放平台应用 ID |
| `FEISHU_APP_SECRET` | `.env` | 飞书开放平台应用 Secret |
| `FEISHU_DOMAIN` | `.env` | 飞书租户域名（默认 `wbenergy.feishu.cn`） |
| `wiki_space_id` | `config.yaml` → `feishu` | 知识库空间 ID |
| `wiki_parent_node_token` | `config.yaml` → `feishu` | 父 wiki 节点 token（报告挂载位置） |

应用需开通权限：`docx:document`、`wiki:wiki`

---

## Part A: API 规格

### 1. 端点信息

| 项 | 值 |
|---|---|
| **端点路径** | `POST /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/descendant` |
| **功能** | 一次性创建所有块（含表格、标题、文本、列表等），飞书服务端自动渲染 |
| **Table 的 block_type** | **31**（与 convert API 一致，无需转换） |
| **TableCell 的 block_type** | **32** |

### 2. 请求体格式

```json
{
  "index": 0,
  "children_id": ["first_level_block_id_1", "first_level_block_id_2", ...],
  "descendants": [
    {
      "block_id": "...",
      "block_type": 31,
      "table": {
        "property": {
          "row_size": 11,
          "column_size": 4,
          "column_width": [183, 183, 183, 183]
        }
      },
      "children": ["cell_id_1", "cell_id_2", ...]
    },
    {
      "block_id": "cell_id_1",
      "block_type": 32,
      "table_cell": {},
      "children": ["text_id_1"]
    },
    {
      "block_id": "text_id_1",
      "block_type": 2,
      "text": {
        "elements": [{"text_run": {"content": "内容", "text_element_style": {}}}],
        "style": {"align": 1, "folded": false}
      },
      "children": []
    }
  ]
}
```

**字段说明**：
- `index`: 固定为 0
- `children_id`: **必填**。对应 convert API 返回的 `first_level_block_ids`（顶层块的 ID 列表）
- `descendants`: **必填**。包含所有块（1000 个），每个块原样复制 convert API 返回的数据

#### 关键规则（踩坑总结）

1. **Table 块**：
   - **删除 `table.cells`**：创建嵌套块 API 不需要。
   - **删除 `table.property.merge_info`**：convert API 会返回此字段，但**创建嵌套块 API 不接受**，传入会报 `invalid param`。
2. **Table Cell 块**：
   - 必须作为独立元素出现在 `descendants` 中。
   - `table_cell` 是块的内容字段（值为 `{}`）。
   - `children` 字段指向单元格内的文本块 ID。
3. **引用完整性**：
   - 所有 `children` 数组引用的 ID，都必须在 `descendants` 中存在。
   - 所有 `block_id` 必须唯一。
   - **`children_id` 中的每个 ID，都必须在 `descendants` 中有对应的块。**
   - `descendants` 数量 ≤ 1000（飞书 API 硬性限制，超限报 code 99992402）。
   - `children_id` 数量必须与 `descendants` 中顶层块数量一致（不一致报 code 1770041 open schema mismatch）。
4. **分批策略**（blocks > 1000 时）：
   - ~~❌ 失败策略（2026-06-06）~~：按 descendants 数组顺序切分（900/批），`children_id` 全量传入 → code 1770041 open schema mismatch。**此策略已验证不可用，不再尝试。**
   - ✅ **正确策略**：按顶层块子树分组切分。每个批次包含完整的若干顶层块及其所有子块，`children_id` = 该批次的顶层块 ID 列表。
5. **通用清理**：
   - **删除 `parent_id`**：convert API 返回的块包含此字段，但创建嵌套块 API 不需要。
   - **确保 `children` 字段存在**：每个块必须有 `children` 字段（空数组 `[]` 也可），convert 没有就手动补上。

### 3. 请求头

```
Authorization: Bearer {tenant_access_token}
Content-Type: application/json; charset=utf-8
```

### 4. 官方文档参考

- [创建嵌套块 API](https://open.feishu.cn/document/docs/docs/document-block/create-2)
- [Markdown/HTML 内容转换为文档块 API](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/convert)

---

## Part B: 完整测试流程

### 5. 执行步骤

```
Step 1: 获取 tenant_access_token
  → POST /auth/v3/tenant_access_token/internal

Step 2: 调用 Convert API（可选，已有数据可跳过）
  → POST /docx/v1/documents/blocks/convert
  → 输入: Markdown 内容
  → 输出: blocks（数量因报告而异）, first_level_block_ids

Step 3: 构建嵌套块请求体（由 `wiki_updater.py` 的 `prepare_batches()` 自动处理）
  → 转换规则:
      1. index = 0
      2. children_id = first_level_block_ids（或分批后的子集）
      3. descendants 移除每个块的 parent_id
      4. 移除 table.cells
      5. 移除 table.property.merge_info (关键!)
      6. 确保每个块有 children 字段（没有则补 []）
      7. blocks > 1000 时按子树分组分批（batch_size=1000）

Step 4: 创建 wiki 子节点（飞书自动绑定空 docx 文档）
  → POST /wiki/v2/spaces/{space_id}/nodes
  → space_id、parent_node_token 从 config.yaml → feishu 读取
  → Body: {"parent_node_token": "<wiki父节点token>", "node_type": "origin", "obj_type": "docx", "title": "<报告标题>"}
  → 返回: node_token

Step 5: 获取 wiki 节点对应的 document_id
  → GET /wiki/v2/spaces/get_node?token={node_token}
  → 返回: obj_token (= document_id)

Step 6: 获取根块 block_id
  → GET /docx/v1/documents/{document_id}/blocks?page_size=1
  → 返回: root_block_id

Step 7: 调用创建嵌套块 API（可分批多次调用）
  → POST /docx/v1/documents/{document_id}/blocks/{root_block_id}/descendant
  → 请求体: prepare_batches() 生成的批次数据
  → 成功返回: code=0

Step 8: 输出 wiki 链接（标题在 Step 4 创建 wiki 节点时已设置）
  → wiki 继承空间权限，无需单独开放权限
  → https://{FEISHU_DOMAIN}/wiki/{node_token}
```

### 脚本分工

| 脚本 | 职责 |
|---|---|
| `scripts/wiki_updater.py` | wiki 内容更新全流程：Convert API → prepare_batches() 清洗和分批 → wiki 子节点创建 → 逐批写入 |
| `scripts/publish_report_to_wiki.py` | 端到端全流程验证：从 Markdown 报告 → Convert → 清洗 → 分批 → 创建 wiki 子页面 → 写入 |

**完整端到端流程**（新报告）：
1. 运行 `publish_report_to_wiki.py`（或 `run_check.py` 自动调用）→ 完成全部流程

### 6. 验证与权限

API 通过 wiki 子节点创建的文档，**自动继承知识空间的权限**，无需单独调用权限接口。
如需额外设置链接分享权限，可调用：
- `PATCH /drive/v1/permissions/{doc_id}/public?type=docx`
- 访问链接：`https://{FEISHU_DOMAIN}/wiki/{node_token}`（`FEISHU_DOMAIN` 默认 `wbenergy.feishu.cn`，可通过 `.env` 覆盖）
