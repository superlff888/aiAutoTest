# 网侧预测 / 网侧实际 load_type 覆盖度校验 — 技术方案

> 编写日期：2026-06-17
> 状态：方案已拍板，待实施
> 涉及文件：`scripts/data_validator.py`、`scripts/report_builder.py`、`scripts/feishu_notifier.py`、`SKILL.md`

---

## 1. 背景与目标

### 1.1 现状问题

当前 `check_data_volume` 对网侧预测 / 网侧实际使用硬编码阈值 `4 ≤ 每天条数 ≤ 20`：

```python
# data_validator.py:309
if day_count < 4 or day_count > 20:
    ...
```

**问题**：

| 问题 | 说明 |
|---|---|
| 阈值粗粒度 | 不同交易中心 load_type 数量差异大（安徽 6/7、广东 18/20），4~20 对各中心宽严不一 |
| 无业务语义 | 阈值不知道"该有多少个 load_type"是合理的 |
| 无法定位问题 | 只能告诉"4~20 范围外"，不能告诉"哪个 load_type 缺/超" |
| 配置未利用 | JSON 里已配 `load_type` 列表（13 中心全覆盖），但代码完全没读 |

### 1.2 目标

- 升级为按 `load_type` 维度的**覆盖度校验**
- 缺失（应有未有）= ❌ 硬失败
- 超出（不应有却有）= ⚠️ 软提示
- 配置缺失（未配/空）= ⚙️ 跳过 + 单独统计

### 1.3 范围

| 范围 | 说明 |
|---|---|
| **作用数据类型** | 仅 `网侧预测`、`网侧实际`（其他类型保持原样） |
| **作用窗口** | 沿用现有 10 天窗口（匹配日期往前推 9 天） |
| **配置文件** | `数据中心类型定义am.json`、`数据中心类型定义pm.json`（两份 load_type 字段完全一致） |
| **影响模块** | 校验核心 + 报告 + 飞书通知 + 文档 |

---

## 2. 核心设计

### 2.1 5 状态判定

| 状态 | 触发条件 | 校验行为 | 表格"数据量"列 | 详情节 | 计数 |
|---|---|---|---|---|---|
| **A. 暂未接入** | `time_config.备注 == "暂未接入"` | 整行跳过 | （整行不出现） | 警告详情 | ⚠️+1 |
| **B. 中心未配 `load_type`** | `'load_type' not in center_config` | 跳过覆盖度校验 | `**交易中心没配load_type**` | 配置缺失详情 | ⚙️+1 |
| **C. 类型 key 缺失** | `data_type not in center_config['load_type']` | 跳过覆盖度校验 | `**未配置该类型标准**` | 配置缺失详情 | ⚙️+1 |
| **D. 标准为空** | `center_config['load_type'][data_type] == []` | 跳过覆盖度校验 | `**标准为空**` | 配置缺失详情 | ⚙️+1 |
| **E. 有标准且非空** | 正常 | 跑覆盖度校验 | 简版 | 失败/警告详情 | ❌/⚠️+1 |

**关键差异**：
- 状态 A 整行**不出现**在表格中（暂未接入无数据可校验）
- 状态 A 在**警告详情**列出（让维护者知道哪些类型暂未接入）
- 状态 B/C/D **仍出现**在表格中（加粗提示），在**配置缺失详情**列出
- 状态 E 正常显示，缺→失败详情，超→警告详情

### 2.2 缺失 / 超出 / 命中的定义

```
标准集合   S = JSON 配置的 load_type 列表
实际集合   A_d = 第 d 天数据库返回的 load_type 集合
实际并集   A = ∪ A_d  for d in 10_days

缺失 = S - A_并   （标准有 ∩ 实际没有）
超出 = A_并 - S   （实际有 ∩ 标准没有）
命中 = A_并 ∩ S   （实际有 ∩ 标准有）
```

### 2.3 load-type-day 覆盖率算法

**核心思想**：把 10 天 × N 个标准 = N×10 个 **load_type-day 单位**，每个单位独立判断"有/无"。

```python
M = window_days × |S|                    # 总单位数 = 60 (10×6)
N = Σ |A_d ∩ S|   for d in 10_days      # 10 天累计命中单位数
命中率 = N / M
```

**示例验证**（用户原始例子）：

> 假设 10 天，有 8 天缺 2 个、2 天缺 3 个，标准是每天 6 个

```
M = 10 × 6 = 60
N = 8 × (6-2) + 2 × (6-3) = 8×4 + 2×3 = 32 + 6 = 38
命中率 = 38/60 ≈ 63.3%
显示：命中 38/60
```

**为什么不取"并集"算法**：

| 算法 | 10天里1天完整 + 9天全无数据 | 问题 |
|---|---|---|
| 并集 ∩ 标准 | 命中 6/6 (100%) | 掩盖另 9 天问题 |
| 缺失反推 | 命中 4/6 (67%) | 反映"10 天里有 4 个标准出现过"，但忽略"哪几天缺" |
| **load-type-day** | **命中 6/60 (10%)** | 精确反映"10 天里 60 个单位只 6 个有" |

**超出对命中不影响**：

```
某天 actual = {3, 4, 5, 6, 7, 8}，S = {1, 2, 3, 4, 5, 6}
命中单位 = |A ∩ S| = |{3,4,5,6}| = 4    ← 不受 {7,8} 影响
超出单位 = |A - S| = |{7,8}| = 2         ← 单独计警告
```

