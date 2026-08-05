#!/usr/bin/env python3
"""
RPA 数据采集校验 — 核心校验模块

功能：
1. 最新数据时间验证：根据 JSON 配置验证数据是否采集到最新
2. 日期连续性验证：验证指定时间范围内每一天的数据是否存在
3. 数据量合理性校验：验证每日数据量是否在合理范围内

依赖：
- report_builder: 报告生成与结构化结果构建（已拆分）
"""

import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

# 支持两种运行方式：
# 1. 通过 run_check.py 调用（SKILL_DIR 在 sys.path，使用 scripts.* 包导入）
# 2. 直接运行 python data_validator.py（SCRIPTS_DIR 自动在 sys.path，使用裸名导入）
try:
    from scripts.db_executor import get_connections, resolve_conn, get_connection, create_connection
    from scripts.report_builder import (
        build_report_markdown, build_structured_result,
        write_report_to_file, _format_date_ranges,
    )
except ModuleNotFoundError:
    from db_executor import get_connections, resolve_conn, get_connection, create_connection
    from report_builder import (
        build_report_markdown, build_structured_result,
        write_report_to_file, _format_date_ranges,
    )

# ─── MySQL 连接断开错误码 ───
_CONNECTION_ERRORS = (2006, 2013, 2055)


class _ReconnectableConn:
    """透明重连包装器：捕获 OperationalError 2006/2013 时自动重建连接并重试。

    实现完整的 __enter__/__exit__ 上下文管理协议，可直接用于 with 语句。
    """

    def __init__(self, connection_name: str):
        self._connection_name = connection_name
        self._conn_info = _get_conn(connection_name)
        self._conn = create_connection(self._conn_info)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def cursor(self):
        return self._conn.cursor()

    def _reconnect(self):
        """重建数据库连接。"""
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = create_connection(self._conn_info)

    def close(self):
        """关闭连接。"""
        try:
            self._conn.close()
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


# ─── 数据类型 SQL 映射（问题 #6：扩展为结构化配置，驱动检查类型） ───

_DATA_TYPE_SQL_MAPPING = {
    '日前节点电价': {'sql': '日前节点电价.sql'},
    '实时节点电价': {'sql': '实时节点电价.sql'},
    '日前结算电价': {'sql': '日前结算电价.sql'},
    '实时结算电价': {'sql': '实时结算电价.sql'},
    '网侧预测': {'sql': '网侧预测.sql', 'check_coverage': True},
    '网侧实际': {'sql': '网侧实际.sql', 'check_coverage': True},
    '日前成交电量': {'sql': '日前成交电量.sql'},
    '代理用户用电明细': {'sql': '代理用户用电明细.sql'},
    '代理用户用电总计': {'sql': '代理用户用电总计.sql'},
    '代理用户用电明细与代理用户用电总计差异': {'sql': '代理用户用电明细与代理用户用电总计差异.sql'},
}

_DATE_FIELDS = ['day', 'date', 'time', 'data_date', 'stat_date']


def _get_conn(connection_name: str):
    cfg = get_connections()
    conn_info = resolve_conn(cfg, connection_name)
    return conn_info


