"""
数据模型定义 - TrendPulse 核心数据结构
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NewsItem:
    """单条新闻/热搜条目"""

    title: str                          # 标题
    url: str = ""                       # 原文链接
    platform: str = ""                  # 来源平台名称
    platform_id: str = ""               # 平台唯一标识
    rank: int = 0                       # 排名（0 = 未排名）
    hot_value: str = ""                 # 热度值（如 "1.2亿"）
    category: str = ""                  # 分类标签（如 "科技"、"财经"）

    def __post_init__(self) -> None:
        self.title = self.title.strip()


@dataclass
class KeywordGroup:
    """关键词组 - 一行关键词解析后的结构"""

    normal_words: list[str] = field(default_factory=list)   # 普通关键词（OR 匹配）
    required_words: list[str] = field(default_factory=list)  # 必须词（AND 匹配，+ 前缀）
    exclude_words: list[str] = field(default_factory=list)   # 过滤词（排除，! 前缀）
    max_count: int = 0                                       # 数量限制（@N，0 = 不限）
    regex_patterns: list[re.Pattern[str]] = field(default_factory=list)  # 正则模式

    def matches(self, text: str) -> bool:
        """判断文本是否匹配当前关键词组"""
        text_lower = text.lower()

        # 1. 排除词优先检查
        for word in self.exclude_words:
            if word.lower() in text_lower:
                return False

        # 2. 正则匹配
        for pattern in self.regex_patterns:
            if pattern.search(text):
                return True

        # 3. 普通词（OR）匹配
        has_normal_match = False
        if self.normal_words:
            has_normal_match = any(w.lower() in text_lower for w in self.normal_words)
        elif not self.regex_patterns:
            # 没有普通词也没有正则 → 无法匹配
            return False

        # 4. 必须词（AND）检查
        if self.required_words:
            all_required = all(w.lower() in text_lower for w in self.required_words)
            return has_normal_match and all_required

        return has_normal_match


@dataclass
class KeywordConfig:
    """完整的关键词配置"""

    global_filters: list[str] = field(default_factory=list)  # 全局过滤词
    groups: list[KeywordGroup] = field(default_factory=list)  # 关键词组列表


@dataclass
class PlatformConfig:
    """平台配置"""

    id: str                             # 平台唯一标识
    name: str                           # 平台显示名称
    type: str = "newsnow"               # 数据源类型: newsnow / hackernews / github / reddit / rss / producthunt
    url: str = ""                       # RSS / API URL（部分平台需要）
    enabled: bool = True                # 是否启用
    max_items: int = 30                 # 最大抓取条数
