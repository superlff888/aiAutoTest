---
name: wind-vector-compose
description: 当用户提到"综合风向"、"风向合成"、"风向风速合成"、"多采样点风向"、"区域风向"、"主导风向"、"风向向量平均"等关键词，并提供多个采样点的风向/风速时序数组要求合成时自动触发，按“同一时刻、跨采样点”做风速加权向量合成，输出各时刻的综合风向数组。
---

# 多采样点风向/风速时序向量合成

对同一省份（或区域）下多个采样点的风向、风速时序数据，逐时刻做**风速加权的向量合成**，得到能代表整体的“综合风向”时间序列。

## 触发方式
当用户提到以下关键词或表达时**自动触发**：
- "综合风向" / "风向合成" / "风向风速合成" / "区域风向" / "主导风向"
- "多采样点风向" / "风向向量平均" / "多点风向求平均"
- 用户提供 N 个采样点的风向数组 + 风速数组，要求合成一个综合风向数组时

## 核心公式
对每一个时刻 t（数组下标），取该时刻所有采样点的风向 `d_i` 与风速 `v_i`：

1. 每个采样点风向转二维向量（气象约定 0°=正北、顺时针）：
   - `x_i = v_i * sin(radians(d_i))`　（东向分量）
   - `y_i = v_i * cos(radians(d_i))`　（北向分量）
2. 跨采样点求和：`x = Σx_i`，`y = Σy_i`
3. 还原角度并归一：`direction = degrees(atan2(x, y)) % 360`

## 关键约定（易错点）
- **角度→弧度**：`sin/cos` 输入必须先 `math.radians()`；**弧度→角度**：`atan2` 结果必须 `math.degrees()`，否则拿到的是弧度值。
- **参数顺序**：还原角度用 `atan2(x, y)`（不是 `atan2(y, x)`），因为角度从北（y 轴）顺时针计量。
- **归一**：`% 360` 把 `atan2` 可能出现的负角归一到 `[0, 360)`。
- **风速是权重**：风大的采样点对合成方向影响大；若缺失风速而统一取 1，则退化为“纯方向平均”，二者物理含义不同，需向用户确认。
- **边界值鲁棒**：风向含 `360.0`、`304.0` 等值无需特殊处理，`radians` 可直接计算。

## 执行方式

```bash
python .claude/skills/wind-vector-compose/scripts/compose_wind_direction.py \
  --input <json文件或内联JSON>
```

或分开传两个数组：

```bash
python .claude/skills/wind-vector-compose/scripts/compose_wind_direction.py \
  --speeds <风速二维数组> --directions <风向二维数组>
```

## 输入结构
`speeds` 与 `directions` 均为**二维数组**：外层是采样点，内层是时刻序列，两者采样点数量与每个时刻长度必须一致。

`--input` 的 JSON 对象格式：
```json
{
  "speeds":     [[点1的24个风速], [点2的24个风速], ...],
  "directions": [[点1的24个风向], [点2的24个风向], ...]
}
```

## 参数说明
- `--input <file_or_json>` — JSON 文件路径或内联 JSON 对象（含 `speeds`、`directions` 键）
- `--speeds <file_or_json>` / `--directions <file_or_json>` — 与 `--input` 二选一，分别传两个二维数组
- `--round <n>` — 结果保留小数位，默认 `2`
- `--consistency` — 额外输出各时刻“方向一致性”（合成向量长度 / 风速总和，越接近 1 表示各点风向越一致）

## 输出
- 一个与时刻数等长的**综合风向数组**（单位：度，范围 `[0, 360)`）
- 可选：各时刻方向一致性数组

## 脚本路径
`.claude/skills/wind-vector-compose/scripts/compose_wind_direction.py`
