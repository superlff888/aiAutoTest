---
name: retail-revenue-output
description: 零售侧收入计算的固定输出格式和数据获取流程
metadata:
  type: feedback
---

## 零售侧收入计算 - 固定输出格式

**数据获取流程**（固定步骤，按顺序执行）：

1. **用户月度用电量** — SQL 查询
   ```
   python .claude/skills/db-connector/scripts/db_executor.py exec test --file .claude/skills/db-connector/sqls/query_user_monthly_energy.sql
   ```

2. **批发侧成本** — SQL 查询
   ```
   python .claude/skills/db-connector/scripts/db_executor.py exec test --file .claude/skills/db-connector/sqls/query_wholesale_cost.sql
   ```

3. **用户合同参数** — 从文本文件读取
   ```
   .claude/skills/retail-revenue/海南零售侧收入基础数据（适配技能retail-revenue）.txt
   ```

4. **组装文本跑计算**
   用 `--text` 模式调用 `retail_revenue_calculator.py`，将 SQL 原始数据和合同参数组装为文本格式输入。

**输出格式**（严格按此 4 个部分，不多不少）：

```
【基础参数】
  月度批发市场度电成本：xxx 元/MWh
  批发侧成本：xxx 元
  总用电量：xxx MWh
  用户数：x

【用户维度明细】

| 用户 | 用电量(MWh) | 零售套餐电费 | 风险管控费用 | 风险状态 | 零售侧收入 |
|---|---|---|---|---|---|
| xxx | xxx | xxx | xxx | xxx | xxx |

【售电公司汇总】
  售电公司售电收益（扣除批发侧成本后）：xxx 元
  售电公司收益均价：xxx 元/MWh
  超额收益返还触发：是/否
  售电公司超额收益返还电费：xxx 元  （仅触发时显示）
  返还比例：70%  （仅触发时显示）

【零售侧总收入】 xxx 元
```

**关键规则**：
- 数据库查询输出原始数据，不做任何格式化
- 【用户维度明细】用 Markdown 表格，只有 6 列：用户、用电量(MWh)、零售套餐电费、风险管控费用、风险状态、零售侧收入
- 只输出这 4 个部分，不做任何额外解读或备注
- 脚本用 `--text` 模式，表格由 Claude Code 直接渲染
