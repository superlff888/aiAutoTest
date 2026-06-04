#!/usr/bin/env python
"""
RPA 数据采集校验 — 定时调度入口（技能自包含，可被任何项目调用）

用法:
  uv run python .claude/skills/prod-rpa-checker/run_check.py
  uv run python .claude/skills/prod-rpa-checker/run_check.py --no-notify
  uv run python .claude/skills/prod-rpa-checker/run_check.py --connection test
  uv run python .claude/skills/prod-rpa-checker/run_check.py --dry-run

可移植性:
  将整个 prod-rpa-checker 目录复制到任何其他项目/智能体的 .claude/skills/ 下，
  配置好 .env 即可直接运行，无需修改任何代码。
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# 自动定位技能目录（不依赖当前工作目录，不硬编码项目路径）
# ---------------------------------------------------------------------------
SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
OUTPUT_DIR = SKILL_DIR / "output"

sys.path.insert(0, str(SCRIPTS_DIR))

# 加载 .env（优先项目根目录，其次技能目录）
from dotenv import load_dotenv
# 尝试从当前工作目录往上找 .env
cwd = Path.cwd()
for parent in [cwd] + list(cwd.parents):
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break
else:
    # 兜底：技能目录下的 .env
    load_dotenv(SKILL_DIR / ".env")

# 加载 config.yaml
import yaml
CONFIG_FILE = SKILL_DIR / "config.yaml"
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
else:
    config = {}

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
log_cfg = config.get("logging", {})
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=getattr(logging, log_cfg.get("level", "INFO")),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            SKILL_DIR / log_cfg.get("file", "output/run_check.log"),
            encoding="utf-8",
        ),
    ],
)

# ---------------------------------------------------------------------------
# 导入技能模块
# ---------------------------------------------------------------------------
from checker import run_check
from feishu_notifier import send_to_feishu
from wiki_updater import get_tenant_token, update_wiki_content


def _save_config():
    """将 config 写回 config.yaml 文件。"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def main():
    parser = argparse.ArgumentParser(
        description="RPA 数据采集校验定时调度（技能自包含）"
    )
    parser.add_argument(
        "--connection",
        default=config.get("checker", {}).get("default_connection", "prod"),
        help="数据库连接 (prod/test)",
    )
    parser.add_argument("--no-notify", action="store_true", help="不发送飞书通知")
    parser.add_argument("--dry-run", action="store_true", help="模拟运行")
    parser.add_argument(
        "--notify-mode",
        choices=["always", "on-failure"],
        default=config.get("notify", {}).get("mode", "always"),
        help="通知策略: always=每天都发, on-failure=仅异常时发",
    )
    args = parser.parse_args()

    notify_cfg = config.get("notify", {})
    feishu_cfg = config.get("feishu", {})

    logging.info(f"=== RPA 数据采集校验开始 (env={args.connection}) ===")

    if args.dry_run:
        logging.info("[DRY RUN] 模拟执行，跳过实际校验")
        sys.exit(0)

    # 1. 执行校验
    try:
        result = run_check(connection=args.connection)
    except Exception as e:
        # 校验异常 → 发送告警
        logging.exception("校验执行异常")
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        if webhook_url:
            secret = os.getenv("FEISHU_WEBHOOK_SECRET")
            send_to_feishu({
                "exec_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "pass_count": 0,
                "fail_count": 0,
                "centers": [{
                    "name": "⚠️ 校验执行异常",
                    "all_pass": False,
                    "failures": [{"data_type": "系统", "message": str(e)}]
                }]
            }, webhook_url, secret,
               wiki_url=feishu_cfg.get("wiki_url"),
               button_text=feishu_cfg.get("button_text", "📄 查看完整报告"))
        sys.exit(1)

    logging.info(
        f"校验完成: ✅ {result['pass_count']} / ❌ {result['fail_count']}, "
        f"报告: {result['report_file']}"
    )

    # 2. 通知策略
    if args.no_notify:
        logging.info("跳过飞书通知 (--no-notify)")
        sys.exit(0)

    if args.notify_mode == "on-failure" and result["fail_count"] == 0:
        logging.info("全部通过，跳过飞书通知（on-failure 模式）")
        sys.exit(0)

    # 3. 创建新文档并挂载到 wiki 父节点下（在推送飞书之前）
    wiki_url = feishu_cfg.get("wiki_url")  # 兜底链接
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    MAX_REPORT_HISTORY = 10  # 最多保留 10 条报告记录

    if app_id and app_secret and result.get("report_file"):
        space_id = feishu_cfg.get("wiki_space_id")
        parent_node_token = feishu_cfg.get("wiki_parent_node_token")

        if space_id and parent_node_token:
            try:
                tenant_token = get_tenant_token(app_id, app_secret)
                new_url, new_doc_id, new_title = update_wiki_content(
                    report_file=result["report_file"],
                    tenant_token=tenant_token,
                    space_id=space_id,
                    parent_node_token=parent_node_token,
                )
                if new_url:
                    wiki_url = new_url
                    logging.info("飞书卡片链接: %s", wiki_url)

                    # 维护报告历史记录
                    node_token = new_url.split("/wiki/")[1].strip()
                    report_history = feishu_cfg.get("report_history", [])
                    report_history.append({
                        "doc_id": new_doc_id,
                        "node_token": node_token,
                        "title": new_title,
                    })

                    # 超过 10 条时，删除最早的报告
                    if len(report_history) > MAX_REPORT_HISTORY:
                        oldest = report_history.pop(0)
                        logging.info(
                            "报告记录已达 %d 条，开始清理最早记录: %s (%s)",
                            MAX_REPORT_HISTORY + 1, oldest.get("title"), oldest.get("doc_id")
                        )
                        from wiki_updater import delete_old_document
                        if not delete_old_document(oldest["doc_id"], tenant_token):
                            logging.warning("最早报告删除失败: %s", oldest.get("doc_id"))

                    feishu_cfg["report_history"] = report_history
                    _save_config()
                    logging.info("报告历史记录: %d 条", len(report_history))
            except Exception:
                logging.exception("wiki 更新失败，使用兜底链接")
        else:
            logging.info("跳过 wiki 更新：未配置 wiki_space_id 或 wiki_parent_node_token")
    else:
        if not (app_id and app_secret):
            logging.info("跳过 wiki 更新：未配置 FEISHU_APP_ID / FEISHU_APP_SECRET")

    # 4. 推送飞书（卡片链接已动态更新为最新报告）
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        logging.error("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        sys.exit(1)

    secret = os.getenv("FEISHU_WEBHOOK_SECRET")
    ok = send_to_feishu(
        result, webhook_url, secret,
        wiki_url=wiki_url,
        button_text=feishu_cfg.get("button_text", "📄 查看完整报告"),
        max_retries=notify_cfg.get("max_retries", 3),
        retry_backoff=notify_cfg.get("retry_backoff", 2),
    )

    if not ok:
        logging.error("飞书推送失败，请检查网络或 Webhook 配置")
        sys.exit(1)

    logging.info("=== RPA 数据采集校验完成 ===")


if __name__ == "__main__":
    main()
