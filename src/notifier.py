"""
通知模块 - 支持多渠道推送 (企业微信, Bark, 钉钉等)
"""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any

import requests

logger = logging.getLogger(__name__)

# 通用配置
SEND_INTERVAL = 1.0
MAX_RETRIES = 3
RETRY_DELAY = 3


class Notifier(ABC):
    """通知器基类"""

    @abstractmethod
    def send(self, messages: list[str], **kwargs: Any) -> bool:
        """发送消息"""
        pass


class WeWorkNotifier(Notifier):
    """企业微信通知器"""

    def __init__(self, webhook_url: str, msg_type: str = "markdown"):
        self.webhook_url = webhook_url
        self.msg_type = msg_type

    def send(self, messages: list[str], **kwargs: Any) -> bool:
        if not self.webhook_url:
            logger.error("❌ 企业微信 Webhook URL 未配置")
            return False

        all_success = True
        for i, msg in enumerate(messages):
            payload = self._build_payload(msg)
            success = self._send_request(payload)
            if not success:
                all_success = False
            
            if i < len(messages) - 1:
                time.sleep(SEND_INTERVAL)
        return all_success

    def _build_payload(self, content: str) -> dict:
        if self.msg_type == "text":
            return {"msgtype": "text", "text": {"content": content}}
        return {"msgtype": "markdown", "markdown": {"content": content}}

    def _send_request(self, payload: dict) -> bool:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    self.webhook_url,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers=headers,
                    timeout=10,
                )
                result = resp.json()
                if result.get("errcode") == 0:
                    return True
                logger.warning("企业微信响应异常: %s", result)
            except Exception as e:
                logger.warning("企业微信请求失败 [第 %d 次]: %s", attempt, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
        return False


class BarkNotifier(Notifier):
    """Bark 通知器 (iOS)"""

    def __init__(self, device_key: str, base_url: str = "https://api.day.app"):
        self.device_key = device_key
        self.base_url = base_url.rstrip("/")

    def send(self, messages: list[str], **kwargs: Any) -> bool:
        if not self.device_key:
            logger.error("❌ Bark Device Key 未配置")
            return False

        all_success = True
        for msg in messages:
            # Bark 消息通常不宜过长，合并为一条可能由服务端截断，这里逐条发送重要摘要
            url = f"{self.base_url}/{self.device_key}"
            payload = {
                "title": kwargs.get("title", "Personal-Intelligence-Center 热点"),
                "body": msg,
                "group": "Personal-Intelligence-Center",
                "icon": "https://raw.githubusercontent.com/gaoryrt/TrendPulse/main/icon.png"
            }
            try:
                resp = requests.post(url, json=payload, timeout=10)
                if resp.status_code != 200:
                    all_success = False
            except Exception as e:
                logger.error("Bark 推送失败: %s", e)
                all_success = False
        return all_success


class DingTalkNotifier(Notifier):
    """钉钉通知器"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send(self, messages: list[str], **kwargs: Any) -> bool:
        if not self.webhook_url:
            logger.error("❌ 钉钉 Webhook URL 未配置")
            return False

        all_success = True
        for msg in messages:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "Personal-Intelligence-Center 热点",
                    "text": msg
                }
            }
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=10)
                result = resp.json()
                if result.get("errcode") != 0:
                    all_success = False
            except Exception as e:
                logger.error("钉钉推送失败: %s", e)
                all_success = False
        return all_success


def get_notifiers(config: dict) -> list[Notifier]:
    """根据配置获取所有启用的通知器"""
    notifiers: list[Notifier] = []
    notify_config = config.get("notifications", {})

    # 兼容旧配置：企业微信
    wework_url = os.environ.get("WEWORK_WEBHOOK_URL") or notify_config.get("wework", {}).get("webhook_url")
    if wework_url:
        msg_type = os.environ.get("WEWORK_MSG_TYPE") or notify_config.get("wework", {}).get("msg_type", "markdown")
        notifiers.append(WeWorkNotifier(wework_url, msg_type))

    # Bark
    bark_config = notify_config.get("bark", {})
    if bark_config.get("enabled"):
        device_key = os.environ.get("BARK_DEVICE_KEY") or bark_config.get("device_key")
        if device_key:
            notifiers.append(BarkNotifier(device_key, bark_config.get("base_url", "https://api.day.app")))

    # 钉钉
    ding_config = notify_config.get("dingtalk", {})
    if ding_config.get("enabled"):
        webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL") or ding_config.get("webhook_url")
        if webhook_url:
            notifiers.append(DingTalkNotifier(webhook_url))

    return notifiers


# 保持向后兼容的函数定义
def send_wework(webhook_url: str, messages: list[str], msg_type: str = "markdown") -> bool:
    notifier = WeWorkNotifier(webhook_url, msg_type)
    return notifier.send(messages)
