"""
消息格式化模块 - 将过滤后的热点生成企业微信 Markdown 消息
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone, timedelta

from src.models import NewsItem

logger = logging.getLogger(__name__)

# 企业微信 Markdown 消息最大长度限制
WEWORK_MAX_LENGTH = 4096

# 北京时间
BJT = timezone(timedelta(hours=8))


# 平台图标映射
PLATFORM_ICONS = {
    "zhihu": "📘",
    "weibo": "👁️‍🗨️",
    "baidu": "🔍",
    "toutiao": "📰",
    "bilibili": "📺",
    "douyin": "🎵",
    "wallstreetcn": "💰",
    "hackernews": "🧡",
    "github": "🔨",
    "reddit": "👽",
    "producthunt": "🐱",
    "techcrunch": "⚡",
    "theverge": "🌐",
    "reuters": "⚖️",
    "bbc": "📻"
}


def format_by_keyword(
    keyword_results: dict[str, list[NewsItem]],
    show_rank: bool = True,
    show_url: bool = True,
    show_hot_value: bool = True,
    show_summary: bool = True,
    use_markdown: bool = True,
    group_summaries: dict[str, str] | None = None,
    daily_insight: str | None = None,
) -> list[str]:
    """
    将按关键词分组的结果格式化为企业微信消息列表。
    """
    if not keyword_results:
        return ["📭 TrendPulse - 暂无匹配关键词的热点"] if not use_markdown else ["📭 **TrendPulse** - 暂无匹配关键词的热点"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    if use_markdown:
        header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"
        if daily_insight:
            header += f"\n💡 **今日洞察**\n> {daily_insight}\n"
    else:
        header = f"📡 TrendPulse 热点速递\n⏰ {now}\n"
        if daily_insight:
            header += f"\n💡 今日洞察：{daily_insight}\n"

    lines: list[str] = []
    for keyword_label, items in keyword_results.items():
        if not items:
            continue
        if use_markdown:
            lines.append(f"\n---\n🔥 **{keyword_label}** `({len(items)}条)`\n")
            if group_summaries and keyword_label in group_summaries:
                lines.append(f"🤖 *AI 综述: {group_summaries[keyword_label]}*\n")
        else:
            lines.append(f"\n---\n🔥 {keyword_label} ({len(items)}条)\n")
            if group_summaries and keyword_label in group_summaries:
                lines.append(f"   [AI 综述] {group_summaries[keyword_label]}\n")
        
        for item in items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary, use_markdown))

    return _split_to_messages(header, lines)


def format_by_platform(
    platform_results: dict[str, list[NewsItem]],
    platform_names: dict[str, str] | None = None,
    show_rank: bool = True,
    show_url: bool = True,
    show_hot_value: bool = True,
    max_per_platform: int = 10,
    show_summary: bool = True,
    use_markdown: bool = True,
    daily_insight: str | None = None,
) -> list[str]:
    """
    将按平台分组的结果格式化为企业微信消息列表。
    """
    if not platform_results:
        return ["📭 TrendPulse - 暂无热点数据"] if not use_markdown else ["📭 **TrendPulse** - 暂无热点数据"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    if use_markdown:
        header = f"📡 **TrendPulse 热点速递**\n⏰ {now}\n"
        if daily_insight:
            header += f"\n💡 **今日洞察**\n> {daily_insight}\n"
    else:
        header = f"📡 TrendPulse 热点速递\n⏰ {now}\n"
        if daily_insight:
            header += f"\n💡 今日洞察：{daily_insight}\n"

    lines: list[str] = []
    for platform_id, items in platform_results.items():
        if not items:
            continue
        
        icon = PLATFORM_ICONS.get(platform_id.split("-")[0].lower(), "📌")
        display_name = items[0].platform if items else (
            platform_names.get(platform_id, platform_id) if platform_names else platform_id
        )
        
        display_items = items[:max_per_platform]
        if use_markdown:
            lines.append(f"\n---\n{icon} **{display_name}**\n")
        else:
            lines.append(f"\n---\n{icon} {display_name}\n")
            
        for item in display_items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary, use_markdown))

    return _split_to_messages(header, lines)


def _safe_byte_truncate(text: str, max_bytes: int) -> str:
    """
    字节级安全截断 Unicode 字符串。
    确保不会在多字节字符中间阶段导致乱码。
    """
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    
    # 截断字节流
    truncated_bytes = encoded[:max_bytes]
    # 过滤掉末尾可能破碎的字符字节
    # UTF-8 中，多字节字符的后续字节都以 10 开头 (0x80 - 0xBF)
    while len(truncated_bytes) > 0 and (truncated_bytes[-1] & 0xC0) == 0x80:
        truncated_bytes = truncated_bytes[:-1]
    
    # 还要去掉起始的那个字节（如果是破碎的）
    if len(truncated_bytes) > 0 and (truncated_bytes[-1] & 0xC0) == 0xC0:
        truncated_bytes = truncated_bytes[:-1]
         
    return truncated_bytes.decode('utf-8', errors='ignore')


def _format_item(
    item: NewsItem, 
    show_rank: bool, 
    show_url: bool, 
    show_hot_value: bool, 
    show_summary: bool = True,
    use_markdown: bool = True
) -> str:
    """格式化单条新闻条目 - 支持 Markdown 和 Text 降级"""
    parts: list[str] = []
    
    # 标题行：加粗并增强视觉区分度
    if use_markdown:
        rank_str = f"`{item.rank}` " if show_rank and item.rank > 0 else ""
        hot_str = f" `[{item.hot_value}]`" if show_hot_value and item.hot_value else ""
    else:
        rank_str = f"[{item.rank}] " if show_rank and item.rank > 0 else ""
        hot_str = f" ({item.hot_value})" if show_hot_value and item.hot_value else ""
    
    # 标题基础清洗：移除所有 HTML 标签并处理换行
    title = re.sub(r'<[^>]+>', '', item.title)
    title = title.replace("\n", " ").strip()
    
    if show_url and item.url:
        if use_markdown:
            title_md = f"{rank_str}**[{title}]({item.url})**{hot_str}"
        else:
            # Text 模式下降级显示链接
            title_md = f"{rank_str}{title}{hot_str} \n🔗 {item.url}"
    else:
        if use_markdown:
            title_md = f"{rank_str}**{title}**{hot_str}"
        else:
            title_md = f"{rank_str}{title}{hot_str}"
    
    parts.append(title_md)
    
    # 摘要行
    if show_summary and item.content:
        # 深度清洗摘要，移除可能的 HTML 残留
        summary = re.sub(r'<[^>]+>', '', item.content)
        summary = summary.replace("\n", " ").strip()
        
        # 安全截断摘要：约 300 字节以内
        if len(summary.encode('utf-8')) > 300:
            summary = _safe_byte_truncate(summary, 290) + "..."
            
        if summary:
            if use_markdown:
                p_tag = f"*{item.platform}* "
                parts.append(f"> {p_tag}{summary}")
            else:
                parts.append(f"   └─ {summary}")
        
    return "\n".join(parts)


def _split_to_messages(header: str, lines: list[str]) -> list[str]:
    """
    将行列表拆分为多条符合字节长度限制的消息。
    """
    messages: list[str] = []
    current_msg = header
    
    # 企微限制 4096 字节。预留安全空间
    BYTE_LIMIT = 3800 

    for line in lines:
        line_with_newline = "\n" + line
        msg_bytes_len = len(current_msg.encode('utf-8'))
        line_bytes_len = len(line_with_newline.encode('utf-8'))
            
        if msg_bytes_len + line_bytes_len > BYTE_LIMIT:
            # 当前消息已接近上限，或者单行本身就巨大
            if current_msg.strip() != header.strip():
                messages.append(current_msg)
                current_msg = header
            
            # 如果单行内容依然超出单条消息的总限制，则由于单行不可分割，进行硬截取
            if len((header + line_with_newline).encode('utf-8')) > BYTE_LIMIT:
                remaining_limit = BYTE_LIMIT - len(header.encode('utf-8')) - 10
                truncated_line = _safe_byte_truncate(line, remaining_limit)
                current_msg = header + "\n" + truncated_line + " (内容超长已截断)..."
                messages.append(current_msg)
                current_msg = header
            else:
                current_msg = header + line
        else:
            current_msg += line_with_newline

    if current_msg and current_msg.strip() != header.strip():
        messages.append(current_msg)

    if not messages:
        return [header + "\n📭 暂无有效内容"]

    # 加上页码
    total_pages = len(messages)
    if total_pages > 1:
        for i in range(total_pages):
            messages[i] += f"\n\n📄 ({i+1}/{total_pages})"

    return messages