### 2.4 三桶收集

`_check_single_center` 返回值新增 3 个桶：

```python
{
    'passed': [...],          # 最新数据时间通过
    'failed': [...],          # load_type 缺失
    'warnings': [...],        # load_type 超出 + 暂未接入
    'config_missing': [...],  # 配置缺失（B/C/D）
}
```

| 桶 | 触发 | 进入条件 |
|---|---|---|
| `passed` | 最新数据时间验证通过 | 命中预期日期 |
| `failed` | 缺失 load_type | 状态 E 且 `has_missing` |
| `warnings` | 超出 load_type / 暂未接入 | 状态 A 或 状态 E 且 `has_extra` |
| `config_missing` | 配置缺失 | 状态 B / C / D |

---

## 3. 数据结构

### 3.1 CoverageResult（覆盖度校验结果）

```python
CoverageResult = {
    'status': 'A' | 'B' | 'C' | 'D' | 'E',   # 5 状态
    'expected_count': 6,                      # |S|，每天标准数
    'window_days': 10,                        # 窗口天数
    'total_units': 60,                        # window_days × expected_count
    'hit_units': 38,                          # Σ |A_d ∩ S|，10 天累计命中
    'hit_rate_text': '38/60',                 # 报告渲染用
    'missing_union': [1, 2],                  # 10 天 missing 并集
    'extra_union': [7, 8],                    # 10 天 extra 并集
    'missing_days': {                         # 按天展开 {date_str: [load_type, ...]}
        '06-01': [1, 2],
        '06-03': [1, 2],
        '06-05': [2],
    },
    'extra_days': {
        '06-01': [7],
        '06-03': [7, 8],
        '06-04': [7],
    },
    'missing_day_count': 3,                   # 出现缺失的天数
    'extra_day_count': 3,                     # 出现超出的天数
    'has_missing': True,                      # 决定是否进 failed
    'has_extra': True,                        # 决定是否进 warnings
    'error_msg': None,                        # SQL 异常时填
}
```

### 3.2 run_check 返回值（新增 2 个计数）

```python
{
    'exec_time': '2026-06-17 17:15:28',
    'pass_count': 70,
    'fail_count': 5,               # load_type 缺失
    'warn_count': 5,               # load_type 超出 + 暂未接入
    'config_missing_count': 0,     # 配置缺失
    'centers': [...],
    'report_file': 'output/...',
}
```

---

## 4. 报告渲染

### 4.1 主表格"数据量"列

按数据类型分两类渲染：

#### 4.1.1 网侧预测 / 网侧实际（覆盖度简版）

| 情况 | 显示 |
|---|---|
| 全过 | `✅` |
| 只缺 | `❌ 缺 [1, 2] (3天)` |
| 只超 | `⚠️ 超 [7, 8] (3天)` |
| 缺+超 | `❌ 缺 [1, 2] (3天) ⚠️ 超 [7, 8] (3天)` |
| 10 天全无数据 | `⏭️ 本月无数据` |
| 配置缺失 | `**交易中心没配load_type**` / `**未配置该类型标准**` / `**标准为空**` |
| SQL 异常 | `❌ 查询异常: {msg}` |
| 暂未接入 | （**整行不出现**） |

> 简版**保持原样**（用户决策：不动）。详版才用详细描述。

#### 4.1.2 其他 8 种类型（10 天总条数）

8 种类型：日前节点电价、实时节点电价、日前结算电价、实时结算电价、日前成交电量、代理用户用电明细、代理用户用电总计、明细与总计差异

| 情况 | 显示 | 计数影响 |
|---|---|---|
| 正常 | `10 天 N 条` | 不影响 pass/fail 桶 |
| N = 0 | `10 天 0 条` | 不影响 pass/fail 桶（**仅显示**） |
| SQL 异常 | `❌ 查询异常: {msg}` | 不影响（最新数据时间校验已处理） |
| 暂未接入 | （**整行不出现**） | — |

> **关键**：
> - 10 天总条数**仅显示用**，**不进入** `pass_count` / `fail_count` / `warn_count` / `config_missing_count`
> - 最新数据时间校验**已经**处理了"数据滞后"等失败情况
> - 10 天 N 条是**辅助信息**，让维护者一眼看出"数据量是否健康"

### 4.2 汇总区（条件显示：✅ 永远显示，其余 3 项 = 0 时不展示）

```markdown
## 校验汇总

- ✅ 通过: 70
- ❌ 失败: 5
- ⚠️ 警告: 5
- ⚙️ 配置缺失: 0
```

**规则**：

| 项 | 条件 | 含义 |
|---|---|---|
| ✅ 通过 | **永远显示** | 通过项数（最新数据时间校验通过） |
| ❌ 失败 | `fail_count > 0` 才显示 | **综合失败数**（含最新数据时间、连续性、load_type 缺失等多类失败） |
| ⚠️ 警告 | `warn_count > 0` 才显示 | 软提示数（load_type 超出 + 暂未接入） |
| ⚙️ 配置缺失 | `config_missing_count > 0` 才显示 | 配置层面缺失（中心未配/标准为空） |

### 4.3 详情节（3 节都条件显示）

