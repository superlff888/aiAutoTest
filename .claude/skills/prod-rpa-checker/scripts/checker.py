#!/usr/bin/env python3
"""
RPA数据采集完整性校验脚本

功能：
1. 最新数据时间验证：根据JSON配置验证数据是否采集到最新
2. 日期连续性验证：验证指定时间范围内每一天的数据都存在
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from db_executor import get_connections, resolve_conn, get_connection

# ─── MySQL 连接断开错误码 ───
_CONNECTION_ERRORS = (2006, 2013, 2055)


class _ReconnectableConn:
    """透明重连包装器：捕获 OperationalError 2006/2013 时自动重建连接并重试。"""

    def __init__(self, conn_cm, connection_name: str):
        # conn_cm 是 context manager，__enter__ 返回真实连接
        self._conn_cm = conn_cm
        self._conn = conn_cm.__enter__()
        self._connection_name = connection_name

    def cursor(self):
        return self._conn.cursor()

    def _reconnect(self):
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = _get_conn(self._connection_name).__enter__()

    def close(self):
        self._conn.close()
        try:
            self._conn_cm.__exit__(None, None, None)
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._conn, name)


def _is_connection_error(e: Exception) -> bool:
    """判断是否为 MySQL 连接断开错误（2006/2013/2055）。"""
    code = getattr(e, 'args', [None])[0]
    if isinstance(code, int) and code in _CONNECTION_ERRORS:
        return True
    msg = str(e).lower()
    return any(k in msg for k in ('mysql server has gone away', 'lost connection', 'broken pipe'))


def _safe_query(conn: _ReconnectableConn, func, *args, **kwargs):
    """执行数据库查询函数，连接断开时自动重连并重试一次。"""
    try:
        return func(conn, *args, **kwargs)
    except Exception as e:
        if _is_connection_error(e):
            conn._reconnect()
            return func(conn, *args, **kwargs)
        raise


_DATA_TYPE_SQL_MAPPING = {
    '日前节点电价': '日前节点电价.sql',
    '实时节点电价': '实时节点电价.sql',
    '日前结算电价': '日前结算电价.sql',
    '实时结算电价': '实时结算电价.sql',
    '网侧预测': '网侧预测.sql',
    '网侧实际': '网侧实际.sql',
    '日前成交电量': '日前成交电量.sql',
    '代理用户用电明细': '代理用户用电明细.sql',
    '代理用户用电总计': '代理用户用电总计.sql',
    '代理用户用电明细与代理用户用电总计差异': '代理用户用电明细与代理用户用电总计差异.sql',
    # '中长期持仓' — 已跳过，不需要 SQL 模板
}

_DATE_FIELDS = ['day', 'date', 'time', 'data_date', 'stat_date']


def _get_conn(connection_name: str):
    cfg = get_connections()
    conn_info = resolve_conn(cfg, connection_name)
    return get_connection(conn_info)


def load_data_center_config(config_path: str) -> dict:
    """加载数据中心类型定义JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_sql_templates(sql_dir: Path) -> dict:
    """预加载所有SQL模板到内存，避免重复IO"""
    templates = {}
    for dtype, sql_file in _DATA_TYPE_SQL_MAPPING.items():
        sql_path = sql_dir / sql_file
        if sql_path.exists():
            templates[dtype] = sql_path.read_text(encoding='utf-8')
    return templates


def parse_offset_days(time_str: str) -> list:
    """将D加减时间转换为offset_days列表"""
    offsets = []
    for tv in time_str.split('/'):
        tv = tv.strip()
        if tv == 'D':
            offsets.append(0)
        elif tv.startswith('D-'):
            offsets.append(int(tv[2:]))
        elif tv.startswith('D+'):
            offsets.append(-int(tv[2:]))
        else:
            raise ValueError(f"无效的日期偏移格式: {tv!r}，应为 D/D-N/D+N 格式")
    return offsets


def _compute_expected_date(offset_days: int) -> datetime:
    return datetime.now() + timedelta(days=-offset_days)


def render_sql(sql_template: str, trade_center_id: str, offset_days: int,
               start_date: str, end_date: str, vpp_id: str = '1') -> str:
    return sql_template.replace('{{trade_center_id}}', str(trade_center_id)) \
                       .replace('{{offset_days}}', str(offset_days)) \
                       .replace('{{vpp_id}}', vpp_id) \
                       .replace('{{start_date}}', start_date) \
                       .replace('{{end_date}}', end_date)


