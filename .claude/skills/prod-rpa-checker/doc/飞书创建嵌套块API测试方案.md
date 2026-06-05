# 飞书"创建嵌套块" API 测试方案

> 编写日期：2026-06-05
> 目的：验证通过 convert API + 创建嵌套块 API，能否将 Markdown 报告以原生格式（含表格、粗体等）写入飞书文档

---

## 1. 核心发现

| 项 | 内容 |
|---|------|
| **端点路径** | `POST /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}/descendants` |
| **功能** | 递归嵌套创建块（支持一次性创建 table + cells + 内容） |
| **Table 的 block_type** | **41**（注意：convert API 返回的是 31，两者不同！） |
| **TableCell 的 block_type** | **32** |

### 关键问题

convert API 返回的 table `block_type=31`，而创建嵌套块需要 `block_type=41`。
这说明 convert 返回的 blocks 不能直接用于"创建嵌套块"，需要格式转换。

---

## 2. 测试步骤

### Step 1：构造请求体

**目的**：手动构造一个符合"创建嵌套块" API 格式的请求体，包含表格+非表格内容。

请求体结构示例：
```json
{
  "children": [
    {
      "block_type": 3,
      "heading1": {"elements": [{"text_run": {"content": "测试标题"}}]}
    },
    {
      "block_type": 41,
      "table": {
        "cells": ["cell_A1", "cell_B1", "cell_A2", "cell_B2"],
        "property": {"row_size": 2, "column_size": 2, "column_width": [200, 200]}
      },
      "children": [
        {
          "block_id": "cell_A1",
          "block_type": 32,
          "table_cell": {},
          "children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "列1"}}]}}]
        },
        {
          "block_id": "cell_B1",
          "block_type": 32,
          "table_cell": {},
          "children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "列2"}}]}}]
        },
        {
          "block_id": "cell_A2",
          "block_type": 32,
          "table_cell": {},
          "children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "A"}}]}}]
        },
        {
          "block_id": "cell_B2",
          "block_type": 32,
          "table_cell": {},
          "children": [{"block_type": 2, "text": {"elements": [{"text_run": {"content": "1"}}]}}]
        }
      ]
    }
  ]
}
```

### Step 2：创建空白文档，获取 document_id 和 root_block_id

**目的**：准备一个目标文档。

### Step 3：调用"创建嵌套块" API

**目的**：验证嵌套结构能否正确创建，特别是表格是否渲染为原生表格。

### Step 4：在飞书中查看文档

**目的**：肉眼确认表格、标题是否正确显示。

### Step 5：如果 Step 3 成功，测试 convert → 转换 → 嵌套创建

**目的**：验证 convert API + 格式转换 + 嵌套创建的完整链路是否可行。

---

## 3. 关键 API 端点

| API | 端点 | 用途 |
|-----|------|------|
| 获取 token | `POST /auth/v3/tenant_access_token/internal` | 获取 API 访问凭证 |
| 创建文档 | `POST /docx/v1/documents` | 创建空白云文档 |
| 获取文档块 | `GET /docx/v1/documents/{doc_id}/blocks` | 获取 root_block_id |
| 创建嵌套块 | `POST /docx/v1/documents/{doc_id}/blocks/{block_id}/descendants` | 递归嵌套创建块 |

## 4. 请求头参数

| 参数 | 值 |
|------|-----|
| Authorization | `Bearer {tenant_access_token}` |
| Content-Type | `application/json; charset=utf-8` |

## 5. 官方文档参考

- **创建嵌套块**: https://open.feishu.cn/document/docs/docs/document-block/create-2
- **块的数据结构**: https://open.feishu.cn/document/docs/docs/data-structure/block
- **创建块**: https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/create
- **Convert Markdown/HTML**: https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/convert
- **批量创建块**: https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/create

---

## 6. Convert API 实际调用结果（2026-06-05）

### 6.1 测试内容

- **报告文件**: `output/rpa_check_report_20260604181316.md`
- **文件大小**: 7999 字符，185 行
- **包含**: 13 个交易中心的校验报告，每个中心含 1 个表格

### 6.2 调用结果

| 项 | 值 |
|---|---|
| **状态码** | 200 |
| **code** | 0 |
| **msg** | success |
| **返回 blocks 数量** | **1000** |
| **first_level_block_ids 数量** | **48** |

### 6.3 块类型分布

| block_type | 含义 | 数量 |
|-----------|------|------|
| 2 | 文本（text/paragraph） | 478 |
| 32 | 表格单元格（table_cell） | 476 |
| 12 | 无序列表（bullet） | 16 |
| 31 | 表格容器（table） | 13 |
| 4 | 二级标题（heading2） | 14 |
| 5 | 三级标题（heading3） | 1 |
| 22 | 引用块（quote） | 1 |
| 3 | 一级标题（heading1） | 1 |

