"""
企业微信推送模块 - 通过 Webhook 发送 Markdown 消息
"""

from __future__ import annotations

import json
import logging
import time

import requests

logger = logging.getLogger(__name__)

# 企业微信 Webhook 请求间隔（秒），防止被限流
SEND_INTERVAL = 1.0
MAX_RETRIES = 3
RETRY_DELAY = 3


def send_wework(webhook_url: str, messages: list[str], msg_type: str = "markdown") -> bool:
    """
    发送消息到企业微信机器人。

    Args:
        webhook_url: 企业微信 Webhook URL
        messages: 消息列表（可能已分片）
        msg_type: 消息类型 "markdown" 或 "text"

    Returns:
        是否全部发送成功
    """
    if not webhook_url:
        logger.error("❌ 企业微信 Webhook URL 未配置")
        return False

    if not messages:
        logger.warning("⚠️  无消息需要发送")
        return True

    all_success = True

    for i, msg in enumerate(messages):
        success = _send_single(webhook_url, msg, msg_type)
        if not success:
            all_success = False
            logger.error("❌ 第 %d/%d 条消息发送失败", i + 1, len(messages))
        else:
            logger.info("✅ 第 %d/%d 条消息发送成功", i + 1, len(messages))

        # 多条消息间加间隔
        if i < len(messages) - 1:
            time.sleep(SEND_INTERVAL)

    return all_success


def _send_single(webhook_url: str, content: str, msg_type: str = "markdown") -> bool:
    """发送单条消息（带重试）"""
    if msg_type == "text":
        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }
    else:
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }

    headers = {"Content-Type": "application/json; charset=utf-8"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            result = resp.json()

            if result.get("errcode") == 0:
                return True

            logger.warning(
                "企业微信 API 响应异常 [第 %d/%d 次]: errcode=%s, errmsg=%s",
                attempt, MAX_RETRIES,
                result.get("errcode"), result.get("errmsg"),
            )

        except requests.RequestException as e:
            logger.warning(
                "企业微信请求失败 [第 %d/%d 次]: %s",
                attempt, MAX_RETRIES, e,
            )

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY * attempt)

    return False
