"""
消息格式化模块 - 将过滤后的热点生成企业微信 Markdown 消息
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from src.models import NewsItem

logger = logging.getLogger(__name__)

# 企业微信 Markdown 消息最大长度限制
WEWORK_MAX_LENGTH = 4096

# 北京时间
BJT = timezone(timedelta(hours=8))


def format_by_keyword(
    keyword_results: dict[str, list[NewsItem]],
    show_rank: bool = True,
    show_url: bool = True,
    show_hot_value: bool = True,
) -> list[str]:
    """
    将按关键词分组的结果格式化为企业微信 Markdown 消息列表。

    Args:
        keyword_results: {关键词组标签: [NewsItem, ...]}
        show_rank: 是否显示排名
        show_url: 是否显示链接
        show_hot_value: 是否显示热度

    Returns:
        格式化后的消息列表（可能因长度限制分为多条）
    """
    if not keyword_results:
        return ["📭 **TrendPulse** - 暂无匹配关键词的热点"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"

    sections: list[str] = []

    for keyword_label, items in keyword_results.items():
        if not items:
            continue

        section_lines = [f"\n---\n🔍 **{keyword_label}** ({len(items)}条)\n"]

        for item in items:
            line = _format_item(item, show_rank, show_url, show_hot_value)
            section_lines.append(line)

        sections.append("\n".join(section_lines))

    # 组装并分片
    return _split_messages(header, sections)


def format_by_platform(
    platform_results: dict[str, list[NewsItem]],
    platform_names: dict[str, str] | None = None,
    show_rank: bool = True,
    show_url: bool = True,
    show_hot_value: bool = True,
    max_per_platform: int = 10,
) -> list[str]:
    """
    将按平台分组的结果格式化为企业微信 Markdown 消息列表。

    Args:
        platform_results: {平台ID: [NewsItem, ...]}
        platform_names: {平台ID: 显示名称}
        show_rank: 是否显示排名
        show_url: 是否显示链接
        show_hot_value: 是否显示热度
        max_per_platform: 每平台最多显示几条

    Returns:
        Markdown 消息列表
    """
    if not platform_results:
        return ["📭 **TrendPulse** - 暂无热点数据"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"

    sections: list[str] = []

    for platform_id, items in platform_results.items():
        if not items:
            continue

        display_name = items[0].platform if items else (
            platform_names.get(platform_id, platform_id) if platform_names else platform_id
        )
        display_items = items[:max_per_platform]

        section_lines = [f"\n---\n📌 **{display_name}**\n"]

        for item in display_items:
            line = _format_item(item, show_rank, show_url, show_hot_value)
            section_lines.append(line)

        sections.append("\n".join(section_lines))

    return _split_messages(header, sections)


def _format_item(item: NewsItem, show_rank: bool, show_url: bool, show_hot_value: bool) -> str:
    """格式化单条新闻条目"""
    parts: list[str] = []

    # 排名
    if show_rank and item.rank > 0:
        parts.append(f"`{item.rank}.`")

    # 标题（带链接或纯文本）
    if show_url and item.url:
        parts.append(f"[{item.title}]({item.url})")
    else:
        parts.append(item.title)

    # 热度值
    if show_hot_value and item.hot_value:
        parts.append(f" `{item.hot_value}`")

    return " ".join(parts)


def _split_messages(header: str, sections: list[str]) -> list[str]:
    """
    将消息按企业微信长度限制分片。
    每条消息以 header 开头，尽量多地包含 section，不超过 4096 字符。
    """
    messages: list[str] = []
    current = header

    for section in sections:
        # 检查加上当前 section 后是否超限
        if len(current) + len(section) > WEWORK_MAX_LENGTH - 50:  # 留 50 字符余量
            if current.strip() != header.strip():
                messages.append(current)
            current = header + section
        else:
            current += section

    if current.strip():
        messages.append(current)

    if not messages:
        messages.append(header + "\n📭 暂无数据")

    # 多条消息时添加分页标记
    if len(messages) > 1:
        for i, msg in enumerate(messages):
            messages[i] = msg + f"\n\n📄 ({i + 1}/{len(messages)})"

    return messages
