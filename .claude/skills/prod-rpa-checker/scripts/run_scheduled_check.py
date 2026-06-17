"""
定时任务启动脚本：上午 / 下午通用入口。
根据 --config 参数加载对应 JSON（am.json / pm.json）。

被 run_silent.ps1（自包含 launcher）调用；也可手动执行用于本地调试。

用法:
  python scripts/run_scheduled_check.py --config doc/数据中心类型定义am.json --tag morning
  python scripts/run_scheduled_check.py --config doc/数据中心类型定义pm.json --tag afternoon

Windows 任务计划程序配置：
  - 触发器：每天 08:35 / 17:15
  - 操作：powershell.exe -File <skill_dir>/run_silent.ps1 <config_rel> <tag>
"""
import argparse
import subprocess
import sys
from pathlib import Path

# 本文件 = <skill_dir>/scripts/run_scheduled_check.py
# skills/prod-rpa-checker/scripts/ 向上 1 层 = skills/prod-rpa-checker/（SKILL_DIR）
# 向上 3 层 = 项目根 aiAutoTest/
SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SKILL_DIR.parent.parent.parent
RUN_CHECK = SKILL_DIR / "run_check.py"


def main():
    parser = argparse.ArgumentParser(
        description="RPA 数据采集校验定时调度入口（上午/下午通用）",
    )
    parser.add_argument(
        "--config", required=True,
        help="数据中心配置 JSON 相对路径（相对项目根），如 doc/数据中心类型定义am.json",
    )
    parser.add_argument(
        "--tag", required=True, choices=["morning", "afternoon"],
        help="任务标签，仅用于日志前缀",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(RUN_CHECK),
        "--config", args.config,
        "--connection", "prod",
    ]
    print(f"[{args.tag}-check] 工作目录: {PROJECT_ROOT}")
    print(f"[{args.tag}-check] 执行命令: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=False)
    except FileNotFoundError as e:
        print(f"[ERROR] 找不到可执行文件: {e}", file=sys.stderr)
        sys.exit(2)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()