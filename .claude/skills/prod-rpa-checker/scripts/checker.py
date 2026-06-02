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
import requests

# 添加 db-connector 路径以便导入
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "db_executor",
    str(Path(__file__).parent.parent.parent / "db-connector" / "scripts" / "db_executor.py")
)
db_executor_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(db_executor_module)

get_connections = db_executor_module.get_connections
resolve_conn = db_executor_module.resolve_conn
get_connection = db_executor_module.get_connection

# MySQL error codes indicating lost connection
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
        self._conn = _get_conn(self._connection_name)
        # If get_connection returns a context manager again, enter it
        if hasattr(self._conn, '__enter__'):
            self._conn = self._conn.__enter__()

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
    '中长期持仓': '代理用户用电明细.sql',
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
    return offsets


def get_expected_date(offset_days: int) -> datetime:
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
        expected_date = get_expected_date(offset)
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
                        range_start = expected_date - timedelta(days=9)
                        missing_dates = _get_missing_dates_from_db(conn, sql_template,
                                                                   trade_center_id, range_start, expected_date, vpp_id)
                        return False, offset, None, f"本月缺失 {len(missing_dates)} 天数据", fallback_log
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
                    if fallback_log:
                        fallback_log.append(error)
                    return False, offset, max_date, error, fallback_log
        except Exception as e:
            error = f"查询异常 (offset={offset}): {str(e)}"
            fallback_log.append(error)
            if i == len(offsets) - 1:
                return False, offset, None, error, fallback_log
            continue


