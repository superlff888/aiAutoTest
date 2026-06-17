"""
定时任务启动脚本：下午 17:15
数据中心配置：pm.json（整体后移 1 天）

走 run_check.py 入口（集成飞书推送 + wiki 文档维护）。

在 Windows 任务计划程序里配置：
  - 触发器：每天 17:15
  - 操作：python <本文件绝对路径>
"""
import subprocess
import sys
from pathlib import Path

# 文件路径：.../aiAutoTest/.claude/skills/prod-rpa-checker/scripts/run_afternoon_check.py
# parents[4] 即项目根目录 aiAutoTest/
PROJECT_ROOT = Path(__file__).resolve().parents[4]
RUN_CHECK = PROJECT_ROOT / ".claude" / "skills" / "prod-rpa-checker" / "run_check.py"
CONFIG_REL = "doc/数据中心类型定义pm.json"


def main():
    cmd = [
        sys.executable,
        str(RUN_CHECK),
        "--config", CONFIG_REL,
        "--connection", "prod",
    ]
    print(f"[afternoon-check] 工作目录: {PROJECT_ROOT}")
    print(f"[afternoon-check] 执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
