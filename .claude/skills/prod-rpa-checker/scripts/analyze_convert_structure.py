"""分析 convert_api_result.json 的层级结构和转换需求"""

import io
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from pathlib import Path

JSON_FILE = Path(__file__).parent.parent / "doc" / "convert_api_result.json"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

blocks = data["blocks"]
first_ids = data["first_level_block_ids"]

print(f"=== convert_api_result.json 结构分析 ===\n")
print(f"总 blocks 数量: {len(blocks)}")
print(f"first_level_block_ids 数量: {len(first_ids)}")

# 构建 block_id → block 映射
block_map = {b["block_id"]: b for b in blocks}

# 统计 block_type
type_count = {}
for b in blocks:
    bt = b.get("block_type")
    type_count[bt] = type_count.get(bt, 0) + 1

print(f"\nblock_type 分布: {json.dumps(type_count, ensure_ascii=False, indent=2)}")

# 分析层级关系
print(f"\n=== 层级关系分析 ===")

# type 31 (table) → children (cell_ids)
# type 32 (table_cell) → children (text_ids)
table_blocks = [b for b in blocks if b.get("block_type") == 31]
cell_blocks = [b for b in blocks if b.get("block_type") == 32]
text_blocks = [b for b in blocks if b.get("block_type") == 2]

print(f"\n表格块 (type=31): {len(table_blocks)} 个")
print(f"单元格块 (type=32): {len(cell_blocks)} 个")
print(f"文本块 (type=2): {len(text_blocks)} 个")

# 检查 table → cell 关系
print(f"\n--- 表格块 children 分析 ---")
total_cells_in_tables = 0
for i, tbl in enumerate(table_blocks[:3]):  # 只看前3个
    cells = tbl.get("children", [])
    total_cells_in_tables += len(cells)
    print(f"表格 {i+1}: block_id={tbl['block_id'][:20]}..., children(cell数量)={len(cells)}")
    # 检查这些 cells 是否存在
    for cid in cells[:2]:
        cell = block_map.get(cid)
        if cell:
            cell_children = cell.get("children", [])
            print(f"  cell={cid[:20]}..., children(text数量)={len(cell_children)}")
            # 检查 text blocks
            for tid in cell_children[:1]:
                txt = block_map.get(tid)
                if txt:
                    elements = txt.get("text", {}).get("elements", [])
                    content = "".join(e.get("text_run", {}).get("content", "") for e in elements)
                    print(f"    text={tid[:20]}..., content='{content[:30]}...'")
        else:
            print(f"  cell={cid[:20]}... ❌ 不存在于 blocks 中!")

# 统计所有表格的 cells
all_table_cells = set()
for tbl in table_blocks:
    for cid in tbl.get("children", []):
        all_table_cells.add(cid)

print(f"\n所有表格引用的 cell_id 总数: {len(all_table_cells)}")
print(f"实际存在的 cell_blocks: {len(cell_blocks)}")
extra = all_table_cells - set(b["block_id"] for b in cell_blocks)
missing = set(b["block_id"] for b in cell_blocks) - all_table_cells
if extra:
    print(f"⚠️ 表格引用了但不存在的 cells: {len(extra)} 个")
if missing:
    print(f"⚠️ 存在但未被任何表格引用的 cells: {len(missing)} 个")

# 检查 parent_id
print(f"\n--- parent_id 分析 ---")
non_empty_parent = [b for b in blocks if b.get("parent_id", "") != ""]
print(f"parent_id 非空的 blocks: {len(non_empty_parent)}")
if non_empty_parent:
    for b in non_empty_parent[:5]:
        print(f"  {b['block_id'][:20]}... parent_id={b['parent_id']}")

# first_level_block_ids 的类型分布
print(f"\n--- first_level_block_ids 类型分布 ---")
first_types = {}
for fid in first_ids:
    b = block_map.get(fid)
    if b:
        bt = b.get("block_type")
        first_types[bt] = first_types.get(bt, 0) + 1
    else:
        print(f"⚠️ first_level_block_id {fid} 不存在于 blocks 中!")
print(f"first_level types: {json.dumps(first_types)}")

# 计算 first_level 中 type=31 (table) 的数量
table_first = [fid for fid in first_ids if block_map.get(fid, {}).get("block_type") == 31]
print(f"\nfirst_level 中表格数量: {len(table_first)}")

# 不在 first_level 中的 blocks
first_set = set(first_ids)
all_ids = set(b["block_id"] for b in blocks)
not_in_first = all_ids - first_set
print(f"不在 first_level 中的 blocks: {len(not_in_first)} 个")

# 这些不在 first_level 中的 blocks 的类型分布
not_first_types = {}
for nid in not_in_first:
    b = block_map.get(nid)
    if b:
        bt = b.get("block_type")
        not_first_types[bt] = not_first_types.get(bt, 0) + 1
print(f"不在 first_level 中的类型分布: {json.dumps(not_first_types)}")

# 总结
print(f"\n=== 转换需求总结 ===")
print(f"1. first_level_block_ids 定义了 {len(first_ids)} 个顶级块")
print(f"2. 表格块 (type=31) 的 children 引用了 {len(all_table_cells)} 个 cell_id")
print(f"3. 每个 cell (type=32) 的 children 引用了 1 个 text block (type=2)")
print(f"4. 转换逻辑: 将扁平 blocks 转为树形结构")
print(f"   - 非表格块: 直接作为 children 元素")
print(f"   - 表格块: block_type 从 31→41, children 改为嵌套的 cell 对象")
print(f"5. 需要移除所有 block_id 和 parent_id（创建嵌套块 API 会自动生成新 ID）")

# 输出第一个表格的完整结构示例
print(f"\n=== 第一个表格的完整嵌套结构示例 ===")
first_table_id = table_first[0]
tbl = block_map[first_table_id]
print(json.dumps(tbl, ensure_ascii=False, indent=2))
