---
name: retail-revenue-data-sources
description: 海南零售侧收入计算的基础数据来源约定
metadata:
  type: feedback
---

计算海南零售侧收入时，基础数据必须从以下两个来源获取：

1. **静态文本文件**：`.claude/skills/retail-revenue/海南零售侧收入基础数据（适配技能retail-revenue）.txt`
2. **数据库 SQL 脚本**：`.claude/skills/db-connector/sqls/` 目录下的 SQL 文件（如 `query_user_monthly_energy.sql`、`query_wholesale_cost.sql`）

**Why:** 用户明确要求——避免硬编码数据，所有基础数据应从这两个来源动态获取，确保数据可维护和复用。

**How to apply:** 每次执行 retail-revenue 技能计算时，优先读取上述文件获取基础数据，不要假设或硬编码任何参数。
