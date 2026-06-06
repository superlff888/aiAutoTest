"""报告生成模块 — 将校验结果格式化为 Markdown 报告 + 结构化通知 dict

由 data_validator.py 的 run_check() 调用，职责：
1. build_report_markdown() — 生成 Markdown 表格 + 失败详情代码块
2. build_structured_result() — 构建飞书通知所需的结构化 dict
3. write_report_to_file() — 写入本地 .md 文件
4. _format_date_ranges() — 共享工具：将连续日期压缩为范围格式
"""

from datetime import datetime


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


def build_report_markdown(results: dict, center_results: dict, exec_time: str = None) -> str:
    """将校验结果构建为 Markdown 报告内容。

    Args:
        results: 校验结果 {'passed': [...], 'failed': [...]}
        center_results: 按交易中心组织的结果
        exec_time: 执行时间戳，未提供时自动生成
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
    report_content.append(f"- ✅ 通过: {len(results['passed'])}")
    report_content.append(f"- ❌ 失败: {len(results['failed'])}")

    if results['failed']:
        report_content.append("\n**失败详情**：\n")
        report_content.append("```")
        for fail in results['failed']:
            check = fail['check']
            ctype = check.get('type', '')
            if ctype == 'continuity':
                missing = ', '.join(check.get('missing_dates', []))
                report_content.append(f"❌ {fail['center']} | {fail['data_type']} - 日期不连续: 缺失 {missing}")
            elif ctype == 'volume':
                report_content.append(f"❌ {fail['center']} | {fail['data_type']} - 数据量: {check['error']}")
            else:
                report_content.append(f"❌ {fail['center']} | {fail['data_type']} (offset={check.get('offset', '?')}) - {check.get('error', '未知错误')}")
        report_content.append("```")

    return '\n'.join(report_content) + '\n'


def build_structured_result(results: dict, center_results: dict, report_file: str, exec_time: str = None) -> dict:
    """将 run_check 的 (results, center_results) 构建为飞书通知所需的结构化 dict。

    Args:
        results: 校验结果
        center_results: 按交易中心组织的结果
        report_file: 报告文件路径
        exec_time: 执行时间戳，未提供时自动生成
    """
    if exec_time is None:
        exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 去重统计 pass/fail（同一 data_type 可能因 volume/continuity 产生多条 failed）
    seen_passed = set()
    for p in results["passed"]:
        seen_passed.add((p["center"], p["data_type"]))

    seen_failed = set()
    for f in results["failed"]:
        seen_failed.add((f["center"], f["data_type"]))

    pass_count = len(seen_passed)
    fail_count = len(seen_failed)

    # 按交易中心组织
    centers = []
    all_center_names = list(center_results.keys())
    for cname in all_center_names:
        center_fails = [f for f in results["failed"] if f["center"] == cname]
        center_passes = [p for p in results["passed"] if p["center"] == cname]
        unique_fail_dts = {(f["data_type"],) for f in center_fails}
        unique_pass_dts = {(p["data_type"],) for p in center_passes}
        all_pass = len(unique_fail_dts) == 0

        failures = []
        for f in center_fails:
            check = f["check"]
            ctype = check.get("type", "latest")
            msg = check.get("error", "")
            if not msg:
                if ctype == "continuity":
                    missing = ", ".join(check.get("missing_dates", [])[:3])
                    msg = f"日期不连续: 缺失 {missing}"
                elif ctype == "volume":
                    msg = f"数据量异常: {check.get('error', '')}"
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
