---
name: retail-revenue
description: 计算虚拟电厂业务零售侧收入，支持多用户风险管控、超额收益返还的分步计算
---

# 零售侧收入计算

## 触发方式
当用户提到：
- "计算零售侧收入" / "算一下零售收入" / "零售侧收入"
- "VPP收入计算" / "虚拟电厂收入"
- 提供用户电量、电价等基础数据要求计算零售侧收入时

## 交互规则

- **除非基础数据缺失，否则不要问任何问题，直接执行脚本。**
- 必需基础数据：
  - 月度批发市场度电成本（元/MWh）— 全局参数
  - 批发侧成本（元）— 全局参数
  - 各用户的：月度汇总实际用电量(MWh)、市场联动价格比例、固定价格(元/MWh)、市场联动价格(元/MWh)

## 执行步骤

```
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost <月度批发市场度电成本> \
  --wholesale-total-cost <批发侧成本> \
  --users <JSON文件或内联JSON>
```

### 方式一：JSON 文件输入

```
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost 400 \
  --wholesale-total-cost 50000 \
  --users users.json
```

users.json 格式：
```json
[
  {
    "name": "用户A",
    "actual_consumption": 1000,
    "market_linkage_ratio": 0.3,
    "fixed_price": 450,
    "market_linkage_price": 420
  },
  {
    "name": "用户B",
    "actual_consumption": 2000,
    "market_linkage_ratio": 0.5,
    "fixed_price": 430,
    "market_linkage_price": 420
  }
]
```

### 方式二：文本文档输入

```
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py --text data.txt
```

data.txt 格式（直接从文档/表格复制粘贴即可）：
```
1. 海南川量新能源科技有限公司：
月度批发市场度电成本 	352.26043元/MWh
批发侧成本	3909459.01507175元
用户月度汇总实际用电量 64.8MWh
市场联动价格比例	75%
固定价格 325.000元/MWh
市场联动价格	359.39000
2. 万帮之星科技（海南）有限公司：
月度批发市场度电成本 	352.26043元/MWh
批发侧成本	3909459.01507175元
用户月度汇总实际用电量 2368.84694MWh
市场联动价格比例	70%
固定价格 355.000元/MWh
市场联动价格	369.39000元/MWh
```

也可通过管道传入文本：
```
cat data.txt | xargs -0 python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py --text "$0"
```

### 方式三：交互式输入

```
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py --interactive
```

脚本会逐项提示输入必要参数（月度批发市场度电成本、批发侧成本、各用户数据）。

### 方式四：JSON 输出（便于程序对接）

```
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost 400 --wholesale-total-cost 50000 --users users.json --json
```

添加 `--json` 参数以 JSON 格式输出完整计算结果，方便其他系统消费。

## 输出格式

用表格格式向用户展示：

### 用户维度明细表
- 用户、用电量(MWh)、固定价格电费、市场联动电费、零售套餐电费、电能量结算均价、风险管控费用、风险状态（枚举值：未触发/上限触发/下限触发）、超额收益返还费用、零售侧收入

### 售电公司汇总
- 售电公司售电收益（扣除批发侧成本后）、售电公司收益均价、超额收益返还触发

## 脚本路径
`.claude/skills/retail-revenue/scripts/retail_revenue_calculator.py`

## 计算逻辑

### 8步计算链（严格按顺序执行，禁止循环依赖）

| 步骤 | 公式 |
|------|------|
| 1. 用户固定价格电费 | 用户实际用电量 × (1 − 市场联动价格比例) × 固定价格 |
| 2. 用户市场联动电费 | 用户实际用电量 × 市场联动价格比例 × 市场联动价格 |
| 3. 用户零售套餐电费 | 步骤1 + 步骤2 |
| 4. 用户电能量结算均价 | 步骤3 ÷ 用户实际用电量 |
| 5. 用户风险管控费用 | 高价触发：用电量 × (度电成本×110% − 结算均价)；低价触发：用电量 × (度电成本×90% − 结算均价) |
| 6. 用户电量电费 | 步骤3 + 步骤5 |
| 7. 售电公司汇总 | 售电收益 = SUM(步骤6) − 批发侧成本；收益均价 = 售电收益 ÷ 总用电量 |
| 8. 超额收益返还 & 最终收入 | 见下方规则 |

### 风险管控触发规则

结算均价与月度批发市场度电成本的比值判断：
- 结算均价 ∈ [度电成本×90%, 度电成本×110%]（闭区间）→ 风险管控费用 = 0（**不触发**）
- 结算均价 > 度电成本×110%（高价触发）→ 风险管控费用 = 用户实际用电量 × (月度批发市场度电成本×**110%** − 结算均价)
- 结算均价 < 度电成本×90%（低价触发）→ 风险管控费用 = 用户实际用电量 × (月度批发市场度电成本×**90%** − 结算均价)

### 超额收益返还规则

- 售电公司收益均价 > 15 元/MWh → **触发**
  - 售电公司超额收益返还电费 = (售电公司收益均价 − 15) × 总用电量 × 0.7
  - 用户维度超额收益返还电费 = 用户用电量 ÷ 总用电量 × 售电公司超额收益返还电费
- 售电公司收益均价 ≤ 15 元/MWh → 超额收益返还 = 0（**不触发**）

### 最终收入

- 用户零售侧收入 = 用户零售套餐电费 + 用户风险管控费用 − 用户超额收益返还电费
- 零售侧总收入 = SUM(所有用户零售侧收入)

### 注意事项

- 风险管控费用可能为负值（当结算均价 > 度电成本×110% 时，向用户退款）
- 风险管控费用可能为正值（当结算均价 < 度电成本×90% 时，用户补交）
- 所有金额单位为**元**，电量单位为**MWh**，价格单位为**元/MWh**
