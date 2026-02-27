"""
摘要模块 - 利用 AI 为新闻生成聚合摘要和今日综述
"""

import logging
from typing import Dict, List, Optional
from src.models import NewsItem
from src.ai_engine import AIEngine

logger = logging.getLogger(__name__)

class Summarizer:
    def __init__(self, ai_engine: AIEngine):
        self.ai = ai_engine

    def summarize_group(self, group_name: str, items: List[NewsItem]) -> Optional[str]:
        """为特定的一组新闻生成简短摘要"""
        if not items:
            return None
            
        content_lines = []
        for it in items[:5]:
            content_lines.append(f"- {it.title}")
            
        prompt = (
            f"你是一个资深的新闻编辑。请针对以下关于“{group_name}”的几条新闻，用一句话总结它们的核心动态或共同趋向。\n"
            f"要求：简练（不超过50字），准确。\n\n"
            "新闻列表：\n" + "\n".join(content_lines) + "\n\n"
            "总结："
        )
        
        return self.ai.generate_content(prompt)

    def generate_daily_insight(self, all_items: List[NewsItem]) -> Optional[str]:
        """为今日所有热点生成一个全局综述（金句/热评）"""
        if not all_items:
            return None
            
        platform_tops = {}
        for it in all_items:
            if it.platform_id not in platform_tops:
                platform_tops[it.platform_id] = []
            if len(platform_tops[it.platform_id]) < 2:
                platform_tops[it.platform_id].append(it.title)
        
        sample_titles = []
        for titles in platform_tops.values():
            sample_titles.extend(titles)
            
        prompt = (
            "你是一个极具洞察力的社会观察员。以下是今日各大平台（知乎、微博、GitHub 等）最热门的话题摘要：\n\n"
            + "\n".join(sample_titles[:20]) + "\n\n"
            "请根据这些信息，写一段简短的“今日洞察”（一句话或两三句），风格可以犀利、幽默或严谨，概括当前社会的关注焦点。\n"
            "要求：字数控制在 80 字以内。\n"
            "洞察："
        )
        
        return self.ai.generate_content(prompt)

    def summarize_full_text(self, title: str, full_text: str) -> Optional[str]:
        """为单篇深度阅读文章生成详尽总结"""
        if not full_text or len(full_text) < 100:
            return None
            
        # 限制正文长度，防止 Token 溢出 (截取前 4000 字符)
        content_sample = full_text[:4000]
        
        prompt = (
            f"你是一个深度新闻分析师。请针对下面这篇标题为《{title}》的文章进行深度提炼。\n"
            "要求：\n"
            "1. 概括文章的核心事实或核心观点。\n"
            "2. 总结文章提到的重要细节或背景信息。\n"
            "3. 篇幅约 200-300 字，分点陈述，确保逻辑清晰。\n"
            "4. 语言风格严谨且具有可读性。\n\n"
            "文章标题：《{title}》\n"
            "文章正文：\n" + content_sample + "\n\n"
            "深度提炼："
        )
        
        return self.ai.generate_content(prompt)