```markdown
### 失败详情
（条件：fail_count > 0）
- ❌ 广东 / 网侧预测（D） — 10天内 3 天 load_type 缺 [1, 2]，命中 4/6
  - 06-01 缺 [1, 2]
  - 06-03 缺 [1, 2]
  - 06-05 缺 [2]

### 警告详情
（条件：warn_count > 0）
- ⚠️ 广东 / 网侧预测（D） — 10天内 3 天 load_type 超 [7, 8]，命中 4/6
  - 06-01 超 [7, 8]
  - 06-03 超 [7, 8]
  - 06-04 超 [7]
- ⚠️ 贵州 / 网侧预测（D） — 暂未接入
- ⚠️ 贵州 / 网侧实际（D-2） — 暂未接入

### 配置缺失详情
（条件：config_missing_count > 0）
- ⚙️ 福建 / 网侧预测（D） — 交易中心没配load_type
- ⚙️ 江西 / 网侧实际（D-2） — 标准为空
```

**规则**：
- 3 节标题**统一简化**（不带括号说明）
- 描述里用 `load_type 缺` / `load_type 超` / 状态描述 自带语义
- **3 节都条件显示**：count = 0 时不输出该节
- 子项用 **2 空格缩进**（飞书 wiki 兼容）
- 按日期升序排列
- 缺+超同一天 → 在"失败详情"和"警告详情"里**各列一次**（不合并）
- 命中显示规则**失败/警告统一**：都展示 `命中 N/M`（**同一个值**，因为是同一覆盖率）

---

## 5. 流程时序图

```
_check_single_center (center_name, center_config, ...)
  │
  ├─ for each (data_type, time_config) in center_config:
  │    │
  │    ├─ [状态 A 判定] time_config.备注 == "暂未接入"
  │    │    └─ continue (整行跳过)
  │    │
  │    ├─ parse offsets → [D-N, D-N-1, ...]
  │    │
  │    ├─ check_latest_data()  →  # 最新数据时间
  │    │    ├─ 失败 → 记录 failed
  │    │    └─ 成功 → cont_start_date / cont_end_date
  │    │
  │    └─ if data_type in (网侧预测, 网侧实际):
  │         │
  │         ├─ [状态 B/C/D 判定] 解析 center.load_type
  │         │    ├─ 'load_type' not in cfg → 状态 B
  │         │    ├─ data_type not in cfg['load_type'] → 状态 C
  │         │    └─ cfg['load_type'][data_type] == [] → 状态 D
  │         │
  │         ├─ if 状态 B/C/D:
  │         │    ├─ rows.append({vol: '**...**'})
  │         │    └─ config_missing.append(...)
  │         │
  │         └─ else (状态 E):
  │              └─ check_load_type_coverage()
  │                   │
  │                   ├─ 按天归组 actual_d
  │                   ├─ 计算 hit_units, missing_union, extra_union
  │                   ├─ missing_days, extra_days (按天展开)
  │                   │
  │                   ├─ if has_missing:
  │                   │    └─ failed.append(按日期展开)
  │                   └─ if has_extra:
  │                        └─ warnings.append(按日期展开)
  │
  └─ return {passed, failed, warnings, config_missing, rows}

run_check()
  │
  ├─ 各中心并行执行 _check_single_center
  │
  ├─ 汇总:
  │    pass_count = len(passed)
  │    fail_count = len(failed)
  │    warn_count = len(warnings)  + 暂未接入条数
  │    config_missing_count = len(config_missing)
  │
  ├─ 调用 build_report_markdown(...)
  │    ├─ 主表格"数据量"列简版
  │    ├─ 汇总 4 计数（永远显示）
  │    └─ 详情节 3 节（条件显示）
  │
  └─ return 结构化结果
```

---

## 6. 代码改动清单

### 6.1 总览

| # | 文件 | 改动量 | 类型 |
|---|---|---|---|
| 1 | `scripts/data_validator.py` | 重写 ~110 行 | 核心 |
| 2 | `scripts/report_builder.py` | 重写 ~100 行 | 报告 |
| 3 | `scripts/feishu_notifier.py` | 改 ~20 行 | 飞书 |
| 4 | `SKILL.md` | 改 1 节 | 文档 |

### 6.2 `scripts/data_validator.py`

#### (a) 行 105-116 — `_DATA_TYPE_SQL_MAPPING`

注释更新（不改功能）：

```python
_DATA_TYPE_SQL_MAPPING = {
    '日前节点电价': {'sql': '日前节点电价.sql'},
    '实时节点电价': {'sql': '实时节点电价.sql'},
    '日前结算电价': {'sql': '日前结算电价.sql'},
    '实时结算电价': {'sql': '实时结算电价.sql'},
    # 网侧预测/网侧实际：触发 load_type 覆盖度校验
    '网侧预测': {'sql': '网侧预测.sql', 'check_coverage': True},
    '网侧实际': {'sql': '网侧实际.sql', 'check_coverage': True},
    '日前成交电量': {'sql': '日前成交电量.sql'},
    '代理用户用电明细': {'sql': '代理用户用电明细.sql'},
    '代理用户用电总计': {'sql': '代理用户用电总计.sql'},
    '代理用户用电明细与代理用户用电总计差异': {'sql': '代理用户用电明细与代理用户用电总计差异.sql'},
}
```

#### (b) 行 279-324 — `check_data_volume` → `check_load_type_coverage`