def _get_missing_dates_from_db(conn, sql_template: str, trade_center_id: str,
                               start_date: datetime, end_date: datetime, vpp_id: str = '1') -> list:
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    sql = render_sql(sql_template, trade_center_id, 0, start_str, end_str, vpp_id)
    _, missing_dates, _ = _safe_query(conn, check_date_continuity, sql, start_date, end_date)
    return missing_dates


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
    """复用数据库连接检查日期连续性"""
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

            existing_dates = set()
            for row in rows:
                date_val = _extract_date(row)
                if date_val is None:
                    continue
                if isinstance(date_val, datetime):
                    existing_dates.add(date_val.strftime('%Y-%m-%d'))
                else:
                    date_str = str(date_val)
                    existing_dates.add(date_str[:10] if '-' in date_str else f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")

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
    # 收尾
    if start == prev:
        ranges.append(start)
    else:
        ranges.append(f'{start}~{prev}')
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
                    diff_dates.append(str(row.get('time', '?')))
            if not diff_dates:
                return "✅ diff=0"
            date_summary = _format_date_ranges(diff_dates)
            return f"❌ diff={len(diff_dates)}，{date_summary}"
    except Exception as e:
        return f"❌ 查询异常: {str(e)}"


def run_check(connection_name: str, config_path: str, trade_center: str = None,
              data_type: str = None, start_date: str = None, end_date: str = None,
              outfile=None) -> tuple:
    """执行校验

    Args:
        outfile: 可选，写入详细表格的文件句柄
    """
    config = load_data_center_config(config_path)
    sql_dir = Path(config_path).parent.parent / 'sqls'
    templates = load_sql_templates(sql_dir)

    results = {'passed': [], 'failed': []}
    center_results = {}

    conn = _ReconnectableConn(_get_conn(connection_name), connection_name)
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

                # === 计算该数据类型的检查范围（近10天）===
                continuity_offset = offsets[0]
                expected_end_date = get_expected_date(continuity_offset)
                range_start = (expected_end_date - timedelta(days=9)).strftime('%Y-%m-%d')
                range_end = expected_end_date.strftime('%Y-%m-%d')

                # === 最新数据时间验证 ===
                passed, used_offset, max_date, error, fallback_log = _safe_query(
                    conn, check_latest_data, sql_template, trade_center_id, offsets, vpp_id
                )
                latest_status = f"✅ {max_date}" if passed else f"❌ {error}"

                # === 数据量合理性校验（仅网侧预测/网侧实际）===
                vol_status = None
                if data_type_name in ('网侧预测', '网侧实际'):
                    volume_sql = render_sql(sql_template, trade_center_id, continuity_offset, range_start, range_end, vpp_id)
                    vol_ok, vol_count, vol_days, vol_err = _safe_query(conn, check_data_volume, volume_sql)
                    vol_status = "—" if vol_err is None else (f"✅ {vol_err}" if vol_ok else f"❌ {vol_err}")

                # === 日期连续性验证 ===
                if not passed and error and '本月缺失' in error:
                    continuity_status = '⏭️ 本月无数据'
                else:
                    rendered_sql = render_sql(sql_template, trade_center_id, continuity_offset, range_start, range_end, vpp_id)
                    continuity_passed, missing_dates, _ = _safe_query(conn, check_date_continuity, rendered_sql, expected_end_date - timedelta(days=9), expected_end_date)
                    if continuity_passed:
                        continuity_status = f"✅ {(expected_end_date - timedelta(days=9)).strftime('%m-%d')}~{expected_end_date.strftime('%m-%d')}"
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
                        'check': {'offset': used_offset, 'expected_date': get_expected_date(used_offset).strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': True}
                    })
                else:
                    results['failed'].append({
                        'center': center_name,
                        'data_type': f'{data_type_name}（{time_label}）',
                        'check': {'offset': used_offset, 'expected_date': get_expected_date(used_offset).strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': False, 'error': error}
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
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if outfile:
        outfile.write(f"# RPA数据采集校验报告\n\n执行时间：{now_str}\n")
        for center_name, cr in center_results.items():
            outfile.write(f"\n## 交易中心: {center_name} (ID: {cr['center_id']})\n")
            outfile.write('| 数据类型 | 最新数据时间 | 数据量 | 日期连续性 |\n')
            outfile.write('|----------|-------------|--------|-----------|\n')
            for r in cr['rows']:
                outfile.write(f"| {r['data_type']} | {r['latest']} | {r['volume']} | {r['continuity']} |\n")

        outfile.write(f"\n---\n\n## 校验汇总\n\n执行时间：{now_str}\n")
        outfile.write(f"- ✅ 通过: {len(results['passed'])}\n")
        outfile.write(f"- ❌ 失败: {len(results['failed'])}\n")
        if results['failed']:
            outfile.write("\n### 失败详情\n")
            for fail in results['failed']:
                check = fail['check']
                ctype = check.get('type', '')
                if ctype == 'continuity':
                    missing = ', '.join(check.get('missing_dates', []))
                    outfile.write(f"- ❌ {fail['center']} / {fail['data_type']} - 日期不连续: 缺失 {missing}\n")
                elif ctype == 'volume':
                    outfile.write(f"- ❌ {fail['center']} / {fail['data_type']} - 数据量: {check['error']}\n")
                else:
                    outfile.write(f"- ❌ {fail['center']} / {fail['data_type']} (offset={check.get('offset', '?')}) - {check.get('error', '未知错误')}\n")

    return results, center_results


def _build_summary(results, center_results):
    """构建控制台摘要"""
    total_pass = len(results['passed'])
    total_fail = len(results['failed'])

    lines = [f"\n✅ 通过: {total_pass} | ❌ 失败: {total_fail}", "按中心快速概览:\n",
             '| 交易中心 | 状态 | 主要问题 |', '|----------|------|----------|']

    for center_name, cr in center_results.items():
        fails = [f for f in results['failed'] if f['center'] == center_name]

        if not fails:
            lines.append(f"| {center_name} | **全部通过** ✅ | — |")
            continue

        type_issues = {}
        for f in fails:
            raw_dt = f['data_type'].split('（')[0]
            err = f['check'].get('error', '')
            if raw_dt not in type_issues:
                type_issues[raw_dt] = err or f['check'].get('type', 'fail')

        issues = []
        for dt, err in type_issues.items():
            if '本月缺失' in err:
                days = err.split(' ')[1] if ' ' in err else '多'
                issues.append(f'{dt}本月缺失{days}天')
            elif '数据不足' in err or '严重不足' in err:
                issues.append(f'{dt}{err.split(": ")[-1] if ": " in err else err}')
            elif '预期' in err and '实际' in err:
                parts = err.split('，')
                try:
                    ed = datetime.strptime(parts[0].replace('预期 ', ''), '%Y-%m-%d')
                    ad = datetime.strptime(parts[1].replace('实际 ', ''), '%Y-%m-%d')
                    issues.append(f'{dt}缺{(ed - ad).days}天')
                except Exception:
                    issues.append(f'{dt}落后')
            else:
                issues.append(f'{dt}{err}')

        problem = '；'.join(issues[:3])
        if len(issues) > 3:
            problem += f' 等{len(issues)}项'
        lines.append(f"| {center_name} | 部分通过 | {problem} |")

    diff_fails = [f for f in results['failed'] if '代理用户用电明细与代理用户用电总计差异' in f.get('data_type', '')]
    if not diff_fails:
        lines.append(f"\n所有交易中心的**明细与总计差异**检查均通过。")

    return '\n'.join(lines)


def send_to_feishu(webhook_url: str, md_file: str):
    try:
        content = Path(md_file).read_text(encoding='utf-8')
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": "📊 RPA数据采集校验报告"}, "template": "blue"},
                "elements": [{"tag": "markdown", "content": content}]
            }
        }
        resp = requests.post(webhook_url, json=payload, timeout=30)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("StatusCode") == 0:
                print("\n✅ 报告已发送到飞书群")
            else:
                print(f"\n❌ 飞书发送失败: {result}")
        else:
            print(f"\n❌ 飞书发送异常 HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"\n❌ 飞书发送异常: {e}")


def main():
    parser = argparse.ArgumentParser(description='RPA数据采集完整性校验')
    parser.add_argument('--config', default='doc/数据中心类型定义.json', help='数据中心类型定义JSON路径')
    parser.add_argument('--connection', '-c', default='prod', help='数据库连接名称（test/prod）')
    parser.add_argument('--trade-center', help='指定交易中心名称')
    parser.add_argument('--data-type', help='指定数据类型')
    parser.add_argument('--start-date', help='起始日期（YYYYMMDD）')
    parser.add_argument('--end-date', help='结束日期（YYYYMMDD）')
    # parser.add_argument('--feishu-webhook',
    #                     default='https://open.feishu.cn/open-apis/bot/v2/hook/604c468d-b8a3-4ef1-8cee-7d3a0e04fd6',
    #                     help='飞书Webhook地址（默认自动发送）')

    args = parser.parse_args()

    config_path = Path(args.config) if Path(args.config).is_absolute() else Path(__file__).parent.parent / args.config

    output_dir = Path(__file__).parent.parent / 'output'
    os.makedirs(output_dir, exist_ok=True)
    report_file = output_dir / f"rpa_check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_file, 'w', encoding='utf-8') as md_file:
        results, center_results = run_check(
            connection_name=args.connection,
            config_path=str(config_path),
            trade_center=args.trade_center,
            data_type=args.data_type,
            start_date=args.start_date,
            end_date=args.end_date,
            outfile=md_file
        )

    # 确保 Windows 控制台 UTF-8 输出
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print(_build_summary(results, center_results))
    print(f"\n报告已保存到: {report_file}")

    # if hasattr(args, 'feishu_webhook') and args.feishu_webhook:
    #     send_to_feishu(args.feishu_webhook, str(report_file))


if __name__ == '__main__':
    main()
