# 零售侧收入计算技能（retail-revenue）

## 业务归属

海南交易中心 — 虚拟电厂业务

## 功能说明

计算虚拟电厂业务中零售侧收入，支持多用户的分步计算，包含：

- **零售套餐电费**：固定价格电费 + 市场联动电费
- **风险管控费用**：根据用户结算均价与批发度电成本的比值判断是否触发（上限/下限）
- **超额收益返还**：售电公司收益均价超过 15 元/MWh 时触发
- **零售侧总收入**：所有用户零售侧收入之和

## 使用方式

### JSON 模式

```bash
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost 352.26 --wholesale-total-cost 848867.66 \
  --users users.json
```

### 文本文档模式

```bash
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost 352.26 --wholesale-total-cost 848867.66 \
  --text data.txt
```

### 交互模式

```bash
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py --interactive
```

### JSON 输出

```bash
python .claude/skills/retail-revenue/scripts/retail_revenue_calculator.py \
  --wholesale-cost 352.26 --wholesale-total-cost 848867.66 \
  --users users.json --json
```

## 文件结构

```
retail-revenue/
├── SKILL.md                          # 技能定义和计算规则
├── memory.md                         # 业务归属记忆
├── README.md                         # 本文件
└── scripts/
    └── retail_revenue_calculator.py  # Python 计算脚本
```