```python
def check_load_type_coverage(
    conn, sql: str, expected_load_types: set, window_days: int = 10
) -> dict:
    """load_type 覆盖度校验（load-type-day 覆盖率算法）。

    返回 CoverageResult 字典。
    """
    expected_count = len(expected_load_types)
    total_units = window_days * expected_count

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

            if not rows:
                return {
                    'status': 'E',
                    'expected_count': expected_count,
                    'window_days': window_days,
                    'total_units': total_units,
                    'hit_units': 0,
                    'hit_rate_text': f'0/{total_units}',
                    'missing_union': sorted(expected_load_types),
                    'extra_union': [],
                    'missing_days': {},
                    'extra_days': {},
                    'missing_day_count': window_days,
                    'extra_day_count': 0,
                    'has_missing': True,
                    'has_extra': False,
                    'error_msg': None,
                }

            # 按天归组
            actual_by_day = {}  # {date_str: set(load_type)}
            for row in rows:
                date_val = _normalize_date(_extract_date(row))
                if date_val:
                    actual_by_day.setdefault(date_val, set()).add(row.get('load_type'))

            # 计算命中单位数（load-type-day 覆盖率）
            hit_units = 0
            actual_union = set()
            missing_days = {}
            extra_days = {}
            missing_day_count = 0
            extra_day_count = 0

            for date_str, actual_set in actual_by_day.items():
                actual_set.discard(None)  # 去掉 None
                # 强转 int → str
                actual_set = {str(x) for x in actual_set}
                expected_str = {str(x) for x in expected_load_types}

                hit_set = actual_set & expected_str
                hit_units += len(hit_set)
                actual_union |= actual_set

                missing = expected_str - actual_set
                extra = actual_set - expected_str
                if missing:
                    missing_days[date_str] = sorted(missing, key=lambda x: int(x) if x.isdigit() else x)
                    missing_day_count += 1
                if extra:
                    extra_days[date_str] = sorted(extra, key=lambda x: int(x) if x.isdigit() else x)
                    extra_day_count += 1

            missing_union = sorted(expected_load_types - actual_union, key=lambda x: int(x) if x.isdigit() else x)
            extra_union = sorted(actual_union - expected_load_types, key=lambda x: int(x) if x.isdigit() else x)

            return {
                'status': 'E',
                'expected_count': expected_count,
                'window_days': window_days,
                'total_units': total_units,
                'hit_units': hit_units,
                'hit_rate_text': f'{hit_units}/{total_units}',
                'missing_union': missing_union,
                'extra_union': extra_union,
                'missing_days': missing_days,
                'extra_days': extra_days,
                'missing_day_count': missing_day_count,
                'extra_day_count': extra_day_count,
                'has_missing': bool(missing_union),
                'has_extra': bool(extra_union),
                'error_msg': None,
            }
    except Exception as e:
        return {
            'status': 'E',
            'expected_count': expected_count,
            'window_days': window_days,
            'total_units': total_units,
            'hit_units': 0,
            'hit_rate_text': f'?/{total_units}',
            'missing_union': [],
            'extra_union': [],
            'missing_days': {},
            'extra_days': {},
            'missing_day_count': 0,
            'extra_day_count': 0,
            'has_missing': False,
            'has_extra': False,
            'error_msg': f'查询异常: {str(e)}',
        }
```

#### (c) 行 411-413 — 暂未接入处加显式注释

```python
if isinstance(time_config, dict):
    # 暂未接入：整行跳过 — 不进表格、不跑最新时间/连续性/覆盖度校验
    # 但在"警告详情"中列出（让维护者知道哪些类型暂未接入）
    if time_config.get('备注') == '暂未接入':
        warnings.append({
            'center': center_name,
            'data_type': f'{data_type_name}（{time_label}）',
            'check': {'type': 'not_connected', 'passed': True, 'message': '暂未接入'},
        })
        continue
    latest_time = time_config.get('最新数据时间', '—')
else:
    latest_time = time_config
```

#### (d) 行 472-519 — 数据量块改：4 状态分流 + 3 桶收集

