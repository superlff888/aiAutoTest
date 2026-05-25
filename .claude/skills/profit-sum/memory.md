---
name: auto-sum-arbitrage-strategy-profit
description: 用户发送 JSON 数据时，自动同时计算 arbitrageProfits 和 strategyProfit 的总和
type: feedback
---

用户发 JSON 数组数据时，默认同时计算两个字段的总和：
- **arbitrageProfits 之和**
- **strategyProfit 之和**

**Why:** 用户日常工作中需要频繁查看这两个字段的汇总值，不希望每次都要手动指定字段或分两次计算。

**How to apply:** 当用户提供 JSON 数组并要求计算套利收益/策略收益/利润汇总时，直接使用 `scripts/sum_strategy_profit.py --profit --input <数据>` 一次性输出两个字段的结果。
