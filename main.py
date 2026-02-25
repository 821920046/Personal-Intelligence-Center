#!/usr/bin/env python3
"""
TrendPulse - 多平台热点订阅推送工具
主入口：抓取 → 过滤 → 格式化 → 推送
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml

from src.fetcher import fetch_all
from src.filter import filter_news, parse_keywords
from src.formatter import format_by_keyword, format_by_platform
from src.models import PlatformConfig
from src.notifier import send_wework

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TrendPulse")

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = ROOT_DIR / "config"


def load_config() -> dict:
    """加载 config.yaml 配置"""
    config_path = CONFIG_DIR / "config.yaml"
    if not config_path.exists():
        logger.error("配置文件不存在: %s", config_path)
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_platforms(config: dict) -> list[PlatformConfig]:
    """从配置中解析平台列表"""
    platforms_raw = config.get("platforms", [])
    platforms: list[PlatformConfig] = []

    for p in platforms_raw:
        platforms.append(PlatformConfig(
            id=p["id"],
            name=p["name"],
            type=p.get("type", "newsnow"),
            url=p.get("url", ""),
            enabled=p.get("enabled", True),
            max_items=p.get("max_items", 30),
        ))

    return platforms


def main() -> None:
    """主流程"""
    logger.info("🚀 TrendPulse 启动")

    # 1. 读取配置
    webhook_url = os.environ.get("WEWORK_WEBHOOK_URL", "")
    # 兼容微信：默认改为 text 模式
    msg_type = os.environ.get("WEWORK_MSG_TYPE", "text")
    use_markdown = (msg_type == "markdown")

    if not webhook_url:
        logger.error("❌ 环境变量 WEWORK_WEBHOOK_URL 未设置")
        sys.exit(1)

    config = load_config()
    display_config = config.get("display", {})

    # 2. 加载平台列表
    platforms = load_platforms(config)
    enabled_count = sum(1 for p in platforms if p.enabled)
    logger.info("📋 已加载 %d 个平台（%d 个启用）", len(platforms), enabled_count)

    # 3. 抓取数据
    translation_config = config.get("translation", {})
    platform_results = fetch_all(
        platforms,
        translation_enabled=translation_config.get("enabled", True),
        translation_workers=translation_config.get("max_workers", 5)
    )

    if not platform_results:
        logger.warning("⚠️  所有平台均无数据")
        messages = ["📭 TrendPulse - 本次运行未获取到任何热点数据"]
        send_wework(webhook_url, messages, msg_type)
        return

    # 汇总所有新闻条目
    all_items = []
    for items in platform_results.values():
        all_items.extend(items)
    logger.info("📊 共抓取到 %d 条热点数据", len(all_items))

    # 4. 关键词过滤
    keyword_config = parse_keywords(CONFIG_DIR / "keywords.txt")
    
    show_summary = display_config.get("show_summary", True)

    if keyword_config.groups:
        # 有关键词 → 按关键词分组推送
        keyword_results = filter_news(all_items, keyword_config)
        if not keyword_results:
            logger.info("📭 无匹配关键词的热点")
            messages = ["📭 TrendPulse - 今日暂无匹配订阅关键词的热点"]
            send_wework(webhook_url, messages, msg_type)
            return

        matched_total = sum(len(v) for v in keyword_results.values())
        logger.info("🎯 关键词匹配到 %d 条热点", matched_total)

        messages = format_by_keyword(
            keyword_results,
            show_rank=display_config.get("show_rank", True),
            show_url=display_config.get("show_url", True),
            show_hot_value=display_config.get("show_hot_value", True),
            show_summary=show_summary,
            use_markdown=use_markdown
        )
    else:
        # 无关键词 → 按平台分组推送全部
        messages = format_by_platform(
            platform_results,
            show_rank=display_config.get("show_rank", True),
            show_url=display_config.get("show_url", True),
            show_hot_value=display_config.get("show_hot_value", True),
            max_per_platform=display_config.get("max_items_per_platform", 10),
            show_summary=show_summary,
            use_markdown=use_markdown
        )

    # 5. 推送到企业微信
    logger.info("📤 准备推送 %d 条消息到企业微信 (模式: %s)", len(messages), msg_type)
    success = send_wework(webhook_url, messages, msg_type)

    if success:
        logger.info("🎉 TrendPulse 推送完成！")
    else:
        logger.error("❌ 部分消息推送失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
