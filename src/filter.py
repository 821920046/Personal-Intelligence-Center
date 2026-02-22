"""
关键词过滤模块 - 解析用户关键词配置并筛选新闻
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.models import KeywordConfig, KeywordGroup, NewsItem

logger = logging.getLogger(__name__)


def parse_keywords(filepath: str | Path) -> KeywordConfig:
    """
    解析 keywords.txt 为结构化的 KeywordConfig。

    支持语法：
      - 普通词（OR 匹配）
      - +词（AND 必须词）
      - !词（排除词）
      - @N（数量限制）
      - /pattern/（正则）
      - [GLOBAL_FILTER] 全局过滤区
      - [WORD_GROUPS] 关键词组区
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning("关键词文件不存在: %s，将推送全部热点", filepath)
        return KeywordConfig()

    content = filepath.read_text(encoding="utf-8")
    lines = content.strip().splitlines()

    if not lines:
        logger.info("关键词文件为空，将推送全部热点")
        return KeywordConfig()

    config = KeywordConfig()
    current_section = "WORD_GROUPS"  # 默认在词组区

    for line in lines:
        line = line.strip()

        # 跳过空行和注释
        if not line or line.startswith("#"):
            continue

        # 区段标记
        if line == "[GLOBAL_FILTER]":
            current_section = "GLOBAL_FILTER"
            continue
        elif line == "[WORD_GROUPS]":
            current_section = "WORD_GROUPS"
            continue

        if current_section == "GLOBAL_FILTER":
            # 全局过滤区：每行一个过滤词
            config.global_filters.append(line)
        else:
            # 关键词组区：解析一行为一个 KeywordGroup
            group = _parse_keyword_line(line)
            if group:
                config.groups.append(group)

    logger.info(
        "📋 关键词配置加载完成：%d 个全局过滤词，%d 个关键词组",
        len(config.global_filters),
        len(config.groups),
    )
    return config


def _parse_keyword_line(line: str) -> KeywordGroup | None:
    """解析单行关键词为 KeywordGroup"""
    tokens = line.split()
    if not tokens:
        return None

    group = KeywordGroup()

    for token in tokens:
        if token.startswith("@") and token[1:].isdigit():
            # 数量限制 @N
            group.max_count = int(token[1:])
        elif token.startswith("+"):
            # 必须词
            word = token[1:]
            if word:
                group.required_words.append(word)
        elif token.startswith("!"):
            # 过滤词
            word = token[1:]
            if word:
                group.exclude_words.append(word)
        elif token.startswith("/") and token.endswith("/"):
            # 正则表达式
            pattern_str = token[1:-1]
            try:
                group.regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error:
                # 无效正则当普通词处理
                group.normal_words.append(token)
        elif token.startswith("/") and "/" in token[1:]:
            # 兼容 /pattern/i 格式
            parts = token.rsplit("/", 1)
            pattern_str = parts[0][1:]
            try:
                group.regex_patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error:
                group.normal_words.append(token)
        else:
            # 普通关键词
            group.normal_words.append(token)

    # 至少有一个匹配条件才是有效组
    if group.normal_words or group.regex_patterns:
        return group
    return None


def filter_news(
    items: list[NewsItem],
    keyword_config: KeywordConfig,
) -> dict[str, list[NewsItem]]:
    """
    按关键词配置过滤新闻列表。

    Args:
        items: 所有新闻条目
        keyword_config: 关键词配置

    Returns:
        {关键词组描述: [匹配的 NewsItem]} 字典。
        如果没有关键词组（留空），返回 {"all": items}。
    """
    # 无关键词 → 全量推送
    if not keyword_config.groups:
        logger.info("无关键词过滤，将推送全部 %d 条热点", len(items))
        return {"全部热点": items}

    # 1. 全局过滤
    global_filters = [w.lower() for w in keyword_config.global_filters]
    if global_filters:
        before = len(items)
        items = [
            item for item in items
            if not any(gf in item.title.lower() for gf in global_filters)
        ]
        filtered_count = before - len(items)
        if filtered_count:
            logger.info("🚫 全局过滤移除了 %d 条", filtered_count)

    # 2. 按关键词组匹配
    results: dict[str, list[NewsItem]] = {}

    for group in keyword_config.groups:
        group_label = _group_label(group)
        matched: list[NewsItem] = []

        for item in items:
            if group.matches(item.title):
                matched.append(item)
                # 数量限制检查
                if group.max_count > 0 and len(matched) >= group.max_count:
                    break

        if matched:
            results[group_label] = matched
            logger.info("🎯 [%s] 命中 %d 条", group_label, len(matched))

    return results


def _group_label(group: KeywordGroup) -> str:
    """生成关键词组的人类可读标签"""
    parts: list[str] = []
    parts.extend(group.normal_words[:3])  # 最多取前 3 个关键词做标签
    for p in group.regex_patterns[:1]:
        parts.append(f"/{p.pattern}/")
    return " ".join(parts) if parts else "未命名"