```python
# === load_type 覆盖度校验（仅网侧预测/网侧实际）===
vol_status = None
type_meta = _DATA_TYPE_SQL_MAPPING.get(data_type_name, {})
if type_meta.get('check_coverage') and cont_start_date is not None:
    # 解析 center.load_type[data_type]
    load_type_map = center_config.get('load_type', {})
    expected = load_type_map.get(data_type_name) if isinstance(load_type_map, dict) else None

    # 状态 B/C/D 判定
    if expected is None or not isinstance(expected, list):
        # 状态 C：类型 key 缺失
        vol_status = '**未配置该类型标准**'
        config_missing.append({
            'center': center_name,
            'data_type': f'{data_type_name}（{time_label}）',
            'check': {'type': 'config_missing', 'passed': False, 'message': '未配置该类型标准'},
        })
    elif len(expected) == 0:
        # 状态 D：标准为空
        vol_status = '**标准为空**'
        config_missing.append({
            'center': center_name,
            'data_type': f'{data_type_name}（{time_label}）',
            'check': {'type': 'config_missing', 'passed': False, 'message': '标准为空'},
        })
    else:
        # 状态 E：跑覆盖度校验
        expected_set = set(int(x) for x in expected)
        volume_sql = render_sql(sql_template, trade_center_id, used_offset,
                                cont_start_date.strftime('%Y-%m-%d'),
                                cont_end_date.strftime('%Y-%m-%d'), vpp_id)
        coverage = _safe_query(conn, check_load_type_coverage, volume_sql, expected_set, 10)

        if coverage['error_msg']:
            vol_status = f"❌ {coverage['error_msg']}"
            failed.append({
                'center': center_name,
                'data_type': f'{data_type_name}（{time_label}）',
                'check': {'type': 'coverage_error', 'passed': False, 'error': coverage['error_msg']},
            })
        elif coverage['has_missing'] and coverage['has_extra']:
            vol_status = f"❌ 缺 [{', '.join(map(str, coverage['missing_union']))}] ({coverage['missing_day_count']}天) ⚠️ 超 [{', '.join(map(str, coverage['extra_union']))}] ({coverage['extra_day_count']}天)"
        elif coverage['has_missing']:
            vol_status = f"❌ 缺 [{', '.join(map(str, coverage['missing_union']))}] ({coverage['missing_day_count']}天)"
        elif coverage['has_extra']:
            vol_status = f"⚠️ 超 [{', '.join(map(str, coverage['extra_union']))}] ({coverage['extra_day_count']}天)"
        else:
            vol_status = "✅"

        # 失败详情（缺失）
        if coverage['has_missing']:
            failed.append({
                'center': center_name,
                'data_type': f'{data_type_name}（{time_label}）',
                'check': {
                    'type': 'coverage_missing',
                    'passed': False,
                    'hit_rate': coverage['hit_rate_text'],
                    'missing_union': coverage['missing_union'],
                    'missing_day_count': coverage['missing_day_count'],
                    'missing_days': coverage['missing_days'],
                },
            })

        # 警告详情（超出）
        if coverage['has_extra']:
            warnings.append({
                'center': center_name,
                'data_type': f'{data_type_name}（{time_label}）',
                'check': {
                    'type': 'coverage_extra',
                    'passed': True,
                    'hit_rate': coverage['hit_rate_text'],
                    'extra_union': coverage['extra_union'],
                    'extra_day_count': coverage['extra_day_count'],
                    'extra_days': coverage['extra_days'],
                },
            })
else:
    # 其他数据类型：数据量列保持 "—"
    if cont_start_date is None:
        vol_status = "—"
    else:
        vol_status = "—"

# 状态 B 判定（中心未配 load_type）
if vol_status is None and type_meta.get('check_coverage') and cont_start_date is not None:
    load_type_map = center_config.get('load_type', None)
    if load_type_map is None:
        vol_status = '**交易中心没配load_type**'
        config_missing.append({
            'center': center_name,
            'data_type': f'{data_type_name}（{time_label}）',
            'check': {'type': 'config_missing', 'passed': False, 'message': '交易中心没配load_type'},
        })

# === 其他 8 种数据类型：显示 10 天总条数（仅显示用，不进任何桶）===
if vol_status is None and not type_meta.get('check_coverage') and cont_start_date is not None:
    count_sql = render_sql(sql_template, trade_center_id, used_offset,
                          cont_start_date.strftime('%Y-%m-%d'),
                          cont_end_date.strftime('%Y-%m-%d'), vpp_id)
    row_count = _safe_query(conn, count_rows_in_window, count_sql)
    if row_count is None:
        vol_status = '❌ 查询异常'
    else:
        vol_status = f'10 天 {row_count} 条'
```

#### (d-extra) 新增 `count_rows_in_window` 函数

位置：在 `check_load_type_coverage` 函数之后、紧挨着定义。

```python
def count_rows_in_window(conn, sql: str) -> int | None:
    """查询 10 天窗口内的总行数（仅显示用，不进任何计数桶）。

    返回:
        int: 行数（≥ 0）
        None: 查询异常
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            return len(cursor.fetchall())
    except Exception:
        return None
```

**关键不变量**：
- `count_rows_in_window` **不进** `pass_count` / `fail_count` / `warn_count` / `config_missing_count`
- 8 种非网侧类型的"数据量"列**只显示**，不参与任何失败/警告判断
- 异常时显示 `❌ 查询异常`（同样不计数）
- 与 `check_latest_data` / `check_date_continuity` **完全独立**——多一次 SQL 查询，但走 `_ReconnectableConn` 复用连接

#### (e) 行 580-637 — `run_check` 增 `warn_count` / `config_missing_count`

```python
# 汇总
pass_count = len(results['passed'])
fail_count = len(results['failed'])
warn_count = len(results['warnings'])
config_missing_count = len(results['config_missing'])

# 返回结构化结果
return build_structured_result(
    results, center_results, str(report_file),
    exec_time=exec_time_str,
    pass_count=pass_count,
    fail_count=fail_count,
    warn_count=warn_count,
    config_missing_count=config_missing_count,
)
```

### 6.3 `scripts/report_builder.py`

#### (a) 主表格"数据量"列渲染

简版渲染逻辑（保持原样）：

```python
def render_volume_cell(vol_status):
    """vol_status 已是完整字符串，直接返回。"""
    return vol_status or '—'
```

#### (b) 汇总区渲染（条件显示：✅ 永远，❌/⚠️/⚙️ = 0 不展示）

