---
name: retail-revenue-skill
description: retail-revenue 技能属于海南交易中心，用于计算其虚拟电厂业务的零售侧收入
type: project
---

零售侧收入计算技能（retail-revenue）属于**海南交易中心**。

**How to apply:** 当使用该技能时，计算逻辑和规则均基于海南交易中心的业务场景。如有规则变更，需确认是否适用于海南交易中心。

---
name: retail-revenue-no-approval
description: 执行零售侧收入计算脚本时，不要询问确认，直接运行
type: feedback
---

**规则**：执行零售侧收入计算脚本（retail_revenue_calculator.py）时，直接运行，不要询问确认。

**Why**：用户明确说了"以后不要再找我审核以上了"。

**How to apply**：每次需要执行零售侧收入计算时，直接调用 Bash 运行脚本，不要等用户批准。
