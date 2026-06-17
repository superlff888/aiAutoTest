"""报告生成模块 — 将校验结果格式化为 Markdown 报告 + 结构化通知 dict

由 data_validator.py 的 run_check() 调用，职责：
1. build_report_markdown() — 生成 Markdown 表格 + 失败详情代码块
2. build_structured_result() — 构建飞书通知所需的结构化 dict
3. write_report_to_file() — 写入本地 .md 文件
4. _format_date_ranges() — 共享工具：将连续日期压缩为范围格式
"""

from datetime import datetime, timedelta


def _format_date_ranges(dates: list) -> str:
    """将连续日期压缩为范围格式，如 20260501~20260510"""
    if not dates:
        return ''
    sorted_dates = sorted(set(dates))
    ranges = []
    start = sorted_dates[0]
    prev = sorted_dates[0]
    for d in sorted_dates[1:]:
        prev_dt = datetime.strptime(prev, '%Y%m%d')
        curr_dt = datetime.strptime(d, '%Y%m%d')
        if (curr_dt - prev_dt).days == 1:
            prev = d
        else:
            if start == prev:
                ranges.append(start)
            else:
                ranges.append(f'{start}~{prev}')
            start = d
            prev = d
    if start == prev:
        ranges.append(start)
    else:
        ranges.append(f'{start}~{prev}')
    return '、'.join(ranges)


def _is_next_day(date1_str: str, date2_str: str) -> bool:
    """判断 date2 是否是 date1 的下一天。"""
    d1 = datetime.strptime(date1_str, '%Y-%m-%d')
    d2 = datetime.strptime(date2_str, '%Y-%m-%d')
    return (d2 - d1).days == 1


def _format_load_type_ranges(days_data: dict, verb: str = '缺') -> list:
    """将按天归组的 load_type 列表合并为日期范围。

    规则：多日缺/超相同的 load_type 时，合并为 06-07~06-11 缺 [94]
    - 输入：{date_str: [load_type, ...]}
    - 输出：格式化行列表，如 ['  - 06-08~06-17 缺 [350]', '  - 06-12~06-13 缺 [168, 513, 514]']

    例：
      输入：{'06-08': [350], '06-09': [350], '06-10': [350], '06-11': [350], '06-12': [1, 2], '06-13': [1, 2]}
      输出：['  - 06-08~06-11 缺 [350]', '  - 06-12~06-13 缺 [1, 2]']
    """
    if not days_data:
        return []

    # 按日期排序
    sorted_dates = sorted(days_data.keys())

    lines = []
    current_lt_tuple = None
    current_start_date = None
    current_end_date = None

    for date_str in sorted_dates:
        lt_list = days_data[date_str]
        lt_tuple = tuple(lt_list)

        if current_lt_tuple is None:
            # 第一组
            current_lt_tuple = lt_tuple
            current_start_date = date_str
            current_end_date = date_str
        elif lt_tuple == current_lt_tuple and _is_next_day(current_end_date, date_str):
            # 相同 load_type + 连续日期 → 合并
            current_end_date = date_str
        else:
            # 输出当前组
            lines.append(_format_range_line(current_start_date, current_end_date, current_lt_tuple, verb))
            # 开始新组
            current_lt_tuple = lt_tuple
            current_start_date = date_str
            current_end_date = date_str

    # 输出最后一组
    if current_lt_tuple is not None:
        lines.append(_format_range_line(current_start_date, current_end_date, current_lt_tuple, verb))

    return lines


def _format_range_line(start_date: str, end_date: str, lt_tuple: tuple, verb: str) -> str:
    """格式化单行：'- 06-08~06-17 缺 [350]' 或 '- 06-08 缺 [350]'"""
    if start_date == end_date:
        date_label = start_date[5:]  # '06-08'
    else:
        date_label = f'{start_date[5:]}~{end_date[5:]}'  # '06-08~06-17'
    lt_str = ', '.join(str(x) for x in lt_tuple)
    return f"  - {date_label} {verb} [{lt_str}]"


