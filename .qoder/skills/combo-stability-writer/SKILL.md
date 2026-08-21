---
name: combo-stability-writer
description: 当用户提到"写入计算器"、"报文数据写入Excel"、"更新指标计算器"、"组合稳定性计算器数据"、"回填A16:E47"、"写入日期/每日排名/策略收益/实际收益/有效天标志列"等关键词，需要把 algorithmRetrospectiveCombinations.json 报文数据写入组合稳定性分布_指标计算器.xlsx 时自动触发。
---

# 组合稳定性分布 · 指标计算器数据写入

从 `algorithmRetrospectiveCombinations.json` 接口报文中提取指定模型组合的数据，按需求口径计算每日排名、换算万元后写入指标计算器 Excel 的 A16:E47 数据区，并与报文指标交叉校验。

## 触发方式
当用户提到以下关键词或表达时**自动触发**：
- "写入计算器" / "更新指标计算器" / "报文数据写入Excel" / "回填计算器数据"
- "写入 A16:E47" / "写入日期、每日排名、策略收益、实际收益、有效天标志列"
- 提供 algorithmRetrospectiveCombinations.json 并要求把某组合数据填入组合稳定性分布计算器时

## 功能
1. 读取报文：`combinations[]`（180 组合）+ `actualBaseline[]`（全局共享实际收益基准）
2. 选定目标组合：`--combo` 指定 label，缺省自动选 validDays 最高者
3. 计算每日排名（口径见下节），策略/实际收益 ÷10000 换算万元（存储 6 位精度、显示 4 位小数）
4. 写入计算器 A17 起数据区：A 日期 / B 每日排名 / C 策略收益(万) / D 实际收益(万)；**E 列有效天公式自动重建**（不写死值）
5. 无效天行高亮（FFF2CC），同步更新 B4 区间天数与口径说明区第 3/4/8 条
6. 写入后与报文四字段交叉校验（validDays/winDays/winRate/coverage），不一致即报错退出

## 数据口径（核心约定，勿改动）
| 项 | 口径 |
|----|------|
| 有效天 | 当日策略收益 ≠ 0 且非空，**且**该日实际收益数据存在（考核数据与实际收益数据是两套数据，但**存在性判定等价**，故以实际收益是否存在判定） |
| 每日排名 | 当日参与组合按策略收益**降序稳定排序**，名次=位置序号；**并列按报文顺序取相邻名次**（对齐 spot_review.js:849-852）；参与口径与有效天一致（需求口径） |
| 无效天三类 | ① strategyProfit 键缺失（B/C 留空）② 策略收益=0（C 写 0）③ 实际收益缺失（D 留空；若策略收益非零，B 也留空——前端 847 行会违规赋排名，属 TP-CH1-002-006 缺陷） |
| 覆盖率 | validDays ÷ 区间天数 D，**D = len(dailyDataList)**（绝不能用 len(actualBaseline)，其=有实际收益的天数 A ≤ D） |
| 胜率 | winDays ÷ validDays，胜天 = 当日策略收益 > 当日实际收益（跑赢实际） |
| 单位换算 | 报文原值（元）÷10000 = 万元；显示 4 位小数，存储 6 位精度保证 C>D 判定不受舍入影响 |

## 执行方式

```bash
# 列出组合摘要（按 validDays 降序，供选择 --combo）
python .qoder/skills/combo-stability-writer/scripts/write_calc_data.py --list

# 写入（缺省自动选 validDays 最高组合，需求口径排名）
python .qoder/skills/combo-stability-writer/scripts/write_calc_data.py

# 指定组合与前端口径
python .qoder/skills/combo-stability-writer/scripts/write_calc_data.py \
  --combo "太乙-七天前实际负荷 × 综合模型" --rank-mode frontend
```

Windows PowerShell 实际执行示例（venv）：
```powershell
$env:PYTHONUTF8="1"; & "E:\AI\pythonProject\aiAutoTest\.venv\Scripts\python.exe" .qoder\skills\combo-stability-writer\scripts\write_calc_data.py --list
```

## 参数说明
- `--json <path>` — 报文路径，默认 `.qoder/picture/algorithmRetrospectiveCombinations.json`
- `--excel <path>` — 计算器路径，默认 `.qoder/output/aiAutoTester/组合稳定性分布/组合稳定性分布_指标计算器.xlsx`
- `--combo <label>` — 目标组合 label（报文 combinations[].label），缺省自动选 validDays 最高者
- `--rank-mode <requirement|frontend>` — 排名口径：`requirement`（默认，有效天参与，实际收益缺失日留空）；`frontend`（仅收益非零非空即参与，复现 spot_review.js:847 缺陷行为，仅 B 列多写对比值，指标统计仍由 E 列门控）
- `--list` — 仅列出组合摘要，不写 Excel
- `--dry-run` — 只计算与校验，不写 Excel
- `--top <n>` — `--list` 显示条数，默认 20

## 输出与校验
- 写入摘要：目标组合、区间、D/A、无效天清单（含类型）
- 交叉校验：Excel 模拟值 T/W/胜率/覆盖率 vs 报文四字段，PASS/FAIL
- 预计算（报文无对应字段，仅供参考）：μ/σ/前10%率/爆雷率/LCB

## 注意事项
- **写入前必须关闭 Excel 文件**（否则 PermissionError，脚本会明确提示）
- 报文 `dailyDataList` 长度须 ≤ 31（计算器数据区容量 17~47 行）；不足 31 天会自动清空多余旧行并同步 B4
- 脚本已规避 openpyxl 的 `cell(value=None)` 不清空旧值陷阱（显式 `.value = None`），可安全重复执行
- `--rank-mode frontend` 下 Excel 的 μ/σ/LCB 仍按 E 列门控（正确口径），与页面缺陷值不同，差异即 TP-CH1-002-006 的量化证据

## 脚本路径
`.qoder/skills/combo-stability-writer/scripts/write_calc_data.py`