def _extract_date(row: dict):
    for field in _DATE_FIELDS:
        if field in row and row[field] is not None:
            return row[field]
    return None


def _normalize_date(date_val) -> str | None:
    if date_val is None:
        return None
    if isinstance(date_val, datetime):
        return date_val.strftime('%Y-%m-%d')
    if isinstance(date_val, str):
        if '-' in date_val:
            return date_val[:10]
        return date_val[:4] + '-' + date_val[4:6] + '-' + date_val[6:8]
    if hasattr(date_val, 'strftime'):
        return date_val.strftime('%Y-%m-%d')
    if isinstance(date_val, int):
        s = str(date_val)
        return s[:4] + '-' + s[4:6] + '-' + s[6:8]
    return None


def check_latest_data(conn, sql_template: str, trade_center_id: str,
                      offsets: list, vpp_id: str = '1') -> tuple:
    """检查最新数据时间，支持多offset降级查询。复用数据库连接。"""
    fallback_log = []
    for i, offset in enumerate(offsets):
        expected_date = _compute_expected_date(offset)
        start_str = (expected_date - timedelta(days=9)).strftime('%Y-%m-%d')
        end_str = expected_date.strftime('%Y-%m-%d')
        sql = render_sql(sql_template, trade_center_id, offset, start_str, end_str, vpp_id)

        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

                if not rows:
                    fallback_log.append(f"{expected_date.strftime('%Y-%m-%d')}({offset}) 无数据")
                    if i == len(offsets) - 1:
                        range_start_date = expected_date - timedelta(days=9)
                        return False, offset, None, f"近10天无数据 ({range_start_date.strftime('%Y-%m-%d')}~{expected_date.strftime('%Y-%m-%d')})", fallback_log
                    continue

                max_date = _normalize_date(_extract_date(rows[0]))
                if max_date is None:
                    fallback_log.append(f"{expected_date.strftime('%Y-%m-%d')}({offset}) 无法获取日期字段")
                    if i == len(offsets) - 1:
                        return False, offset, None, "无法获取日期字段", fallback_log
                    continue

                expected_str = expected_date.strftime('%Y-%m-%d')
                if max_date == expected_str:
                    if fallback_log:
                        fallback_log.append(f"✅ 降级成功: {max_date} (offset={offset})")
                    return True, offset, max_date, None, fallback_log
                else:
                    error = f"预期 {expected_str}，实际 {max_date}"
                    fallback_log.append(error)
                    if i == len(offsets) - 1:
                        return False, offset, max_date, error, fallback_log
                    continue  # 日期不符，降级到下一个offset
        except Exception as e:
            error = f"查询异常 (offset={offset}): {str(e)}"
            fallback_log.append(error)
            if i == len(offsets) - 1:
                return False, offset, None, error, fallback_log
            continue


def check_data_volume(conn, sql: str) -> tuple:
    """检查每日数据条数是否在 4~20 条范围内"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            count = len(rows)

            if not rows:
                return False, count, 0, "无数据"

            # 按日期分组统计，收集所有load_type
            date_counts = {}
            date_load_types = {}
            for row in rows:
                date_val = _normalize_date(_extract_date(row))
                if date_val:
                    date_counts[date_val] = date_counts.get(date_val, 0) + 1
                    load_type = row.get('load_type')
                    if load_type is not None:
                        if date_val not in date_load_types:
                            date_load_types[date_val] = set()
                        date_load_types[date_val].add(str(load_type))

            if not date_counts:
                return False, count, 0, "无法获取日期字段"

            # 检查每天数据量
            abnormal_days = []
            for date_str, day_count in sorted(date_counts.items()):
                if day_count < 4 or day_count > 20:
                    lt_set = date_load_types.get(date_str)
                    if lt_set:
                        lt_str = '、'.join(sorted(lt_set))
                    else:
                        lt_str = '无'
                    abnormal_days.append((date_str, day_count, lt_str))

            if abnormal_days:
                details = '；'.join(f'{d}(load_type={lt}): {c}条' for d, c, lt in abnormal_days[:5])
                if len(abnormal_days) > 5:
                    details += f' 等{len(abnormal_days)}天'
                return False, count, len(date_counts), f'{len(abnormal_days)}天数据量异常: {details}'
            return True, count, len(date_counts), f"正常(日均{count/len(date_counts):.0f}条)"
    except Exception as e:
        return False, 0, 0, f"数据量检查异常: {str(e)}"


def check_date_continuity(conn, sql: str, start_date: datetime, end_date: datetime) -> tuple:
    """复用数据库连接检查日期连续性，复用 _normalize_date/_extract_date 统一逻辑"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

            existing_dates = set()
            for row in rows:
                ds = _normalize_date(_extract_date(row))
                if ds is not None:
                    existing_dates.add(ds)

            missing_dates = []
            current = start_date
            while current <= end_date:
                ds = current.strftime('%Y-%m-%d')
                if ds not in existing_dates:
                    missing_dates.append(ds)
                current += timedelta(days=1)

            if missing_dates:
                return False, missing_dates, f"缺失 {len(missing_dates)} 天"
            return True, [], None
    except Exception as e:
        return False, [], f"查询异常: {str(e)}"