```python
def render_summary(pass_count, fail_count, warn_count, config_missing_count):
    """汇总区：✅ 永远显示；其余 3 项 = 0 时不展示。"""
    lines = [
        '## 校验汇总',
        '',
        f'- ✅ 通过: {pass_count}',
    ]
    if fail_count > 0:
        lines.append(f'- ❌ 失败: {fail_count}')
    if warn_count > 0:
        lines.append(f'- ⚠️ 警告: {warn_count}')
    if config_missing_count > 0:
        lines.append(f'- ⚙️ 配置缺失: {config_missing_count}')
    return lines
```

#### (c) 详情节渲染（3 节条件显示）

```python
def render_failure_details(failed_list):
    """失败详情：condition = fail_count > 0"""
    if not failed_list:
        return []
    lines = ['### 失败详情', '']
    for f in failed_list:
        check = f['check']
        if check['type'] == 'coverage_missing':
            lines.append(f"- ❌ {f['center']} / {f['data_type']} — 10天内 {check['missing_day_count']} 天 load_type 缺 [{', '.join(map(str, check['missing_union']))}]，命中 {check['hit_rate']}")
            for date_str in sorted(check['missing_days'].keys()):
                lt_list = check['missing_days'][date_str]
                date_label = date_str[5:]  # '06-01'
                lines.append(f"  - {date_label} 缺 [{', '.join(map(str, lt_list))}]")
        else:
            # 其他失败类型（最新数据时间失败等）
            lines.append(f"- ❌ {f['center']} / {f['data_type']} — {check.get('error', check.get('message', '失败'))}")
    return lines


def render_warning_details(warnings_list):
    """警告详情：condition = warn_count > 0"""
    if not warnings_list:
        return []
    lines = ['### 警告详情', '']
    for w in warnings_list:
        check = w['check']
        if check['type'] == 'coverage_extra':
            lines.append(f"- ⚠️ {w['center']} / {w['data_type']} — 10天内 {check['extra_day_count']} 天 load_type 超 [{', '.join(map(str, check['extra_union']))}]，命中 {check['hit_rate']}")
            for date_str in sorted(check['extra_days'].keys()):
                lt_list = check['extra_days'][date_str]
                date_label = date_str[5:]
                lines.append(f"  - {date_label} 超 [{', '.join(map(str, lt_list))}]")
        elif check['type'] == 'not_connected':
            lines.append(f"- ⚠️ {w['center']} / {w['data_type']} — 暂未接入")
    return lines


def render_config_missing_details(config_missing_list):
    """配置缺失详情：condition = config_missing_count > 0"""
    if not config_missing_list:
        return []
    lines = ['### 配置缺失详情', '']
    for c in config_missing_list:
        check = c['check']
        msg = check.get('message', '配置缺失')
        # 配置缺失直接显示 message
        if msg == '交易中心没配load_type':
            display = '交易中心没配load_type'
        elif msg == '未配置该类型标准':
            display = '未配置该类型标准'
        elif msg == '标准为空':
            display = '标准为空'
        else:
            display = msg
        lines.append(f"- ⚙️ {c['center']} / {c['data_type']} — {display}")
    return lines
```

#### (d) `build_report_markdown` 整合

```python
def build_report_markdown(results, center_results, exec_time=None,
                          pass_count=0, fail_count=0,
                          warn_count=0, config_missing_count=0,
                          **kwargs):
    lines = []
    # ... 原有各中心主表格 ...
    # ... 汇总区 ...
    lines.extend(render_summary(pass_count, fail_count, warn_count, config_missing_count))
    # 详情节（条件显示）
    lines.extend(render_failure_details(results['failed']))
    lines.extend(render_warning_details(results['warnings']))
    lines.extend(render_config_missing_details(results['config_missing']))
    return '\n'.join(lines)
```

### 6.4 `scripts/feishu_notifier.py`

`build_card` 增 2 个字段：

```python
def build_card(result: dict, wiki_url: str = "", button_text: str = "📄 查看完整报告") -> dict:
    has_failures = result["fail_count"] > 0
    header_template = "red" if has_failures else "green"
    status_emoji = "❌" if has_failures else "✅"

    # 各中心摘要（保持原样）
    center_lines = []
    for c in result["centers"]:
        ...

    # 汇总区增 2 个字段
    summary_text = (
        f"**✅ 通过**：{result['pass_count']}  "
        f"**❌ 失败**：{result['fail_count']}  "
        f"**⚠️ 警告**：{result.get('warn_count', 0)}  "
        f"**⚙️ 配置缺失**：{result.get('config_missing_count', 0)}"
    )

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{status_emoji} RPA数据采集校验报告"},
            "template": header_template,
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**执行时间**：{result['exec_time']}"},
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": summary_text},
            },
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": center_md}},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": button_text},
                        "url": wiki_url,
                        "type": "primary",
                    }
                ],
            },
        ],
    }
    return card
```

### 6.5 `SKILL.md`

"3. 数据量合理性校验"小节改写为：