### 6.4 关键发现

1. **13 个表格容器（type=31）**，每个表格对应 1 个交易中心
2. **476 个单元格（type=32）**，每个表格约 10 行 × 4 列 = 40 单元格，13 × 40 ≈ 520，实际 476 说明部分表格行数较少
3. **48 个 first_level_block_ids**，对应 13 个中心表格块 + 标题 + 汇总段落等顶级块
4. **响应已保存**: `doc/convert_api_result.json`（可用于后续格式转换分析）

### 6.5 核心目标：创建嵌套块 API 必须支持的目标数据

**目标数据源**: `doc/convert_api_result.json`（由 Convert API 对实际报告内容调用生成）

**核心要求**: 创建嵌套块 API 的请求体经格式转换后，写入飞书文档的内容**必须与 convert_api_result.json 中的语义内容完全一致**，即：

| 要求 | 说明 |
|------|------|
| **标题** | H1/H2/H3 文本内容完全一致 |
| **表格** | 13 个表格，每个行列数、单元格内容完全一致（原生表格渲染） |
| **粗体/斜体/行内代码** | 行内格式样式完全一致 |
| **列表** | 16 个无序列表项内容一致 |
| **段落文本** | 所有文本内容一致（共 478 个文本块） |

### 6.6 convert_api_result.json 完整结构分析

**层级关系**: 1000 个 blocks 全部扁平（`parent_id=""`），通过 `children` 引用链建立层级：

```
first_level_block_ids (48个顶级块)
├── 非表格块 (35个): H1(1), H2(14), H3(1), 文本(2), 无序列表(16), 引用块(1)
│   └── 直接渲染，无子块
│
└── 表格块 (13个, type=31)
    └── children → 单元格 (476个, type=32)
        └── children → 文本块 (476个, type=2)
            └── text.elements[].text_run → 实际内容
```

**数据量统计**:
- first_level 中非表格块: 35 个（标题+文本+列表等）
- first_level 中表格块: 13 个（每个交易中心 1 个表格）
- 单元格总数: 476 个（每个表格 11 行×4 列≈44 个，13×44≈572，部分表格行数不同，实际 476）
- 单元格内文本块: 476 个（每个 cell 含 1 个 text block）
- 总 blocks = 35(非表格) + 13(表格) + 476(cells) + 476(cell内texts) = 1000

**不在 first_level 中的 952 个 blocks 全部是**:
- 476 个单元格（type=32）
- 476 个单元格内文本（type=2）

### 6.7 Convert → 创建嵌套块的转换逻辑

**转换原理**: 将扁平的 1000 blocks 转为 3 层嵌套结构（`{children: [...]}`）

**转换规则**:

1. **非表格块**（不在 first_level 中的 cells/texts 之外的所有块）:
   - 按 `first_level_block_ids` 顺序遍历
   - 直接作为 `children` 元素传入
   - 移除 `block_id` 和 `parent_id` 字段（创建嵌套块 API 会自动生成新 ID）

2. **表格块**（type=31 → type=41）:
   - 将 `block_type` 从 31 改为 **41**
   - 将 `children` 数组从 `["cell_id_1", ...]` 改为**完整的 cell block 对象数组**：
     ```
     原结构: "children": ["cell_id_A", "cell_id_B", ...]
     新结构: "children": [
       {block_id: "cell_id_A", block_type: 32, table_cell: {}, children: [
         {block_type: 2, text: {elements: [...]}}
       ]},
       {block_id: "cell_id_B", block_type: 32, table_cell: {}, children: [
         {block_type: 2, text: {elements: [...]}}
       ]},
       ...
     ]
     ```
   - 每个 cell 对象嵌套其对应的 text block（从 blocks map 中查找）
   - 移除 cell block 的 `parent_id` 字段
   - 移除 text block 的 `block_id` 和 `parent_id` 字段
   - cell 的 `block_id` **必须保留**（table.property.cells 和 table.children 数组中引用的是相同的 ID）

3. **最终请求体格式**:
   ```json
   {
     "children": [
       // 非表格块（按 first_level 顺序）
       {"block_type": 3, "heading1": {...}},
       {"block_type": 2, "text": {...}},
       // 表格块（含嵌套 cells）
       {
         "block_type": 41,
         "table": {...},
         "children": [
           {"block_id": "cell_A1", "block_type": 32, "table_cell": {}, "children": [
             {"block_type": 2, "text": {...}}
           ]},
           ...
         ]
       },
       ...
     ]
   }
   ```

**转换后 blocks 数量**: 35(非表格) + 13(表格) = **48 个顶级 children**

**完整性验证**: 转换后的嵌套结构包含所有 1000 个原始 blocks 的语义内容（标题文本、表格行列内容、列表项、段落等），只是从扁平引用改为嵌套结构。
