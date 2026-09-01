---
name: combo-stability-writer
description: 当用户提到"写入计算器"、"报文数据写入Excel"、"更新指标计算器"、"组合稳定性计算器数据"、"回填数据区"、"写入日期/每日排名/策略收益/实际收益/有效天标志列"、"写入综合评价标签"、"写入分位线"等关键词，需要把 algorithmRetrospectiveCombinations.json 报文数据写入组合稳定性分布_指标计算器.xlsx 时自动触发。
---

# 组合稳定性分布 · 指标计算器数据写入

从 `algorithmRetrospectiveCombinations.json` 接口报文中提取指定模型组合的数据，按需求口径计算每日排名，收益按报文原值(元)写入指标计算器 Excel 的数据区（19~49 行），同时写入综合评价标签（B16）与分位线（B17），并与报文指标交叉校验。

## 当前 Excel 布局（2026-08-21 版，用户插入两行后）
| 位置 | 内容 |
|------|------|
| A5 | 指标计算区标题（合并 A5:E5 锚点），动态显示目标组合：`指标计算区(<label>)`，如 `指标计算区(太乙-七天前实际负荷 × 综合模型)` |
| B16 | 综合评价标签值（如"表现中等"） |
| B17 | 分位线与值，格式"分位线（值）"，如 `P10(63.8)/P35(78.5)/P65(93.9)/P90(118.2)` |
| 18 行 | 数据表头：日期｜每日排名 r｜策略收益(元)｜实际收益(元)｜有效天标志 |
| 19~49 行 | 数据区（最多 31 天） |
| A51 / A52:E59 | 口径说明标题 / 合并说明区 |

## 触发方式
当用户提到以下关键词或表达时**自动触发**：
- "写入计算器" / "更新指标计算器" / "报文数据写入Excel" / "回填计算器数据"
- "写入 A16:E47" / "写入日期、每日排名、策略收益、实际收益、有效天标志列"
- 提供 algorithmRetrospectiveCombinations.json 并要求把某组合数据填入组合稳定性分布计算器时

## 功能
1. 读取报文：`combinations[]`（全量组合，当前报文 240 个）+ `actualBaseline[]`（全局共享实际收益基准）
2. 选定目标组合：`--combo` 指定 label，缺省自动选 validDays 最高者
3. 计算每日排名（口径见下节），策略/实际收益按**报文原值(元)直接写入**（显示 2 位小数、存储原值精度）
4. 写入计算器 19 行起数据区：A 日期 / B 每日排名 / C 策略收益(元) / D 实际收益(元)；**E 列有效天公式自动重建**（不写死值）
5. **综合评价标签 → B16**：全量组合按 mode 口径算 LCB（μ+σ/√T，对齐 spot_review.js:860-880），升序取 P10/P35/P65/P90 分位线（对齐 1070-1097），目标组合定档：≤P10 稳定优秀 / ≤P35 较稳定 / >P90 易爆雷 / >P65 不稳定 / else 表现中等
6. **分位线与值 → B17**：格式"分位线（值）"四条分位线拼接，如 `P10(63.8)/P35(78.5)/P65(93.9)/P90(118.2)`
7. 无效天行高亮（FFF2CC），同步更新 **A5 指标计算区标题（指标计算区(<目标组合label>)，随 --combo 切换）**、**B2 组合总数(label个数)**、**B4 区间天数 D=len(dailyDataList)** 与口径说明区第 3/4/6/8 条（第 6 条负责校正 LCB 公式口径为 μ+z·σ/√T）
8. 写入后与报文四字段交叉校验（validDays/winDays/winRate/coverage），不一致即报错退出

## 明确不动的单元格（用户约定）
- **A18:E18** 数据表头行
- **A1~A17 列的标题/标签文本，但 A5 除外**（A5 为技能维护单元格，每次写入同步目标组合名；B16/B17 的值写入不受影响）
- **B3**（z 系数）、**B6:B15 公式区**（保持公式，数据写入后由 Excel 自动重算）

## 数据口径（核心约定，勿改动）
| 项 | 口径 |
|----|------|
| 有效天 | 当日策略收益 ≠ 0 且非空，**且**该日实际收益数据存在（考核数据与实际收益数据是两套数据，但**存在性判定等价**，故以实际收益是否存在判定） |
| 每日排名 | **竞赛排名法**：当日参与组合按策略收益降序，**并列同名次、下一名次跳过**（名次=当日收益严格更高者个数+1，对齐报文后端 dailyRank 口径；2026-08-26 由相邻名次法改入）；参与口径与有效天一致（需求口径） |
| 无效天三类 | ① strategyProfit 键缺失（B/C 留空）② 策略收益=0（C 写 0）③ 实际收益缺失（D 留空；若策略收益非零，B 也留空——前端 847 行会违规赋排名，属 TP-CH1-002-006 缺陷） |
| 覆盖率 | validDays ÷ 区间天数 D，**D = len(dailyDataList)**（绝不能用 len(actualBaseline)，其=有实际收益的天数 A ≤ D） |
| 胜率 | winDays ÷ validDays，胜天 = 当日策略收益 > 当日实际收益（跑赢实际） |
| 单位 | 报文原值（元）**直接写入，不换算**；显示 2 位小数（`0.00`），存储原值精度保证 C>D 胜天判定不受舍入影响（2026-08-26 由"÷10000 万元显示 4 位"改入） |
| 综合评价标签 | 跨组合横向分位（非每日排名与 topK 比较）：LCB=μ+z·σ/√T(z=1)，全员 LCB 升序取分位线定档（对齐 spot_review.js:1070-1097） |

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
- `--json <path>` — 报文路径，默认 `.qoder/skills/combo-stability-writer/algorithmRetrospectiveCombinations.json`（报文已随技能内置，2026-08-26 从 picture 目录迁入）
- `--excel <path>` — 计算器路径，默认 `.qoder/skills/combo-stability-writer/组合稳定性分布_指标计算器.xlsx`（计算器已随技能内置于技能根目录，2026-08-26 从 output 目录迁入）
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
- 报文 `dailyDataList` 长度须 ≤ 31（计算器数据区容量 19~49 行）；不足 31 天会自动清空多余旧行并同步 B4
- **布局假设已适配 2026-08-21 版**（用户插入 16/17 两行）；若用户再次手工插行，必须先读盘核对 DATA_START/说明区锚点再改脚本常量
- 脚本已规避 openpyxl 的 `cell(value=None)` 不清空旧值陷阱（显式 `.value = None`），可安全重复执行
- `--rank-mode frontend` 下 Excel 的 μ/σ/LCB 仍按 E 列门控（正确口径），与页面缺陷值不同，差异即 TP-CH1-002-006 的量化证据

## 脚本与资源路径
- 脚本：`.qoder/skills/combo-stability-writer/scripts/write_calc_data.py`
- 报文：`.qoder/skills/combo-stability-writer/algorithmRetrospectiveCombinations.json`（技能内置，勿再引用旧路径 .qoder/picture/）
- 计算器：`.qoder/skills/combo-stability-writer/组合稳定性分布_指标计算器.xlsx`（技能内置，勿再引用旧路径 .qoder/output/aiAutoTester/组合稳定性分布/）
