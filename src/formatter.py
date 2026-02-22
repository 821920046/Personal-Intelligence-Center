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
    show_summary: bool = True,
) -> list[str]:
    """
    将按关键词分组的结果格式化为企业微信 Markdown 消息列表。
    """
    if not keyword_results:
        return ["📭 **TrendPulse** - 暂无匹配关键词的热点"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"

    lines: list[str] = []
    for keyword_label, items in keyword_results.items():
        if not items:
            continue
        lines.append(f"\n---\n🔍 **{keyword_label}** ({len(items)}条)\n")
        for item in items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary))

    return _split_to_messages(header, lines)


def format_by_platform(
    platform_results: dict[str, list[NewsItem]],
    platform_names: dict[str, str] | None = None,
    show_rank: bool = True,
    show_url: bool = True,
    show_hot_value: bool = True,
    max_per_platform: int = 10,
    show_summary: bool = True,
) -> list[str]:
    """
    将按平台分组的结果格式化为企业微信 Markdown 消息列表。
    """
    if not platform_results:
        return ["📭 **TrendPulse** - 暂无热点数据"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"

    lines: list[str] = []
    for platform_id, items in platform_results.items():
        if not items:
            continue
        display_name = items[0].platform if items else (
            platform_names.get(platform_id, platform_id) if platform_names else platform_id
        )
        display_items = items[:max_per_platform]
        lines.append(f"\n---\n📌 **{display_name}**\n")
        for item in display_items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary))

    return _split_to_messages(header, lines)


def _format_item(
    item: NewsItem, 
    show_rank: bool, 
    show_url: bool, 
    show_hot_value: bool, 
    show_summary: bool = True
) -> str:
    """格式化单条新闻条目"""
    parts: list[str] = []
    
    # 标题行
    title_line_parts = []
    if show_rank and item.rank > 0:
        title_line_parts.append(f"`{item.rank}.`")
    if show_url and item.url:
        title_line_parts.append(f"[{item.title}]({item.url})")
    else:
        title_line_parts.append(f"**{item.title}**")
    if show_hot_value and item.hot_value:
        title_line_parts.append(f" `{item.hot_value}`")
    
    parts.append(" ".join(title_line_parts))
    
    # 摘要行
    if show_summary and item.content:
        # 清洗摘要，防止过长
        summary = item.content.replace("\n", " ").strip()
        if len(summary) > 150:
            summary = summary[:147] + "..."
        parts.append(f"> {summary}")
        
    return "\n".join(parts)


def _split_to_messages(header: str, lines: list[str]) -> list[str]:
    """
    将行列表拆分为多条符合长度限制的消息。
    """
    messages: list[str] = []
    current_msg = header
    
    # 预留分页符号和余量的空间 (约 200 字符)
    safe_limit = WEWORK_MAX_LENGTH - 200

    for line in lines:
        # 如果单行已经超过限制（极少见），截断它
        if len(line) > safe_limit:
            line = line[:safe_limit] + "..."
            
        if len(current_msg) + len(line) + 1 > safe_limit:
            messages.append(current_msg)
            current_msg = header + line
        else:
            current_msg += "\n" + line

    if current_msg and current_msg != header:
        messages.append(current_msg)

    if not messages:
        return [header + "\n📭 暂无有效内容"]

    # 加上页码
    if len(messages) > 1:
        for i in range(len(messages)):
            messages[i] += f"\n\n📄 ({i+1}/{len(messages)})"

    return messages