```markdown
## 3. 数据量合理性校验

**仅对网侧预测 / 网侧实际**两种数据类型启用，校验逻辑已升级为 **load_type 覆盖度校验**。

### 3.1 校验逻辑

以 JSON 配置 `center.load_type[data_type]` 为标准集合 S，10 天窗口内每天的数据库返回集合 A_d：

- **缺失** = S - A_并（标准有 ∩ 实际没有）→ ❌ 失败
- **超出** = A_并 - S（实际有 ∩ 标准没有）→ ⚠️ 警告
- **命中** = Σ |A_d ∩ S|，M = 10 × |S|，显示 `命中 N/M`

### 3.2 5 状态判定

| 状态 | 触发 | 处理 |
|---|---|---|
| A. 暂未接入 | `time_config.备注 == "暂未接入"` | 整行跳过，警告详情列出 |
| B. 中心未配 `load_type` | `'load_type' not in cfg` | 表格 `**交易中心没配load_type**` |
| C. 类型 key 缺失 | `data_type not in cfg['load_type']` | 表格 `**未配置该类型标准**` |
| D. 标准为空 | `cfg['load_type'][data_type] == []` | 表格 `**标准为空**` |
| E. 有标准且非空 | 正常 | 跑覆盖度校验 |

### 3.3 报告

- 主表格"数据量"列简版：`❌ 缺 [1, 2] (3天)` / `⚠️ 超 [7, 8] (3天)` 等
- 汇总 4 计数：✅ 通过 / ❌ 失败 / ⚠️ 警告 / ⚙️ 配置缺失
- 详情节 3 节（条件显示）：失败详情 / 警告详情 / 配置缺失详情
```

---

## 7. 验证

### 7.1 跑通 am.json + pm.json

```bash
# 默认 = pm.json
python .claude/skills/prod-rpa-checker/run_check.py

# 显式 am.json
python .claude/skills/prod-rpa-checker/run_check.py --config doc/数据中心类型定义am.json
```

**验证项**：
- [ ] 主表格"数据量"列：网侧预测/网侧实际显示简版覆盖度
- [ ] 主表格"数据量"列：8 种非网侧类型显示 `10 天 N 条`
- [ ] 暂未接入的（如贵州）**整行不出现** + **警告详情列出**
- [ ] 汇总 4 计数条件显示
- [ ] 详情节 3 节条件显示
- [ ] load_type 缺失/超出按日期展开
- [ ] 配置缺失（应无）不显示"### 配置缺失详情"

### 7.2 飞书 wiki 渲染

#### 关键发现（实测确认）

**飞书 `/descendant` API 限制**：`descendants ≤ 1000`（错误信息 `the max len is 1000`）。
改造前 987 blocks < 1000，单次调用无问题；改造后 1235 blocks > 1000，必须分批。

**飞书多次调用渲染顺序行为**：后调用的内容渲染**在上面**。
实测验证：分别测过 2 批、84 批，按 first_level 顺序切分都出现"失败/警告写到主表格上面"问题。

#### 解决：多日合并日期范围 + 调换两批顺序

**步骤 1：report_builder.py 多日合并日期范围**

`06-08 缺 [350]` + `06-09 缺 [350]` + ... + `06-17 缺 [350]` 合并为 `06-08~06-17 缺 [350]`。
减少 130+ 子项到 26 子项，减少 173 blocks（1235 → 1062）。

**步骤 2：wiki_updater.py 调换两批顺序**

`prepare_batches` 找包含 `### 校验汇总` 的 first_level 块作为分界点：
- **第一批（先调用）**：81 块 = 汇总 + 失败详情 + 警告详情 + 配置缺失详情
- **第二批（后调用）**：981 块 = 主表格

飞书渲染：第二批（后调用）→ 在上面 → **主表格在上** ✅
第一批（先调用）→ 在下面 → **汇总 + 失败 + 警告 + 配置缺失在下** ✅

#### 验证项

手动触发一次通知，验证：
- [ ] 飞书卡片显示 4 计数
- [ ] wiki 文档主表格 3 列表头正确
- [ ] **主表格在 wiki 上面**（后调用的第二批）
- [ ] **汇总 + 失败 + 警告 + 配置缺失在 wiki 下面**（先调用的第一批）
- [ ] 详情节多级缩进（2 空格）正确
- [ ] 多日合并日期范围：`06-08~06-17 缺 [350]` 正确显示
- [ ] emoji `❌⚠️⚙️` 正常渲染

---

## 8. 不变量

| 项 | 行为 |
|---|---|
| 4~20 条硬编码 | **彻底删除** |
| 校验范围 | 仅网侧预测 / 网侧实际 |
| 缺失 | ❌ 失败详情 / ❌+1 |
| 超出 | ⚠️ 警告详情 / ⚠️+1（**不计命中**） |
| 暂未接入 | ⚠️ 警告详情（不出现表格）/ ⚠️+1 |
| 配置缺失 | ⚙️ 配置缺失详情 / ⚙️+1 |
| 命中算法 | **load-type-day 覆盖率**（10 天累计 N/M） |
| 命中显示 | `命中 N/M`（失败/警告统一显示） |
| 主表格列名 | 保持"数据量" |
| 主表格内容 | 简版（不动） |
| 详版 | 按日期展开（2 空格缩进） |
| 缺+超同天 | 两节各列一次 |
| 详情节标题 | 全部简化（### 失败详情 / ### 警告详情 / ### 配置缺失详情） |
| 3 节显示 | **都条件显示**（count = 0 时不输出） |
| 汇总区 | ✅ 永远显示；❌/⚠️/⚙️ **条件显示**（= 0 时不输出） |
| 汇总区括号说明 | **都不带**（含义看 4.2 规则表的"含义"列） |
| 8 种非网侧类型"数据量" | 显示 `10 天 N 条`（**仅显示用，不进任何计数桶**） |
| 详版日期范围合并 | 多日缺/超相同 load_type 合并为 `06-08~06-17 缺 [350]`（**减少 ~173 blocks**） |
| 飞书 wiki 切分 | 找"### 校验汇总"作分界点，**第一批=汇总+失败+警告+配置缺失**（先调用）、**第二批=主表格**（后调用），飞书渲染后调用在上面 |
| am/pm 关系 | 不做元校验 |

