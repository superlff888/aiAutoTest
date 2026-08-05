#!/usr/bin/env python3
"""
db_executor.py - 数据库连接执行脚本

功能：
  - 从 .claude/.env 读取 test/prod 环境配置
  - SQL 执行：连接指定数据库并执行 SQL，返回格式化结果
"""

import argparse
import os
import sys
from contextlib import contextmanager


# ─── Environment Variable Resolver ───

from dotenv import load_dotenv, find_dotenv


def _load_dotenv():
    """自动向上搜索 .env 文件并加载。"""
    load_dotenv(find_dotenv())


def get_connections():
    """从环境变量加载数据库连接配置，支持 test/prod 环境。

    环境变量命名规则：{ENV}_MYSQL_HOST / {ENV}_MYSQL_PORT / {ENV}_MYSQL_USER /
                       {ENV}_MYSQL_PASSWORD / {ENV}_MYSQL_DATABASE
    """
    _load_dotenv()
    env_prefixes = ["TEST", "PROD"]
    cfg = {}
    for prefix in env_prefixes:
        host = os.environ.get(f"{prefix}_MYSQL_HOST")
        if not host:
            continue
        port = os.environ.get(f"{prefix}_MYSQL_PORT", "3306")
        user = os.environ.get(f"{prefix}_MYSQL_USER", "")
        password = os.environ.get(f"{prefix}_MYSQL_PASSWORD", "")
        database = os.environ.get(f"{prefix}_MYSQL_DATABASE", "")

        env_name = prefix.lower()
        cfg[env_name] = {
            "host": host,
            "port": int(port),
            "user": user,
            "password": password,
            "database": database,
            "type": "mysql",
            "databases": [database] if database else [],
        }
    return cfg


def resolve_conn(cfg, conn_name):
    """解析连接名称，支持 "env" 或 "env:db" 格式。"""
    # 直接匹配 key
    if conn_name in cfg:
        entry = cfg[conn_name]
        if "database" in entry:
            return entry

    # 分组格式：env:db 或 env（取第一个库）
    if ":" in conn_name:
        env_name, db_name = conn_name.split(":", 1)
    else:
        env_name = conn_name
        db_name = None

    if env_name in cfg:
        entry = cfg[env_name]
        if "databases" in entry:
            databases = entry["databases"]
            if db_name is None:
                db_name = databases[0]
            elif db_name not in databases:
                raise KeyError(
                    f"数据库 '{db_name}' 不在环境 '{env_name}' 的配置中，"
                    f"可用库: {', '.join(databases)}"
                )
            return {
                "host": entry["host"],
                "port": entry.get("port", 3306),
                "user": entry["user"],
                "password": entry["password"],
                "database": db_name,
                "type": entry.get("type", "mysql"),
            }

    raise KeyError(f"连接 '{conn_name}' 不存在")


# ─── DB Engine ───

def get_driver(conn_info):
    db_type = conn_info.get("type", "mysql")
    if db_type == "mysql":
        try:
            import pymysql
            return "pymysql"
        except ImportError:
            print("[ERROR] 缺少 pymysql 依赖: pip install pymysql")
            sys.exit(1)
    elif db_type == "sqlite":
        import sqlite3
        return "sqlite3"
    else:
        print(f"[ERROR] 不支持的数据库类型: {db_type}")
        sys.exit(1)


def create_connection(conn_info):
    """创建并返回原始数据库连接（无 context manager 包装）。

    用于需要手动管理连接生命周期的场景（如 _ReconnectableConn 重连包装器）。
    """
    driver = get_driver(conn_info)
    host = conn_info.get("host", "")
    port = conn_info.get("port", 3306)
    user = conn_info.get("user", "")
    password = conn_info.get("password", "")
    database = conn_info.get("database", "")

    if driver == "pymysql":
        import pymysql
        return pymysql.connect(
            host=host, port=int(port), user=user,
            password=password, database=database,
            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10, read_timeout=120, write_timeout=30,
        )
    elif driver == "sqlite3":
        import sqlite3
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        return conn
    else:
        raise ValueError(f"不支持的驱动: {driver}")


