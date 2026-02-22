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
    将行列表拆分为多条符合字节长度限制的消息。
    注意：企业微信的 4096 限制通常是指字节数（UTF-8 编码）。
    """
    messages: list[str] = []
    current_msg = header
    
    # 企微限制 4096 字节。预留约 100 字节给分页号和末尾空白
    # 这里的阈值使用字节数进行判定
    BYTE_LIMIT = 4000 

    for line in lines:
        # 预估当前消息加上新行后的字节长度
        line_with_newline = "\n" + line
        msg_bytes_len = len(current_msg.encode('utf-8'))
        line_bytes_len = len(line_with_newline.encode('utf-8'))
            
        if msg_bytes_len + line_bytes_len > BYTE_LIMIT:
            # 如果加上这行就超了，先把手头的发出去
            if current_msg.strip() != header.strip():
                messages.append(current_msg)
            current_msg = header + line
        else:
            current_msg += line_with_newline

    if current_msg and current_msg.strip() != header.strip():
        messages.append(current_msg)

    if not messages:
        return [header + "\n📭 暂无有效内容"]

    # 加上页码
    if len(messages) > 1:
        for i in range(len(messages)):
            messages[i] += f"\n\n📄 ({i+1}/{len(messages)})"

    return messages
