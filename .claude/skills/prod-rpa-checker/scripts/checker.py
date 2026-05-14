#!/usr/bin/env python3
"""
RPA数据采集完整性校验脚本

功能：
1. 最新数据时间验证：根据JSON配置验证数据是否采集到最新
2. 日期连续性验证：验证指定时间范围内每一天的数据都存在
"""

import argparse
import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

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


def load_data_center_config(config_path: str) -> dict:
    """加载数据中心类型定义JSON"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_sql_template(sql_path: str) -> str:
    """加载SQL模板文件"""
    with open(sql_path, 'r', encoding='utf-8') as f:
        return f.read()


def parse_offset_days(time_str: str) -> list:
    """
    将D加减时间转换为offset_days列表
    例如：D-1/D-2 → [1, 2]
    """
    offsets = []
    time_values = time_str.split('/')
    for tv in time_values:
        tv = tv.strip()
        if tv == 'D':
            offsets.append(0)
        elif tv.startswith('D-'):
            days = int(tv[2:])
            offsets.append(days)
        elif tv.startswith('D+'):
            days = int(tv[2:])
            offsets.append(-days)
    return offsets


def get_expected_date(offset_days: int) -> datetime:
    """根据offset_days计算预期日期"""
    return datetime.now() + timedelta(days=-offset_days)


def render_sql(sql_template: str, trade_center_id: str, offset_days: int) -> str:
    """渲染SQL模板，替换占位符"""
    return sql_template.replace('{{trade_center_id}}', str(trade_center_id)).replace('{{offset_days}}', str(offset_days))


def get_db_connection(connection_name: str = 'test'):
    """获取数据库连接"""
    cfg = get_connections()
    conn_info = resolve_conn(cfg, connection_name)
    return get_connection(conn_info)


def check_latest_data(connection_name: str, sql: str, expected_date: datetime) -> tuple:
    """
    检查最新数据时间

    返回: (是否通过, 最大日期字符串, 错误信息)
    """
    try:
        with get_db_connection(connection_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

                if not rows:
                    return False, None, "无数据"

                # 获取最大日期 - 尝试不同可能的日期字段
                max_date = None
                for row in rows:
                    # 尝试多种可能的日期字段名
                    for field_name in ['day', 'date', 'time', 'data_date', 'stat_date']:
                        if field_name in row and row[field_name] is not None:
                            max_date = row[field_name]
                            break
                    if max_date is not None:
                        break

                if max_date is None:
                    return False, None, "无法获取日期字段"

                # 标准化日期字符串
                max_date_str = None
                if isinstance(max_date, datetime):
                    max_date_str = max_date.strftime('%Y-%m-%d')
                elif isinstance(max_date, str):
                    if '-' in max_date:
                        max_date_str = max_date[:10]
                    else:
                        # 假设是 YYYYMMDD 格式
                        max_date_str = f"{max_date[:4]}-{max_date[4:6]}-{max_date[6:8]}"
                elif hasattr(max_date, 'strftime'):
                    # date 对象也有 strftime 方法
                    max_date_str = max_date.strftime('%Y-%m-%d')

                if max_date_str is None:
                    return False, None, f"无法解析日期类型: {type(max_date)}"

                expected_str = expected_date.strftime('%Y-%m-%d')

                if max_date_str == expected_str:
                    return True, max_date_str, None
                else:
                    return False, max_date_str, f"预期 {expected_str}，实际 {max_date_str}"
    except Exception as e:
        return False, None, f"查询异常: {str(e)}"


def check_date_continuity(connection_name: str, sql: str, start_date: datetime, end_date: datetime) -> tuple:
    """
    检查日期连续性

    返回: (是否通过, 缺失日期列表, 错误信息)
    """
    try:
        with get_db_connection(connection_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

                # 提取所有日期
                existing_dates = set()
                for row in rows:
                    for field_name in ['day', 'date', 'time', 'data_date', 'stat_date']:
                        if field_name in row and row[field_name] is not None:
                            date_val = row[field_name]
                            if isinstance(date_val, datetime):
                                existing_dates.add(date_val.strftime('%Y-%m-%d'))
                            else:
                                date_str = str(date_val)
                                if '-' in date_str:
                                    existing_dates.add(date_str[:10])
                                else:
                                    existing_dates.add(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}")
                            break

                # 生成日期序列
                missing_dates = []
                current = start_date
                while current <= end_date:
                    date_str = current.strftime('%Y-%m-%d')
                    if date_str not in existing_dates:
                        missing_dates.append(date_str)
                    current += timedelta(days=1)

                if missing_dates:
                    return False, missing_dates, f"缺失 {len(missing_dates)} 天"
                else:
                    return True, [], None
    except Exception as e:
        return False, [], f"查询异常: {str(e)}"


def get_data_type_to_sql_mapping() -> dict:
    """获取数据类型到SQL文件的映射"""
    return {
        '日前节点电价': '日前节点电价.sql',
        '实时节点电价': '实时节点电价.sql',
        '日前结算电价': '日前结算电价.sql',
        '实时结算电价': '实时结算电价.sql',
        '网侧预测': '网侧预测 .sql',
        '网侧实际': '网侧实际.sql',
        '日前成交电量': '日前成交电量.sql',
        '代理用户用电明细': '代理用户用电明细.sql',
        '代理用户用电总计': '代理用户用电总计.sql',
        '中长期持仓': '代理用户用电明细.sql',  # 使用代理用户用电明细SQL，日期范围不同需调整
    }


def run_check(connection_name: str, config_path: str, trade_center: str = None,
              data_type: str = None, start_date: str = None, end_date: str = None):
    """执行校验"""

    # 加载配置
    config = load_data_center_config(config_path)
    sql_dir = Path(config_path).parent.parent / 'sqls'
    mapping = get_data_type_to_sql_mapping()

    # 默认日期范围
    if start_date is None:
        start_date = datetime.now().replace(day=1)
    else:
        start_date = datetime.strptime(start_date, '%Y%m%d')

    if end_date is None:
        end_date = datetime.now()
    else:
        end_date = datetime.strptime(end_date, '%Y%m%d')

    results = {
        'passed': [],
        'failed': []
    }

    for center_name, center_config in config.items():
        if trade_center and trade_center != center_name:
            continue

        trade_center_id = center_config.get('trade_center_id')
        if not trade_center_id:
            continue

        for data_type_name, time_config in center_config.items():
            if data_type_name == 'trade_center_id':
                continue

            if data_type and data_type != data_type_name:
                continue

            # 判断是否暂未接入
            if isinstance(time_config, dict):
                if time_config.get('备注') == '暂未接入':
                    continue
                latest_time = time_config.get('最新数据时间', '—')
            else:
                latest_time = time_config

            if latest_time == '—':
                continue

            # 处理latest_time为列表的情况（JSON中可能是列表）
            if isinstance(latest_time, list):
                # 列表格式，直接用第一个元素作为主查询
                time_str = latest_time[0]
            else:
                time_str = latest_time

            # 跳过中长期持仓（SQL不同，需要特殊处理）
            if data_type_name == '中长期持仓':
                continue

            sql_file_name = mapping.get(data_type_name)
            if not sql_file_name:
                continue

            sql_path = sql_dir / sql_file_name
            if not sql_path.exists():
                continue

            sql_template = load_sql_template(sql_path)

            # 解析offset_days
            offsets = parse_offset_days(time_str)

            center_result = {
                'center': center_name,
                'data_type': data_type_name,
                'latest_time': latest_time,
                'checks': []
            }

            for offset in offsets:
                expected_date = get_expected_date(offset)
                rendered_sql = render_sql(sql_template, trade_center_id, offset)

                passed, max_date, error = check_latest_data(connection_name, rendered_sql, expected_date)

                check_result = {
                    'offset': offset,
                    'expected_date': expected_date.strftime('%Y-%m-%d'),
                    'max_date': max_date,
                    'passed': passed,
                    'error': error
                }

                if passed:
                    check_result['message'] = f"[PASS] 数据最新 ({max_date})"
                else:
                    check_result['message'] = f"[FAIL] {error}"

                center_result['checks'].append(check_result)

                if not passed:
                    results['failed'].append({
                        'center': center_name,
                        'data_type': data_type_name,
                        'check': check_result
                    })
                else:
                    results['passed'].append({
                        'center': center_name,
                        'data_type': data_type_name,
                        'check': check_result
                    })

            # 打印结果
            print(f"\n{'='*60}")
            print(f"交易中心: {center_name} (ID: {trade_center_id})")
            print(f"数据类型: {data_type_name}")
            print(f"最新数据时间配置: {latest_time}")

            for check in center_result['checks']:
                offset = check['offset']
                offset_str = f"D{'+' if offset < 0 else '-' if offset > 0 else ''}{abs(offset) if offset != 0 else 0}"
                status = "PASS" if check['passed'] else "FAIL"
                print(f"  [{status}] offset={offset} ({offset_str})")
                print(f"      预期: {check['expected_date']}")
                print(f"      实际: {check['max_date'] or 'N/A'}")
                if check['error']:
                    print(f"      错误: {check['error']}")

    # 打印汇总
    print(f"\n{'='*60}")
    print("校验汇总")
    print(f"{'='*60}")
    print(f"通过: {len(results['passed'])}")
    print(f"失败: {len(results['failed'])}")

    if results['failed']:
        print("\n失败详情:")
        for fail in results['failed']:
            print(f"  - {fail['center']} / {fail['data_type']}: {fail['check']['error']}")

    return results


def main():
    parser = argparse.ArgumentParser(description='RPA数据采集完整性校验')
    parser.add_argument('--config', default='doc/数据中心类型定义.json',
                        help='数据中心类型定义JSON路径')
    parser.add_argument('--connection', '-c', default='test',
                        help='数据库连接名称（test/prod）')
    parser.add_argument('--trade-center',
                        help='指定交易中心名称（默认检查所有）')
    parser.add_argument('--data-type',
                        help='指定数据类型（默认检查所有）')
    parser.add_argument('--start-date',
                        help='日期连续性验证起始日期（格式：YYYYMMDD）')
    parser.add_argument('--end-date',
                        help='日期连续性验证结束日期（格式：YYYYMMDD）')

    args = parser.parse_args()

    # 根据 args.config 计算相对路径的基准目录
    if Path(args.config).is_absolute():
        config_path = args.config
    else:
        config_path = Path(__file__).parent.parent / args.config

    run_check(
        connection_name=args.connection,
        config_path=str(config_path),
        trade_center=args.trade_center,
        data_type=args.data_type,
        start_date=args.start_date,
        end_date=args.end_date
    )


if __name__ == '__main__':
    main()