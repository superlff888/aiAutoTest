---
name: retail-revenue-data-workflow
description: 海南零售侧收入计算的数据获取流程，包含SQL查询和文本文件读取步骤
---

## 海南零售侧收入 - 数据获取流程

当用户要求计算海南零售侧收入时，按以下固定步骤获取数据：

### Step 1：用户月度用电量 — SQL 查询

```bash
python .claude/skills/db-connector/scripts/db_executor.py exec test --file .claude/skills/db-connector/sqls/query_user_monthly_energy.sql
```

输出格式：`公司名称 | 用电量原始值`

### Step 2：批发侧成本 — SQL 查询

```bash
python .claude/skills/db-connector/scripts/db_executor.py exec test --file .claude/skills/db-connector/sqls/query_wholesale_cost.sql
```

输出格式：`月度批发市场度电成本原始值 | 批发侧成本原始值`

### Step 3：用户合同参数 — 文本文件读取

```
.claude/skills/retail-revenue/海南零售侧收入基础数据（适配技能retail-revenue）.txt
```

包含：市场联动价格比例、固定价格、市场联动价格

### Step 4：组装文本跑计算

将 SQL 原始数据与合同参数组装为文本文档格式，用 `--text` 模式调用 `retail_revenue_calculator.py`。

### Step 5：按固定格式输出

严格按 4 段输出：【基础参数】、【用户维度明细】、【售电公司汇总】、【零售侧总收入】
