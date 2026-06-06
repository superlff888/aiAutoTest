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
import io
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 自动定位技能目录（不依赖当前工作目录，不硬编码项目路径）
# ---------------------------------------------------------------------------
SKILL_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
OUTPUT_DIR = SKILL_DIR / "output"

# 将 SKILL_DIR 加入 sys.path，支持 "scripts.xxx" 包导入
# 使用 SKILL_DIR（而非 SCRIPTS_DIR）避免裸名导入冲突
sys.path.insert(0, str(SKILL_DIR))

# ---------------------------------------------------------------------------
# .env 加载（延迟到首次需要时，避免 import 时触发）
# ---------------------------------------------------------------------------
_env_loaded = False


def _ensure_env_loaded():
    """延迟加载 .env，仅执行一次。"""
    global _env_loaded
    if _env_loaded:
        return
    from dotenv import load_dotenv, find_dotenv
    _env_path = find_dotenv(usecwd=True)
    if not _env_path:
        _env_path = SKILL_DIR / ".env"
        if _env_path.exists():
            _env_path = str(_env_path)
    if _env_path:
        load_dotenv(_env_path)
    _env_loaded = True


# ---------------------------------------------------------------------------
# config.yaml 加载（延迟到首次需要时）
# ---------------------------------------------------------------------------
_config_cache = None


def _load_config() -> dict:
    """加载 config.yaml，带缓存。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    import yaml
    CONFIG_FILE = SKILL_DIR / "config.yaml"
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}
    return _config_cache


# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
def _setup_logging():
    """配置日志（先修复 Windows 控制台 UTF-8 编码，再配置 logging）。"""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    config = _load_config()
    log_cfg = config.get("logging", {})
    OUTPUT_DIR.mkdir(exist_ok=True)

    _log_file = log_cfg.get("file", "output/run_check.log")
    _log_path = Path(_log_file)
    if not _log_path.is_absolute():
        _log_path = SKILL_DIR / _log_path

    logging.basicConfig(
        level=getattr(logging, log_cfg.get("level", "INFO")),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(_log_path, encoding="utf-8"),
        ],
    )


# ---------------------------------------------------------------------------
# 报告历史
# ---------------------------------------------------------------------------
HISTORY_FILE = OUTPUT_DIR / "report_history.json"
MAX_REPORT_HISTORY = 10
MAX_LOCAL_REPORTS = 10  # 本地 .md 报告保留上限


def _load_history() -> list:
    """加载报告历史记录。"""
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(history: list):
    """保存报告历史记录。"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def _cleanup_old_local_reports():
    """清理本地 .md 报告，仅保留最新的 MAX_LOCAL_REPORTS 条。"""
    reports = sorted(
        OUTPUT_DIR.glob("rpa_check_report_*.md"),
        key=lambda p: p.stat().st_mtime,
    )
    if len(reports) > MAX_LOCAL_REPORTS:
        to_delete = reports[:-MAX_LOCAL_REPORTS]
        for r in to_delete:
            try:
                r.unlink()
                logging.info("清理旧报告: %s", r.name)
            except OSError as e:
                logging.warning("删除旧报告失败: %s (%s)", r.name, e)
        logging.info("本地报告清理完成，保留 %d 条", MAX_LOCAL_REPORTS)


# ---------------------------------------------------------------------------
# 导入技能模块（在 logging 和 .env 配置之后）
# ---------------------------------------------------------------------------
_ensure_env_loaded()
_setup_logging()

from scripts.data_validator import run_check
from scripts.feishu_notifier import send_to_feishu
from scripts.wiki_updater import get_tenant_token, update_wiki_content, delete_old_document


def main():
    config = _load_config()
    exec_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    t0 = time.monotonic()

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

    # 1. 执行校验（统一传入 exec_time）
    t_check = time.monotonic()
    try:
        result = run_check(connection=args.connection, exec_time=exec_time)
    except Exception as e:
        # 校验异常 → 发送告警
        logging.exception("校验执行异常")
        webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
        if webhook_url:
            secret = os.getenv("FEISHU_WEBHOOK_SECRET")
            send_to_feishu({
                "exec_time": exec_time,
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
    t1 = time.monotonic()
    logging.info(f"[性能] DB 校验耗时: {t1 - t_check:.1f}s")

    # 1.5 清理本地旧报告（仅保留最新的 MAX_LOCAL_REPORTS 条）
    _cleanup_old_local_reports()

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
    t_wiki = time.monotonic()

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

                    # 维护报告历史记录（独立 JSON 文件）
                    report_history = _load_history()
                    node_token = new_url.split("/wiki/")[1].strip()
                    report_history.append({
                        "doc_id": new_doc_id,
                        "node_token": node_token,
                        "title": new_title,
                    })

                    # 超过上限时，删除最早的报告（用 obj_token 调用 wiki 删除 API）
                    if len(report_history) > MAX_REPORT_HISTORY:
                        oldest = report_history.pop(0)
                        logging.info(
                            "报告记录已达 %d 条，开始清理最早记录: %s (obj_token=%s)",
                            MAX_REPORT_HISTORY + 1, oldest.get("title"), oldest.get("doc_id")
                        )
                        if not delete_old_document(oldest["doc_id"], tenant_token, space_id=space_id):
                            logging.warning("最早报告删除失败: %s", oldest.get("doc_id"))

                    _save_history(report_history)
                    logging.info("报告历史记录: %d 条", len(report_history))
            except Exception:
                logging.exception("wiki 更新失败，使用兜底链接")
        else:
            logging.info("跳过 wiki 更新：未配置 wiki_space_id 或 wiki_parent_node_token")
    else:
        if not (app_id and app_secret):
            logging.info("跳过 wiki 更新：未配置 FEISHU_APP_ID / FEISHU_APP_SECRET")

    t2 = time.monotonic()
    logging.info(f"[性能] Wiki 更新耗时: {t2 - t_wiki:.1f}s")

    # 4. 推送飞书（卡片链接已动态更新为最新报告）
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        logging.error("未配置 FEISHU_WEBHOOK_URL，跳过推送")
        sys.exit(1)

    t_push = time.monotonic()
    secret = os.getenv("FEISHU_WEBHOOK_SECRET")
    ok = send_to_feishu(
        result, webhook_url, secret,
        wiki_url=wiki_url,
        button_text=feishu_cfg.get("button_text", "📄 查看完整报告"),
        max_retries=notify_cfg.get("max_retries", 3),
        retry_backoff=notify_cfg.get("retry_backoff", 2),
    )
    t3 = time.monotonic()
    logging.info(f"[性能] 飞书推送耗时: {t3 - t_push:.1f}s")
    logging.info(f"[性能] 总耗时: {t3 - t0:.1f}s")

    if not ok:
        logging.error("飞书推送失败，请检查网络或 Webhook 配置")
        sys.exit(1)

    logging.info("=== RPA 数据采集校验完成 ===")


if __name__ == "__main__":
    main()
