"""飞书 Webhook 通知模块 — 将校验结果推送到飞书群"""

import hashlib
import hmac
import base64
import time
import logging
import requests
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 签名工具
# ---------------------------------------------------------------------------

def _gen_sign(timestamp: int, secret: str) -> str:
    """生成飞书 Webhook 签名（HMAC-SHA256）"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


# ---------------------------------------------------------------------------
# 卡片构建
# ---------------------------------------------------------------------------

def build_card(
    result: dict[str, Any],
    wiki_url: str = "https://wbenergy.feishu.cn/wiki/APocwMagEigGtmkgLkBcHr2Dned",
    button_text: str = "📄 查看完整报告",
) -> dict:
    """
    从 checker 返回的结构化结果构建飞书消息卡片。

    result 预期结构:
    {
        "exec_time": "2026-06-04 17:10:28",
        "pass_count": 47,
        "fail_count": 64,
        "centers": [
            {"name": "广东", "trade_center_id": 1, "failures": [...], "all_pass": False},
            ...
        ]
    }
    """
    has_failures = result["fail_count"] > 0
    header_template = "red" if has_failures else "green"
    status_emoji = "❌" if has_failures else "✅"

    # 各中心摘要
    center_lines = []
    for c in result["centers"]:
        if c["all_pass"]:
            center_lines.append(f"**{c['name']}** ✅ 全部通过")
        else:
            fail_count = len(c.get("failures", []))
            preview = c["failures"][:3]
            lines = "\n".join(f"  • {f['data_type']}: {f['message']}" for f in preview)
            more = f"\n  • ... 等共 {fail_count} 项失败" if fail_count > 3 else ""
            center_lines.append(f"**{c['name']}** ❌ {fail_count}项失败\n{lines}{more}")

    center_md = "\n\n".join(center_lines)

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{status_emoji} RPA数据采集校验报告"},
            "template": header_template,
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**执行时间**：{result['exec_time']}"},
            },
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**✅ 通过**：{result['pass_count']}  **❌ 失败**：{result['fail_count']}",
                },
            },
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": center_md}},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": button_text},
                        "url": wiki_url,
                        "type": "primary",
                    }
                ],
            },
        ],
    }
    return card


# ---------------------------------------------------------------------------
# 发送逻辑
# ---------------------------------------------------------------------------

def send_to_feishu(
    result: dict[str, Any],
    webhook_url: str,
    secret: str | None = None,
    wiki_url: str = "https://wbenergy.feishu.cn/wiki/APocwMagEigGtmkgLkBcHr2Dned",
    button_text: str = "📄 查看完整报告",
    max_retries: int = 3,
    retry_backoff: int = 2,
) -> bool:
    """
    发送校验结果到飞书。

    :param result: checker 返回的结构化结果
    :param webhook_url: 飞书 Webhook URL
    :param secret: Webhook 签名密钥（可选）
    :param wiki_url: 消息卡片中的跳转链接
    :param button_text: 按钮显示文字
    :param max_retries: 最大重试次数
    :param retry_backoff: 指数退避基数（秒）
    :return: 是否发送成功
    """
    card = build_card(result, wiki_url, button_text)
    payload = {"msg_type": "interactive", "card": card}

    # 签名
    if secret:
        timestamp = int(time.time())
        payload["timestamp"] = str(timestamp)
        payload["sign"] = _gen_sign(timestamp, secret)

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 0:
                logger.info("飞书推送成功")
                return True
            else:
                logger.warning(f"飞书返回错误 (尝试 {attempt}/{max_retries}): {data}")
        except requests.RequestException as e:
            logger.warning(f"飞书请求异常 (尝试 {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            backoff = retry_backoff ** attempt  # 2s, 4s, 8s
            time.sleep(backoff)

    logger.error(f"飞书推送失败，已重试 {max_retries} 次")
    return False