---

## 9. 完整样例

### 9.0 主表格"数据量"列样例

```markdown
## 交易中心: 广东 (ID: 1)

| 数据类型 | 最新数据时间 | 数据量 | 日期连续性 |
| --- | --- | --- | --- |
| 日前节点电价（D-1）     | ✅ 2026-06-16 | 10 天 96 条   | ✅ 06-07~06-16 |
| 实时节点电价（D-3）     | ✅ 2026-06-14 | 10 天 288 条  | ✅ 06-04~06-14 |
| 日前结算电价（D-7）     | ✅ 2026-06-10 | 10 天 96 条   | ✅ 05-31~06-10 |
| 实时结算电价（D-7）     | ✅ 2026-06-10 | 10 天 288 条  | ✅ 05-31~06-10 |
| 网侧预测（D）           | ✅ 2026-06-16 | ❌ 缺 [1, 2] (3天) ⚠️ 超 [7, 8] (3天) | ✅ 06-07~06-16 |
| 网侧实际（D-3）         | ✅ 2026-06-14 | ✅ | ✅ 06-05~06-14 |
| 日前成交电量（D-1）     | ✅ 2026-06-16 | 10 天 10 条   | ✅ 06-07~06-16 |
| 代理用户用电明细（D-5） | ✅ 2026-06-12 | 10 天 50 条   | ✅ 06-02~06-12 |
| 代理用户用电总计（D-5） | ✅ 2026-06-12 | 10 天 5 条    | ✅ 06-02~06-12 |
| 代理用户用电明细与代理用户用电总计差异 | ✅ 明细与总计一致 | — | — |
```

> 关键点：
> - **8 种非网侧类型**的"数据量"列显示 `10 天 N 条`（N 是 10 天窗口内总行数）
> - **网侧预测/网侧实际**的"数据量"列显示简版覆盖度（缺/超/全过/配置缺失）
> - **暂未接入**的（如贵州网侧预测）**整行不出现**
> - **明细与总计差异**的"数据量"列保持 `—`（特殊处理）

### 9.1 报告最末（场景 1：所有计数都有值）

```markdown
## 校验汇总

- ✅ 通过: 50
- ❌ 失败: 3
- ⚠️ 警告: 5
- ⚙️ 配置缺失: 2

### 失败详情
- ❌ 广东 / 网侧预测（D） — 10天内 3 天 load_type 缺 [1, 2]，命中 38/60
  - 06-01 缺 [1, 2]
  - 06-03 缺 [1, 2]
  - 06-05 缺 [2]
- ❌ 江苏 / 网侧实际（D-2） — 10天内 5 天 load_type 缺 [103, 104, 105]，命中 5/10
  - 06-01 缺 [103, 104, 105]
  - 06-02 缺 [103]
  - 06-03 缺 [104]
  - 06-04 缺 [103, 104, 105]
  - 06-05 缺 [103]

### 警告详情
- ⚠️ 广东 / 网侧预测（D） — 10天内 3 天 load_type 超 [7, 8]，命中 38/60
  - 06-01 超 [7, 8]
  - 06-03 超 [7, 8]
  - 06-04 超 [7]
- ⚠️ 贵州 / 网侧预测（D） — 暂未接入
- ⚠️ 贵州 / 网侧实际（D-2） — 暂未接入

### 配置缺失详情
- ⚙️ 福建 / 网侧预测（D） — 交易中心没配load_type
- ⚙️ 江西 / 网侧实际（D-2） — 标准为空
```

### 9.2 报告最末（场景 2：只有失败）

```markdown
## 校验汇总

- ✅ 通过: 70
- ❌ 失败: 5

### 失败详情
- ❌ 广东 / 网侧预测（D） — 10天内 3 天 load_type 缺 [1, 2]，命中 38/60
  - 06-01 缺 [1, 2]
  - 06-03 缺 [1, 2]
  - 06-05 缺 [2]
（不输出 "### 警告详情" 和 "### 配置缺失详情"）
```

### 9.3 报告最末（场景 3：全过）

```markdown
## 校验汇总

- ✅ 通过: 80

（不输出任何详情节）
```

---

## 10. 任务清单

| # | 任务 | 状态 |
|---|---|---|
| 1 | 整理技术方案文档到 `doc/` 目录 | ✅ 完成 |
| 2 | 改 `data_validator.py`：新增 `check_load_type_coverage` + 4 状态分流 + 3 桶收集 | ⏳ pending |
| 3 | 改 `report_builder.py`：表格简版 + 4 计数 + 3 条件节 | ⏳ pending |
| 4 | 改 `feishu_notifier.py`：飞书卡片增 `warn_count` / `config_missing_count` | ⏳ pending |
| 5 | 改 `SKILL.md`："3. 数据量合理性校验"小节改写 | ⏳ pending |
| 6 | 验证：跑 `am.json` + `pm.json` | ⏳ pending |
| 7 | 验证：飞书 wiki 渲染 | ⏳ pending |
