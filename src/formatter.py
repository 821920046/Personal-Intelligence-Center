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
    "bbc": "📻",
    "cnn": "📺",
    "nytimes": "🗞️",
    "guardian": "🛡️",
    "apnews": "🔔",
    "nhk": "🇯🇵",
    "wsj": "💹",
}


def _build_header(title: str, now: str, daily_insight: str | None, use_markdown: bool) -> str:
    """构建消息头部（含装饰带和洞察）"""
    if use_markdown:
        header = f"━━━━━━━━━━━━━━━━━━━━\n📡 **{title}**\n⏰ {now}\n━━━━━━━━━━━━━━━━━━━━"
        if daily_insight:
            header += f"\n\n💡 **今日洞察**\n> {daily_insight}"
    else:
        header = f"════════════════════\n📡 {title}\n⏰ {now}\n════════════════════"
        if daily_insight:
            header += f"\n\n💡 今日洞察：\n{daily_insight}"
    return header


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
        return ["📭 Personal-Intelligence-Center - 暂无匹配关键词的热点"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = _build_header("Personal-Intelligence-Center 热点速递", now, daily_insight, use_markdown)

    lines: list[str] = []
    for keyword_label, items in keyword_results.items():
        if not items:
            continue

        # 分组分隔线 + 标题
        if use_markdown:
            lines.append(f"\n───────────────")
            lines.append(f"🔥 **{keyword_label}**  ┃ {len(items)}条")
            if group_summaries and keyword_label in group_summaries:
                lines.append(f"> 🤖 {_safe_byte_truncate(group_summaries[keyword_label], 200)}")
        else:
            lines.append(f"\n────────────────")
            lines.append(f"🔥 {keyword_label}  | {len(items)}条")
            if group_summaries and keyword_label in group_summaries:
                lines.append(f"  [AI] {group_summaries[keyword_label]}")
        
        for item in items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary, use_markdown))

    # 结束装饰
    if use_markdown:
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    else:
        lines.append("\n════════════════════")

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
        return ["📭 Personal-Intelligence-Center - 暂无热点数据"]

    now = datetime.now(BJT).strftime("%Y-%m-%d %H:%M")
    header = _build_header("Personal-Intelligence-Center 平台热搜", now, daily_insight, use_markdown)

    lines: list[str] = []
    for platform_id, items in platform_results.items():
        if not items:
            continue
        
        icon = PLATFORM_ICONS.get(platform_id.split("-")[0].lower(), "📌")
        display_name = items[0].platform if items else (
            platform_names.get(platform_id, platform_id) if platform_names else platform_id
        )
        
        display_items = items[:max_per_platform]

        # 分组分隔线 + 平台标题
        if use_markdown:
            lines.append(f"\n───────────────")
            lines.append(f"{icon} **{display_name}**  ┃ {len(display_items)}条")
        else:
            lines.append(f"\n────────────────")
            lines.append(f"{icon} {display_name}  | {len(display_items)}条")
            
        for item in display_items:
            lines.append(_format_item(item, show_rank, show_url, show_hot_value, show_summary, use_markdown))

    # 结束装饰
    if use_markdown:
        lines.append("\n━━━━━━━━━━━━━━━━━━━━")
    else:
        lines.append("\n════════════════════")

    return _split_to_messages(header, lines)


def _safe_byte_truncate(text: str, max_bytes: int) -> str:
    """
    字节级安全截断 Unicode 字符串。
    确保不会在多字节字符中间阶段导致乱码。
    """
    encoded = text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return text
    
    truncated_bytes = encoded[:max_bytes]
    while len(truncated_bytes) > 0 and (truncated_bytes[-1] & 0xC0) == 0x80:
        truncated_bytes = truncated_bytes[:-1]
    
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
    """格式化单条新闻条目 - 清晰层级排版"""
    parts: list[str] = []
    
    # 清洗标题首尾空格和换行
    title = re.sub(r'<[^>]+>', '', item.title).replace("\n", " ").strip()
    
    # 带圈数字序号映射 ①-⑳
    CIRCLED_NUMS = "⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    
    if show_rank and 1 <= item.rank <= 20:
        rank_str = f"{CIRCLED_NUMS[item.rank]} "
    elif show_rank and item.rank > 0:
        rank_str = f"{item.rank}. "
    else:
        rank_str = "◆ "
    
    if use_markdown:
        parts.append(f"{rank_str}{title}")
        if show_hot_value and item.hot_value:
            parts.append(f"   📊 `{item.hot_value}`")
    else:
        hot_str = f"  ({item.hot_value})" if show_hot_value and item.hot_value else ""
        parts.append(f"{rank_str}{title}{hot_str}")
    
    # 摘要行
    if show_summary and item.content:
        summary = re.sub(r'<[^>]+>', '', item.content).replace("\n", " ").strip()
        
        # 截断摘要到约 100 字节，更短更精练
        if len(summary.encode('utf-8')) > 120:
            summary = _safe_byte_truncate(summary, 110) + "..."
            
        if summary:
            if use_markdown:
                parts.append(f"> {summary}")
            else:
                parts.append(f"   └ {summary}")
    
    # 条目之间增加空行提升呼吸感
    return "\n".join(parts)


def _split_to_messages(header: str, lines: list[str]) -> list[str]:
    """
    将行列表拆分为多条符合字节长度限制的消息。
    """
    messages: list[str] = []
    current_msg = header
    
    BYTE_LIMIT = 3800 

    for line in lines:
        line_with_newline = "\n" + line
        msg_bytes_len = len(current_msg.encode('utf-8'))
        line_bytes_len = len(line_with_newline.encode('utf-8'))
            
        if msg_bytes_len + line_bytes_len > BYTE_LIMIT:
            if current_msg.strip() != header.strip():
                messages.append(current_msg)
                current_msg = header
            
            if len((header + line_with_newline).encode('utf-8')) > BYTE_LIMIT:
                remaining_limit = BYTE_LIMIT - len(header.encode('utf-8')) - 10
                truncated_line = _safe_byte_truncate(line, remaining_limit)
                current_msg = header + "\n" + truncated_line + " (已截断)"
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
            messages[i] += f"\n\n({i+1}/{total_pages})"

    return messages