@contextmanager
def get_connection(conn_info):
    conn = create_connection(conn_info)
    try:
        yield conn
    finally:
        conn.close()


def test_connection(args):
    cfg = get_connections()
    try:
        conn_info = resolve_conn(cfg, args.name)
    except KeyError as e:
        print(f"[ERROR] {e}")
        return
    try:
        with get_connection(conn_info) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        print(f"[OK] 连接 '{args.name}' 测试成功")
    except Exception as e:
        print(f"[FAIL] 连接 '{args.name}' 测试失败: {e}")


def execute_sql(args):
    cfg = get_connections()
    conn_name = args.connection

    # Support inline connection via --inline flag
    if args.inline:
        conn_info = {
            "host": args.host or "",
            "port": args.port or 3306,
            "user": args.user or "",
            "password": args.password or "",
            "database": args.database or "",
            "type": args.db_type or "mysql",
        }
    else:
        try:
            conn_info = resolve_conn(cfg, conn_name)
        except KeyError as e:
            print(f"[ERROR] {e}")
            return

    # Read SQL from file or argument
    sql_file = getattr(args, 'sql_file', None)
    sql_text = getattr(args, 'sql', None)

    if sql_file:
        with open(sql_file, "r", encoding="utf-8") as f:
            sql = f.read()
    elif sql_text:
        sql = sql_text
    else:
        print("[ERROR] 请提供 SQL 语句或 SQL 文件路径")
        return

    sql = sql.strip().rstrip(";")
    driver = get_driver(conn_info)

    try:
        with get_connection(conn_info) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
                if driver == "sqlite3":
                    cols = rows[0].keys() if rows else []
                    rows = [dict(r) for r in rows]
                else:
                    cols = cursor.description
                    cols = [c[0] for c in cols] if cols else []

                print(f"\n{'='*60}")
                print(f"  执行成功 | 返回 {len(rows)} 行数据")
                print(f"{'='*60}\n")

                if not rows:
                    print("(无数据)")
                    return

                # 原始数据输出，不做任何格式化
                for row in rows:
                    print(" | ".join(str(row.get(c, "")) for c in cols))

    except Exception as e:
        print(f"[ERROR] SQL 执行失败: {e}")
        sys.exit(1)


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(
        description="数据库连接器 - SQL 执行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 测试连接
  python db_executor.py test test
  python db_executor.py test prod

  # 执行 SQL
  python db_executor.py exec test --sql "SELECT * FROM users LIMIT 10"

  # 从文件执行 SQL
  python db_executor.py exec test --file query.sql

  # 内联连接（不依赖 .env 配置）
  python db_executor.py exec --inline --host 127.0.0.1 --user root \\
      --password xxx --database mydb --sql "SELECT 1"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # test
    p_test = subparsers.add_parser("test", help="测试数据库连接")
    p_test.add_argument("name", help="连接名称（test/prod）")
    p_test.set_defaults(func=test_connection)

    # exec
    p_exec = subparsers.add_parser("exec", aliases=["e"], help="执行 SQL")
    p_exec.add_argument("connection", nargs="?", help="连接名称（test/prod，使用 --inline 时可选）")
    p_exec.add_argument("--sql", help="SQL 语句")
    p_exec.add_argument("--file", dest="sql_file", help="SQL 文件路径")
    p_exec.add_argument("--inline", action="store_true", help="使用内联连接参数")
    p_exec.add_argument("--host")
    p_exec.add_argument("--port", default=3306)
    p_exec.add_argument("--user")
    p_exec.add_argument("--password")
    p_exec.add_argument("--database")
    p_exec.add_argument("--db-type", default="mysql", choices=["mysql", "sqlite"])
    p_exec.set_defaults(func=execute_sql)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