def load_data_center_config(config_path: str) -> dict:
    """加载数据中心类型定义JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_sql_templates(sql_dir: Path) -> dict:
    """预加载所有SQL模板到内存，避免重复IO。

    SQL 模板缺失时打 warning，避免被静默跳过导致"全部通过"假象。
    """
    templates = {}
    for dtype, meta in _DATA_TYPE_SQL_MAPPING.items():
        sql_path = sql_dir / meta['sql']
        if sql_path.exists():
            templates[dtype] = sql_path.read_text(encoding='utf-8')
        else:
            logging.warning(
                "SQL 模板缺失: %s（数据类型 %s 将被跳过，请检查文件是否漏提交/漏同步）",
                sql_path, dtype,
            )
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


def _compute_expected_date(offset_days: int, now: datetime = None) -> datetime:
    """计算 offset 对应的预期日期。

    now: 时间基准，None 时使用 datetime.now()。从外部传入可保证
    并行执行的多线程使用同一时间基准，避免跨零点时各线程"今天"不一致。
    """
    if now is None:
        now = datetime.now()
    return now + timedelta(days=-offset_days)


# ─── 问题 #7：SQL 参数安全校验 ───

_SAFE_ID_RE = re.compile(r'^[a-zA-Z0-9_\-{}]+$')


def _validate_sql_param(value, name: str) -> str:
    """校验 SQL 参数安全性，防止注入。"""
    s = str(value).strip()
    if not _SAFE_ID_RE.match(s):
        raise ValueError(f"SQL 参数 {name} 包含不安全字符: {value!r}")
    return s


def render_sql(sql_template: str, trade_center_id: str, offset_days: int,
               start_date: str, end_date: str, vpp_id: str = '1') -> str:
    """渲染 SQL 模板，参数经过安全校验。"""
    safe_tc = _validate_sql_param(trade_center_id, 'trade_center_id')
    safe_vpp = _validate_sql_param(vpp_id, 'vpp_id')
    safe_offset = str(int(offset_days))  # 强制整数，防止注入
    return sql_template.replace('{{trade_center_id}}', safe_tc) \
                       .replace('{{offset_days}}', safe_offset) \
                       .replace('{{vpp_id}}', safe_vpp) \
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
                      offsets: list, vpp_id: str = '1', now: datetime = None) -> tuple:
    """检查最新数据时间，支持多offset降级查询。复用数据库连接。

    now: 时间基准，None 时使用 datetime.now()。
    """
    fallback_log = []
    for i, offset in enumerate(offsets):
        expected_date = _compute_expected_date(offset, now)
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


def check_load_type_coverage(
    conn, sql: str, expected_load_types: set, window_days: int = 10
) -> dict:
    """load_type 覆盖度校验（load-type-day 覆盖率算法）。

    以 expected_load_types 为标准集合 S，对 10 天窗口内的 SQL 结果：
    - 命中 = Σ |actual_d ∩ S|（10 天累计）
    - M = window_days × |S|
    - 缺失 = S - actual_并
    - 超出 = actual_并 - S

    返回 CoverageResult 字典：
    {
        'status': 'E',
        'expected_count': int,           # |S|
        'window_days': int,             # 10
        'total_units': int,             # window_days × expected_count
        'hit_units': int,               # 10 天累计命中单位数
        'hit_rate_text': str,           # 'N/M' 渲染用
        'missing_union': list,          # 10 天 missing 并集
        'extra_union': list,            # 10 天 extra 并集
        'missing_days': dict,           # {date_str: [load_type, ...]}
        'extra_days': dict,
        'missing_day_count': int,
        'extra_day_count': int,
        'has_missing': bool,
        'has_extra': bool,
        'error_msg': str | None,
    }
    """
    expected_count = len(expected_load_types)
    total_units = window_days * expected_count
    expected_str = {str(x) for x in expected_load_types}

    empty_result = {
        'status': 'E',
        'expected_count': expected_count,
        'window_days': window_days,
        'total_units': total_units,
        'hit_units': 0,
        'hit_rate_text': f'0/{total_units}',
        'missing_union': sorted(expected_load_types, key=lambda x: int(x) if str(x).isdigit() else str(x)),
        'extra_union': [],
        'missing_days': {},
        'extra_days': {},
        'missing_day_count': 0,
        'extra_day_count': 0,
        'has_missing': bool(expected_load_types),
        'has_extra': False,
        'error_msg': None,
    }

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()

            if not rows:
                return empty_result

            # 按天归组 actual_d
            actual_by_day = {}  # {date_str: set(load_type)}
            for row in rows:
                date_val = _normalize_date(_extract_date(row))
                if date_val:
                    actual_by_day.setdefault(date_val, set()).add(row.get('load_type'))

            if not actual_by_day:
                return {
                    **empty_result,
                    'error_msg': '无法获取日期字段',
                    'missing_union': sorted(expected_load_types, key=lambda x: int(x) if str(x).isdigit() else str(x)),
                    'has_missing': bool(expected_load_types),
                }

            # 计算命中单位数（load-type-day 覆盖率）
            hit_units = 0
            actual_union = set()
            missing_days = {}
            extra_days = {}
            missing_day_count = 0
            extra_day_count = 0

            def _sort_key(x):
                s = str(x)
                return (0, int(s)) if s.isdigit() else (1, s)

            for date_str, actual_set in actual_by_day.items():
                # 强转 → str；丢弃 None
                actual_set = {str(x) for x in actual_set if x is not None}

                hit_set = actual_set & expected_str
                hit_units += len(hit_set)
                actual_union |= actual_set

                missing = expected_str - actual_set
                extra = actual_set - expected_str
                if missing:
                    missing_days[date_str] = sorted(missing, key=_sort_key)
                    missing_day_count += 1
                if extra:
                    extra_days[date_str] = sorted(extra, key=_sort_key)
                    extra_day_count += 1

            missing_union = sorted(expected_str - actual_union, key=_sort_key)
            extra_union = sorted(actual_union - expected_str, key=_sort_key)

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
            **empty_result,
            'error_msg': f'查询异常: {str(e)}',
        }


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
                    date_key = row.get('time') or row.get('day') or row.get('date') or row.get('data_date') or '?'
                    diff_dates.append(str(date_key))
            if not diff_dates:
                return "✅ diff=0"
            date_summary = _format_date_ranges(diff_dates)
            return f"❌ diff={len(diff_dates)}，{date_summary}"
    except Exception as e:
        return f"❌ 查询异常: {str(e)}"


def _check_single_center(center_name: str, center_config: dict, templates: dict,
                         connection: str, trade_center: str = None,
                         data_type: str = None, now: datetime = None) -> dict:
    """单交易中心校验（每个线程独立连接，互不干扰）。

    now: 统一的时间基准，跨线程保证"今天"一致。

    返回: {center_name: center_id, rows, passed, failed}
    """
    passed = []
    failed = []
    warnings = []
    config_missing = []
    rows = []

    with _ReconnectableConn(connection) as conn:
        trade_center_id = center_config.get('trade_center_id')
        if not trade_center_id:
            return {'center_id': 0, 'rows': [], 'passed': [], 'failed': []}

        vpp_id = center_config.get('vpp_id', '1')

        for data_type_name, time_config in center_config.items():
            if data_type_name in ('trade_center_id', 'vpp_id', '中长期持仓'):
                continue

            if trade_center and trade_center != center_name:
                continue

            if data_type and data_type != data_type_name:
                continue

            if isinstance(time_config, dict):
                # 暂未接入：整行跳过 — 不进表格、不跑最新时间/连续性/覆盖度校验
                # 但在"警告详情"中列出（让维护者知道哪些类型暂未接入）
                if time_config.get('备注') == '暂未接入':
                    warnings.append({
                        'center': center_name,
                        'data_type': data_type_name,
                        'check': {'type': 'not_connected', 'passed': True, 'message': '暂未接入'},
                    })
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
                _now = now or datetime.now()
                diff_start = (_now - timedelta(days=9)).strftime('%Y%m%d')
                diff_end = _now.strftime('%Y%m%d')
                diff_sql = render_sql(sql_template, trade_center_id, 0, diff_start, diff_end, vpp_id)
                diff_status = _safe_query(conn, _check_diff, diff_sql)
                rows.append({
                    'data_type': '明细与总计差异',
                    'latest': diff_status,
                    'volume': '—',
                    'continuity': '—',
                })
                if '✅' in diff_status:
                    passed.append({'center': center_name, 'data_type': data_type_name, 'check': {'passed': True}})
                else:
                    failed.append({'center': center_name, 'data_type': data_type_name, 'check': {'passed': False, 'error': diff_status}})
                continue

            offsets = parse_offset_days(time_str)

            # === 最新数据时间验证 ===
            check_passed, used_offset, max_date, error, fallback_log = _safe_query(
                conn, check_latest_data, sql_template, trade_center_id, offsets, vpp_id, now
            )
            latest_status = f"✅ {max_date}" if check_passed else f"❌ {error}"

            # 缓存预期日期，避免重复计算
            expected_date = _compute_expected_date(used_offset, now)

            # === 计算连续性验证窗口（最新数据日期往前推10天）===
            if not check_passed and error and '无数据' in error:
                # 全部offset都无数据，不跑连续性检查
                continuity_status = '⏭️ 本月无数据'
                cont_start_date = cont_end_date = None
            else:
                if check_passed:
                    cont_end_date = datetime.strptime(max_date, '%Y-%m-%d')
                else:
                    cont_end_date = expected_date - timedelta(days=1)
                cont_start_date = cont_end_date - timedelta(days=9)

            # === 数据量/覆盖度校验（由 _DATA_TYPE_SQL_MAPPING 驱动） ===
            vol_status = None
            type_meta = _DATA_TYPE_SQL_MAPPING.get(data_type_name, {})

            if type_meta.get('check_coverage') and cont_start_date is not None:
                # === 网侧预测/网侧实际：load_type 覆盖度校验（4 状态分流） ===
                load_type_map = center_config.get('load_type', None)

                # 状态 B：中心未配 load_type 字段
                if load_type_map is None or not isinstance(load_type_map, dict):
                    vol_status = '**交易中心没配load_type**'
                    config_missing.append({
                        'center': center_name,
                        'data_type': f'{data_type_name}（{time_label}）',
                        'check': {'type': 'config_missing', 'passed': False, 'message': '交易中心没配load_type'},
                    })
                else:
                    expected = load_type_map.get(data_type_name)

                    # 状态 C：类型 key 缺失
                    if expected is None:
                        vol_status = '**未配置该类型标准**'
                        config_missing.append({
                            'center': center_name,
                            'data_type': f'{data_type_name}（{time_label}）',
                            'check': {'type': 'config_missing', 'passed': False, 'message': '未配置该类型标准'},
                        })
                    # 状态 D：标准为空
                    elif not isinstance(expected, list) or len(expected) == 0:
                        vol_status = '**标准为空**'
                        config_missing.append({
                            'center': center_name,
                            'data_type': f'{data_type_name}（{time_label}）',
                            'check': {'type': 'config_missing', 'passed': False, 'message': '标准为空'},
                        })
                    # 状态 E：有标准且非空，跑覆盖度校验
                    else:
                        coverage_sql = render_sql(sql_template, trade_center_id, used_offset,
                                                 cont_start_date.strftime('%Y-%m-%d'),
                                                 cont_end_date.strftime('%Y-%m-%d'), vpp_id)
                        coverage = _safe_query(
                            conn, check_load_type_coverage, coverage_sql, set(expected), 10
                        )

                        if coverage['error_msg']:
                            vol_status = f"❌ {coverage['error_msg']}"
                            failed.append({
                                'center': center_name,
                                'data_type': f'{data_type_name}（{time_label}）',
                                'check': {'type': 'coverage_error', 'passed': False, 'error': coverage['error_msg']},
                            })
                        else:
                            parts = []
                            if coverage['has_missing']:
                                miss = ', '.join(str(x) for x in coverage['missing_union'])
                                parts.append(f"❌ 缺 [{miss}] ({coverage['missing_day_count']}天)")
                            if coverage['has_extra']:
                                ext = ', '.join(str(x) for x in coverage['extra_union'])
                                parts.append(f"⚠️ 超 [{ext}] ({coverage['extra_day_count']}天)")
                            if not parts:
                                vol_status = "✅"
                            else:
                                vol_status = ' '.join(parts)

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
            elif not type_meta.get('check_coverage') and cont_start_date is not None:
                # === 其他 8 种非网侧类型：显示 10 天总条数（仅显示用，不进任何桶） ===
                count_sql = render_sql(sql_template, trade_center_id, used_offset,
                                      cont_start_date.strftime('%Y-%m-%d'),
                                      cont_end_date.strftime('%Y-%m-%d'), vpp_id)
                row_count = _safe_query(conn, count_rows_in_window, count_sql)
                if row_count is None:
                    vol_status = '❌ 查询异常'
                else:
                    vol_status = f'10 天 {row_count} 条'

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

            if check_passed:
                passed.append({
                    'center': center_name,
                    'data_type': f'{data_type_name}（{time_label}）',
                    'check': {'offset': used_offset, 'expected_date': expected_date.strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': True}
                })
            else:
                failed.append({
                    'center': center_name,
                    'data_type': f'{data_type_name}（{time_label}）',
                    'check': {'offset': used_offset, 'expected_date': expected_date.strftime('%Y-%m-%d'), 'max_date': max_date, 'passed': False, 'error': error}
                })

    return {
        'center_id': trade_center_id,
        'rows': rows,
        'passed': passed,
        'failed': failed,
        'warnings': warnings,
        'config_missing': config_missing,
    }


def run_check(connection: str = "prod", config_path: str | None = None,
              trade_center: str = None, data_type: str = None,
              start_date: str = None, end_date: str = None,
              outfile=None, exec_time=None, max_workers: int = 4):
    """执行完整校验，返回结构化结果。

    各交易中心并行查询（每个线程独立数据库连接），总耗时取决于最慢的一个中心。

    Args:
        connection: 数据库连接名称（prod/test）
        config_path: 数据中心配置 JSON 路径（None 时自动定位）
        trade_center: 指定交易中心名称
        data_type: 指定数据类型
        start_date: 起始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        outfile: 可选，报告内容写入该文件句柄
        exec_time: 可选，统一的时间基准（datetime 对象）。None 时兜底为 datetime.now()。
                   传入可保证并行线程跨零点时"今天"基准一致。
        max_workers: 最大并行线程数（默认 4，受 CPU 核心数限制）

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
    if exec_time is None:
        exec_time = datetime.now()
    # 字符串版本仅用于报告渲染
    exec_time_str = exec_time.strftime("%Y-%m-%d %H:%M:%S")

    # 自动定位 config_path（默认 pm.json：手动触发场景下更贴近当前时点的预期）
    if config_path is None:
        config_path = str(Path(__file__).parent.parent / "doc" / "数据中心类型定义pm.json")
    config_path = Path(config_path) if not isinstance(config_path, Path) else config_path

    config = load_data_center_config(str(config_path))
    sql_dir = config_path.parent.parent / 'sqls'
    templates = load_sql_templates(sql_dir)

    # 收集待查中心列表
    center_tasks = []
    for center_name, center_config in config.items():
        if trade_center and trade_center != center_name:
            continue
        if not center_config.get('trade_center_id'):
            continue
        center_tasks.append((center_name, center_config))

    results = {'passed': [], 'failed': [], 'warnings': [], 'config_missing': []}
    center_results = {}

    # 并行执行各交易中心校验
    effective_workers = min(max_workers, len(center_tasks))
    if effective_workers <= 1:
        effective_workers = 1

    logging.info("DB 查询并行度: %d（共 %d 个交易中心）", effective_workers, len(center_tasks))

    with ThreadPoolExecutor(max_workers=effective_workers, thread_name_prefix="checker") as executor:
        future_to_name = {}
        for center_name, center_config in center_tasks:
            future = executor.submit(
                _check_single_center,
                center_name, center_config, templates, connection,
                trade_center, data_type, exec_time,
            )
            future_to_name[future] = center_name

        for future in as_completed(future_to_name):
            center_name = future_to_name[future]
            try:
                center_result = future.result()
                center_results[center_name] = {
                    'center_id': center_result['center_id'],
                    'rows': center_result['rows'],
                }
                results['passed'].extend(center_result['passed'])
                results['failed'].extend(center_result['failed'])
                results['warnings'].extend(center_result.get('warnings', []))
                results['config_missing'].extend(center_result.get('config_missing', []))
            except Exception as e:
                logging.exception("交易中心 %s 校验异常", center_name)
                center_results[center_name] = {
                    'center_id': config[center_name].get('trade_center_id', 0),
                    'rows': [{
                        'data_type': '⚠️ 校验异常',
                        'latest': f"❌ {str(e)}",
                        'volume': '—',
                        'continuity': '—',
                    }],
                }

    # === 按交易中心配置顺序排序输出 ===
    sorted_centers = {cn: center_results[cn] for cn in config if cn in center_results}
    center_results = sorted_centers

    # === 生成报告内容 & 写入文件 ===
    output_dir = Path(__file__).parent.parent / 'output'
    os.makedirs(output_dir, exist_ok=True)
    report_file = output_dir / f"rpa_check_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"

    md_text = build_report_markdown(
        results, center_results,
        exec_time=exec_time_str,
        warn_count=len(results['warnings']),
        config_missing_count=len(results['config_missing']),
    )

    # 写入文件
    write_report_to_file(report_file, md_text, outfile)

    # === 构建并返回结构化结果 ===
    return build_structured_result(
        results, center_results, str(report_file),
        exec_time=exec_time_str,
        warn_count=len(results['warnings']),
        config_missing_count=len(results['config_missing']),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description='RPA数据采集完整性校验')
    parser.add_argument('--config', default='doc/数据中心类型定义pm.json', help='数据中心类型定义JSON路径（默认 pm.json：手动触发场景下更贴近当前时点的预期；如需 am.json 请显式 --config doc/数据中心类型定义am.json）')
    parser.add_argument('--connection', '-c', default='prod', help='数据库连接名称（test/prod）')
    parser.add_argument('--trade-center', help='指定交易中心名称')
    parser.add_argument('--data-type', help='指定数据类型')
    parser.add_argument('--start-date', help='起始日期（YYYYMMDD）')
    parser.add_argument('--end-date', help='结束日期（YYYYMMDD）')
    parser.add_argument('--max-workers', type=int, default=4, help='最大并行线程数（默认 4）')

    args = parser.parse_args()

    config_path = Path(args.config) if Path(args.config).is_absolute() else Path(__file__).parent.parent / args.config

    result = run_check(
        connection=args.connection,
        config_path=str(config_path),
        trade_center=args.trade_center,
        data_type=args.data_type,
        start_date=args.start_date,
        end_date=args.end_date,
        max_workers=args.max_workers,
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