def build_report_markdown(results: dict, center_results: dict, exec_time: str = None,
                          warn_count: int = 0, config_missing_count: int = 0) -> str:
    """将校验结果构建为 Markdown 报告内容。

    Args:
        results: 校验结果 {'passed': [...], 'failed': [...], 'warnings': [...], 'config_missing': [...]}
        center_results: 按交易中心组织的结果
        exec_time: 执行时间戳，未提供时自动生成
        warn_count: 警告数（load_type 超出 + 暂未接入）
        config_missing_count: 配置缺失数
    """
    if exec_time is None:
        exec_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report_content = [
        f"**RPA数据采集校验报告**\n\n执行时间：{exec_time}",
    ]

    for center_name, cr in center_results.items():
        report_content.append(f"\n## 交易中心: {center_name} (ID: {cr['center_id']})")
        report_content.append('| 数据类型 | 最新数据时间 | 数据量 | 日期连续性 |')
        report_content.append('|----------|-------------|--------|-----------|')
        for r in cr['rows']:
            report_content.append(f"| {r['data_type']} | {r['latest']} | {r['volume']} | {r['continuity']} |")

    report_content.append(f"\n---\n\n## 校验汇总\n\n执行时间：{exec_time}")
    pass_count = len({(p['center'], p['data_type']) for p in results.get('passed', [])})
    fail_count = len({(f['center'], f['data_type']) for f in results.get('failed', [])})
    report_content.append(f"- ✅ 通过: {pass_count}")
    if fail_count > 0:
        report_content.append(f"- ❌ 失败: {fail_count}")
    if warn_count > 0:
        report_content.append(f"- ⚠️ 警告: {warn_count}")
    if config_missing_count > 0:
        report_content.append(f"- ⚙️ 配置缺失: {config_missing_count}")

    # 失败详情（条件显示：fail_count > 0）
    if results.get('failed'):
        report_content.append("\n### 失败详情\n")
        for fail in results['failed']:
            check = fail['check']
            ctype = check.get('type', '')
            if ctype == 'coverage_missing':
                miss = ', '.join(str(x) for x in check.get('missing_union', []))
                report_content.append(
                    f"- ❌ {fail['center']} / {fail['data_type']} — 10天内 {check.get('missing_day_count', 0)} 天 load_type 缺 [{miss}]，命中 {check.get('hit_rate', '?')}"
                )
                # 按日期范围合并：多日缺相同 load_type 合并为 06-07~06-11 缺 [94]
                for sub_line in _format_load_type_ranges(check.get('missing_days', {}), verb='缺'):
                    report_content.append(sub_line)
            else:
                # 其他失败类型（最新数据时间失败、覆盖度异常等）
                msg = check.get('error', '未知错误')
                report_content.append(f"- ❌ {fail['center']} / {fail['data_type']} — {msg}")

    # 警告详情（条件显示：warn_count > 0）
    if results.get('warnings'):
        report_content.append("\n### 警告详情\n")
        for w in results['warnings']:
            check = w['check']
            ctype = check.get('type', '')
            if ctype == 'coverage_extra':
                ext = ', '.join(str(x) for x in check.get('extra_union', []))
                report_content.append(
                    f"- ⚠️ {w['center']} / {w['data_type']} — 10天内 {check.get('extra_day_count', 0)} 天 load_type 超 [{ext}]，命中 {check.get('hit_rate', '?')}"
                )
                for sub_line in _format_load_type_ranges(check.get('extra_days', {}), verb='超'):
                    report_content.append(sub_line)
            elif ctype == 'not_connected':
                report_content.append(f"- ⚠️ {w['center']} / {w['data_type']} — 暂未接入")

    # 配置缺失详情（条件显示：config_missing_count > 0）
    if results.get('config_missing'):
        report_content.append("\n### 配置缺失详情\n")
        for c in results['config_missing']:
            check = c['check']
            msg = check.get('message', '配置缺失')
            report_content.append(f"- ⚙️ {c['center']} / {c['data_type']} — {msg}")

    return '\n'.join(report_content) + '\n'


def build_structured_result(results: dict, center_results: dict, report_file: str,
                            exec_time: str = None,
                            warn_count: int = 0, config_missing_count: int = 0) -> dict:
    """将 run_check 的 (results, center_results) 构建为飞书通知所需的结构化 dict。

    Args:
        results: 校验结果
        center_results: 按交易中心组织的结果
        report_file: 报告文件路径
        exec_time: 执行时间戳，未提供时自动生成
        warn_count: 警告数
        config_missing_count: 配置缺失数
    """
    if exec_time is None:
        exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 去重统计 pass/fail（同一 data_type 可能因 volume/continuity 产生多条 failed）
    seen_passed = set()
    for p in results.get("passed", []):
        seen_passed.add((p["center"], p["data_type"]))

    seen_failed = set()
    for f in results.get("failed", []):
        seen_failed.add((f["center"], f["data_type"]))

    pass_count = len(seen_passed)
    fail_count = len(seen_failed)

    # 按交易中心组织
    centers = []
    all_center_names = list(center_results.keys())
    for cname in all_center_names:
        center_fails = [f for f in results.get("failed", []) if f["center"] == cname]
        unique_fail_dts = {(f["data_type"],) for f in center_fails}
        all_pass = len(unique_fail_dts) == 0

        failures = []
        for f in center_fails:
            check = f["check"]
            ctype = check.get("type", "latest")
            msg = check.get("error", "")
            if not msg:
                if ctype == "coverage_missing":
                    miss = ', '.join(str(x) for x in check.get('missing_union', []))
                    msg = f"load_type 缺 [{miss}]，命中 {check.get('hit_rate', '?')}"
                elif ctype == "coverage_error":
                    msg = f"覆盖度查询异常: {check.get('error', '')}"
            failures.append({
                "data_type": f["data_type"],
                "offset": check.get("offset", "—"),
                "message": msg,
            })

        centers.append({
            "name": cname,
            "trade_center_id": center_results[cname]["center_id"],
            "all_pass": all_pass,
            "failures": failures,
        })

    return {
        "exec_time": exec_time,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "config_missing_count": config_missing_count,
        "centers": centers,
        "report_file": report_file,
    }


def write_report_to_file(report_file, md_text: str, outfile=None):
    """将报告内容写入文件，同时支持附加输出句柄。"""
    with open(report_file, 'w', encoding='utf-8') as _f:
        _f.write(md_text)
    if outfile is not None:
        outfile.write(md_text)
        outfile.flush()
