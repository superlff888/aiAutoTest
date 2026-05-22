---
name: strategy-profit-sum
description: 当用户提到"套利收益"、"套利利润"、"策略收益"等关键词时自动触发，从 JSON 数组中提取指定数值字段并求和
---

# JSON 数值字段求和

## 触发方式
当用户提到以下关键词或表达时**自动触发**：
- "套利收益" / "套利利润" / "策略收益" / "策略利润"
- "strategyProfit" / "arbitrageProfits" / "maxArbitrageProfit"
- 用户提供一段 JSON 数组数据并要求汇总某个字段的总和时

## 执行方式

```bash
python .claude/skills/strategy-profit-sum/scripts/sum_strategy_profit.py --input <json文件或内联数据> --field <字段名>
```

默认输出：
- 所有目标字段的明细（time + value）
- 总计条数
- 总和（保留 4 位小数）

支持参数：
- `--input <file_or_json>` — JSON 文件路径或直接传入 JSON 字符串
- `--field <field_name>` — 要求和的字段名，默认 `strategyProfit`
- `--time-field <field_name>` — 时间/标签列字段名，默认 `time`

## 常用字段
- `strategyProfit` — 策略收益（默认）
- `arbitrageProfits` — 套利收益
- `maxArbitrageProfit` — 最大套利收益
- `deviationRecovery` — 偏差恢复
- `strategyDeviationRecovery` — 策略偏差恢复

## 脚本路径
`.claude/skills/strategy-profit-sum/scripts/sum_strategy_profit.py`
