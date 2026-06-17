"""数据库迁移脚本（Alembic 封装）

用法：
    python -m scripts.db_migrate upgrade           # 升级到最新版本
    python -m scripts.db_migrate downgrade -1       # 回滚一个版本
    python -m scripts.db_migrate current           # 查看当前版本
    python -m scripts.db_migrate history           # 查看历史
    python -m scripts.db_migrate revision "说明"    # 创建新迁移
"""
from __future__ import annotations

import sys

from alembic import command
from alembic.config import Config


def main() -> None:
    """主入口。"""
    if len(sys.argv) < 2:
        print("用法: python -m scripts.db_migrate <command> [args]")
        print("\n可用命令:")
        print("  upgrade [revision]    升级到指定版本（默认 head）")
        print("  downgrade <revision>  回滚到指定版本")
        print("  current              查看当前版本")
        print("  history              查看历史")
        print('  revision "<message>" 创建新迁移')
        sys.exit(1)

    cfg = Config("alembic.ini")

    cmd = sys.argv[1]
    args = sys.argv[2:]

    try:
        if cmd == "upgrade":
            target = args[0] if args else "head"
            print(f"🔼 升级到 {target} ...")
            command.upgrade(cfg, target)
            print("✅ 升级完成")
        elif cmd == "downgrade":
            target = args[0] if args else "-1"
            print(f"🔽 回滚到 {target} ...")
            command.downgrade(cfg, target)
            print("✅ 回滚完成")
        elif cmd == "current":
            command.current(cfg)
        elif cmd == "history":
            command.history(cfg)
        elif cmd == "revision":
            message = args[0] if args else "auto-generated"
            command.revision(cfg, message=message, autogenerate=True)
            print("✅ 迁移文件已生成")
        else:
            print(f"❌ 未知命令: {cmd}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