def _format_date_ranges(dates: list) -> str:
    """将连续日期压缩为范围格式，如 20260501~20260510"""
    if not dates:
        return ''
    # 排序去重
    sorted_dates = sorted(set(dates))
    ranges = []
    start = sorted_dates[0]
    prev = sorted_dates[0]
    for d in sorted_dates[1:]:
        # 比较日期是否连续（相差1天）
        prev_dt = datetime.strptime(prev, '%Y%m%d')
        curr_dt = datetime.strptime(d, '%Y%m%d')
        if (curr_dt - prev_dt).days == 1:
            prev = d
        else:
            if start == prev:
                ranges.append(start)
            else:
                ranges.append(f'{start}～{prev}')
            start = d
            prev = d
    # 收尾 — 统一使用半角 ~
    if start == prev:
        ranges.append(start)
    else:
        ranges.append(f'{start}～{prev}')
    return '、'.join(ranges)


def _check_diff(conn, sql: str) -> str:
    """检查代理用户用电明细与代理用户用电总计的差异，复用连接"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                return "✅ diff=0"
            diff_dates = []
            for row in rows:
                diff_val = row.get('diff_energy', 0)
                try:
                    diff_val = abs(float(diff_val))
                except (ValueError, TypeError):
                    diff_val = 0
                if diff_val > 0.01:
                    # 尝试多种可能的列名
                    date_key = row.get('time') or row.get('day') or row.get('date') or row.get('data_date') or '?'
                    diff_dates.append(str(date_key))
            if not diff_dates:
                return "✅ diff=0"
            date_summary = _format_date_ranges(diff_dates)
            return f"❌ diff={len(diff_dates)}，{date_summary}"
    except Exception as e:
        return f"❌ 查询异常: {str(e)}"


def run_check(connection: str = "prod", config_path: str | None = None,
              trade_center: str = None, data_type: str = None,
              start_date: str = None, end_date: str = None,
              outfile=None):
    """执行完整校验，返回结构化结果。

    Args:
        connection: 数据库连接名称（prod/test）
        config_path: 数据中心配置 JSON 路径（None 时自动定位）
        trade_center: 指定交易中心名称
        data_type: 指定数据类型
        start_date: 起始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        outfile: 可选，报告内容写入该文件句柄

    返回:
    {
        "exec_time": "2026-06-04 17:10:28",
        "pass_count": int,
        "fail_count": int,
        "centers": [
            {"name": "广东", "trade_center_id": 1, "all_pass": False,
             "failures": [{"data_type": "...", "offset": "D", "message": "..."}, ...]},
            ...
        ],
        "report_file": "output/rpa_check_report_20260604171028.md"
    }
    """
    # 自动定位 config_path
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "doc" / "数据中心类型定义.json")
    config_path = Path(config_path) if not isinstance(config_path, Path) else config_path

    config = load_data_center_config(str(config_path))
    sql_dir = config_path.parent.parent / 'sqls'
    templates = load_sql_templates(sql_dir)

    results = {'passed': [], 'failed': []}
    center_results = {}

    conn = _ReconnectableConn(_get_conn(connection), connection)
    try:
        for center_name, center_config in config.items():
            if trade_center and trade_center != center_name:
                continue

            trade_center_id = center_config.get('trade_center_id')
            if not trade_center_id:
                continue

            vpp_id = center_config.get('vpp_id', '1')
            rows = []

            for data_type_name, time_config in center_config.items():
                if data_type_name in ('trade_center_id', 'vpp_id', '中长期持仓'):
                    continue

                if data_type and data_type != data_type_name:
                    continue

                if isinstance(time_config, dict):
                    if time_config.get('备注') == '暂未接入':
                        continue
                    latest_time = time_config.get('最新数据时间', '—')
                else:
                    latest_time = time_config

                if latest_time == '—':
                    continue

                time_str = '/'.join(latest_time) if isinstance(latest_time, list) else latest_time
                time_label = f'[{", ".join(latest_time)}]' if isinstance(latest_time, list) else latest_time

                sql_template = templates.get(data_type_name)
                if not sql_template:
                    continue

                # 代理用户用电明细与代理用户用电总计差异：特殊处理
                if data_type_name == '代理用户用电明细与代理用户用电总计差异':
                    diff_start = (datetime.now() - timedelta(days=9)).strftime('%Y%m%d')
                    diff_end = datetime.now().strftime('%Y%m%d')
                    diff_sql = render_sql(sql_template, trade_center_id, 0, diff_start, diff_end, vpp_id)
                    diff_status = _safe_query(conn, _check_diff, diff_sql)
                    rows.append({
                        'data_type': '明细与总计差异',
                        'latest': diff_status,
                        'volume': '—',
                        'continuity': '—',
                    })
                    if '✅' in diff_status:
                        results['passed'].append({'center': center_name, 'data_type': data_type_name, 'check': {'passed': True}})
                    else:
                        results['failed'].append({'center': center_name, 'data_type': data_type_name, 'check': {'passed': False, 'error': diff_status}})
                    continue

                offsets = parse_offset_days(time_str)

                # === 最新数据时间验证 ===
                passed, used_offset, max_date, error, fallback_log = _safe_query(
                    conn, check_latest_data, sql_template, trade_center_id, offsets, vpp_id
                )
                latest_status = f"✅ {max_date}" if passed else f"❌ {error}"

                # 缓存预期日期，避免重复计算
                expected_date = _compute_expected_date(used_offset)

                # === 计算连续性验证窗口（最新数据日期往前推10天）===
                if not passed and error and '无数据' in error:
                    # 全部offset都无数据，不跑连续性检查
                    continuity_status = '⏭️ 本月无数据'
                    cont_start_date = cont_end_date = None
                else:
                    if passed:
                        cont_end_date = datetime.strptime(max_date, '%Y-%m-%d')
                    else:
                        cont_end_date = expected_date - timedelta(days=1)
                    cont_start_date = cont_end_date - timedelta(days=9)

                # === 数据量合理性校验（仅网侧预测/网侧实际）===
                vol_status = None
                if data_type_name in ('网侧预测', '网侧实际') and cont_start_date is not None:
                    volume_sql = render_sql(sql_template, trade_center_id, used_offset,
                                           cont_start_date.strftime('%Y-%m-%d'),
                                           cont_end_date.strftime('%Y-%m-%d'), vpp_id)
                    vol_ok, vol_count, vol_days, vol_err = _safe_query(conn, check_data_volume, volume_sql)
                    vol_status = "—" if vol_err is None else (f"✅ {vol_err}" if vol_ok else f"❌ {vol_err}")

                # === 日期连续性验证 ===
                if cont_start_date is not None:
                    rendered_sql = render_sql(sql_template, trade_center_id, used_offset,
                                             cont_start_date.strftime('%Y-%m-%d'),
                                             cont_end_date.strftime('%Y-%m-%d'), vpp_id)
                    continuity_passed, missing_dates, _ = _safe_query(
                        conn, check_date_continuity, rendered_sql, cont_start_date, cont_end_date)
                    if continuity_passed:
                        continuity_status = f"✅ {cont_start_date.strftime('%m-%d')}~{cont_end_date.strftime('%m-%d')}"
                    elif len(missing_dates) > 3:
                        continuity_status = f"❌ {', '.join(missing_dates[:3])} 等{len(missing_dates)}天"
                    else:
                        continuity_status = f"❌ {', '.join(missing_dates)}"

                rows.append({
                    'data_type': f'{data_type_name}（{time_label}）',
                    'latest': latest_status,
                    'volume': vol_status or '—',
                    'continuity': continuity_status,
                })

                if passed:
                    results['passed'].append({
                        'center': center_name,
                        'data_type': f'{data_type_name}（{time_label}）',
                        'check': {'offset': used_offset, 'expected_date': expected_date.strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': True}
                    })
                else:
                    results['failed'].append({
                        'center': center_name,
                        'data_type': f'{data_type_name}（{time_label}）',
                        'check': {'offset': used_offset, 'expected_date': expected_date.strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': False, 'error': error}
                    })

                if vol_status and '❌' in vol_status:
                    results['failed'].append({
                        'center': center_name,
                        'data_type': f'{data_type_name}（{time_label}）',
                        'check': {'type': 'volume', 'passed': False, 'error': vol_status}
                    })

            center_results[center_name] = {'center_id': trade_center_id, 'rows': rows}
    finally:
        conn.close()

    # === 写入 MD 文件 ===
    output_dir = Path(__file__).parent.parent / 'output'
    os.makedirs(output_dir, exist_ok=True)
    report_file = output_dir / f"rpa_check_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"

    report_content = []
    report_content.append(f"# RPA数据采集校验报告\n\n执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for center_name, cr in center_results.items():
        report_content.append(f"\n## 交易中心: {center_name} (ID: {cr['center_id']})")
        report_content.append('| 数据类型 | 最新数据时间 | 数据量 | 日期连续性 |')
        report_content.append('|----------|-------------|--------|-----------|')
        for r in cr['rows']:
            report_content.append(f"| {r['data_type']} | {r['latest']} | {r['volume']} | {r['continuity']} |")

    report_content.append(f"\n---\n\n## 校验汇总\n\n执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_content.append(f"- ✅ 通过: {len(results['passed'])}")
    report_content.append(f"- ❌ 失败: {len(results['failed'])}")
    if results['failed']:
        report_content.append("\n### 失败详情")
        for fail in results['failed']:
            check = fail['check']
            ctype = check.get('type', '')
            if ctype == 'continuity':
                missing = ', '.join(check.get('missing_dates', []))
                report_content.append(f"- ❌ {fail['center']} / {fail['data_type']} - 日期不连续: 缺失 {missing}")
            elif ctype == 'volume':
                report_content.append(f"- ❌ {fail['center']} / {fail['data_type']} - 数据量: {check['error']}")
            else:
                report_content.append(f"- ❌ {fail['center']} / {fail['data_type']} (offset={check.get('offset', '?')}) - {check.get('error', '未知错误')}")

    md_text = '\n'.join(report_content) + '\n'

    # 写入文件
    with open(report_file, 'w', encoding='utf-8') as _f:
        _f.write(md_text)

    # 同时写入用户传入的 outfile（如有）
    if outfile is not None:
        outfile.write(md_text)

    # === 构建并返回结构化结果 ===
    return _build_structured_result(results, center_results, str(report_file))


def _build_structured_result(results, center_results, report_file: str):
    """将 run_check 的 (results, center_results) 构建为飞书通知所需的结构化 dict"""
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


def main():
    parser = argparse.ArgumentParser(description='RPA数据采集完整性校验')
    parser.add_argument('--config', default='doc/数据中心类型定义.json', help='数据中心类型定义JSON路径')
    parser.add_argument('--connection', '-c', default='prod', help='数据库连接名称（test/prod）')
    parser.add_argument('--trade-center', help='指定交易中心名称')
    parser.add_argument('--data-type', help='指定数据类型')
    parser.add_argument('--start-date', help='起始日期（YYYYMMDD）')
    parser.add_argument('--end-date', help='结束日期（YYYYMMDD）')

    args = parser.parse_args()

    config_path = Path(args.config) if Path(args.config).is_absolute() else Path(__file__).parent.parent / args.config

    result = run_check(
        connection=args.connection,
        config_path=str(config_path),
        trade_center=args.trade_center,
        data_type=args.data_type,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # 确保 Windows 控制台 UTF-8 输出
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # 从结构化结果构建控制台摘要
    lines = [
        f"\n✅ 通过: {result['pass_count']} | ❌ 失败: {result['fail_count']}",
        "按中心快速概览:\n",
        '| 交易中心 | 状态 | 主要问题 |',
        '|----------|------|----------|',
    ]
    for c in result['centers']:
        if c['all_pass']:
            lines.append(f"| {c['name']} | **全部通过** ✅ | — |")
        else:
            fails = c['failures'][:3]
            problems = [f"{f['data_type']}: {f['message']}" for f in fails]
            problem = '；'.join(problems)
            if len(c['failures']) > 3:
                problem += f" 等{len(c['failures'])}项"
            lines.append(f"| {c['name']} | 部分通过 | {problem} |")

    print('\n'.join(lines))
    print(f"\n报告已保存到: {result['report_file']}")


if __name__ == '__main__':
    main()
