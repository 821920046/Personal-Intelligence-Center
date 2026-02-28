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
from src.models import PlatformConfig, NewsItem
from src.notifier import get_notifiers
from src.cache import CacheManager
from src.ai_engine import AIEngine
from src.summarizer import Summarizer
from src.content_extractor import extract_full_text
from src.semantic import SemanticEngine
from src.dashboard import DashboardGenerator

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
    
    # 1.1 初始化缓存
    cache_config = config.get("cache", {})
    cache_enabled = cache_config.get("enabled", True)
    cache_mgr = None
    if cache_enabled:
        cache_path = ROOT_DIR / cache_config.get("file", "config/cache.json")
        cache_mgr = CacheManager(cache_path, expire_days=cache_config.get("expire_days", 7))
        logger.info("💾 已启用去重缓存: %s", cache_path)

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
        messages = ["📭 Personal-Intelligence-Center - 本次运行未获取到任何热点数据"]
        send_wework(webhook_url, messages, msg_type)
        return

    # 汇总所有新闻条目，并进行缓存去重
    all_items = []
    skipped_count = 0
    for items in platform_results.values():
        for item in items:
            if cache_mgr and cache_mgr.is_seen(item.url):
                skipped_count += 1
                continue
            all_items.append(item)
            
    if skipped_count:
        logger.info("♻️ 已过滤掉 %d 条已推送过的热点", skipped_count)
    logger.info("📊 本次共处理 %d 条新热点数据", len(all_items))

    # 4. 关键词过滤
    keyword_config = parse_keywords(CONFIG_DIR / "keywords.txt")
    
    show_summary = display_config.get("display", {}).get("show_summary", True) if isinstance(display_config, dict) else True
    # 修正上面配置获取逻辑
    show_summary = config.get("display", {}).get("show_summary", True)

    # 4.1 AI 智能摘要处理
    ai_config = config.get("ai_summarization", {})
    daily_insight = None
    group_summaries = {}
    
    if ai_config.get("enabled", False):
        logger.info("🤖 正在启动 AI 智能处理...")
        # 优先从环境变量获取 API Key，如果没有则尝试从配置获取
        api_key = os.environ.get("AI_API_KEY") or ai_config.get("api_key")
        ai_engine = AIEngine(
            api_key=api_key,
            model=ai_config.get("model", "gemini-1.5-flash"),
            base_url=ai_config.get("base_url")
        )
        summarizer = Summarizer(ai_engine)
        
        # 4.2 初始化语义雷达
        semantic_config = config.get("semantic_radar", {})
        semantic_engine = None
        if semantic_config.get("enabled", True):
            semantic_engine = SemanticEngine(ai_engine, threshold=semantic_config.get("threshold", 0.7))
            logger.info("📡 语义雷达已就绪")

        # 生成今日洞察
        if ai_config.get("enable_daily_insight", True):
            daily_insight = summarizer.generate_daily_insight(all_items)
            if daily_insight:
                logger.info("💡 今日洞察生成成功")
    
    if keyword_config.groups:
        # 有关键词 → 按关键词分组推送
        keyword_results = filter_news(all_items, keyword_config)
        if not keyword_results:
            logger.info("📭 无匹配关键词的热点")
            messages = ["📭 Personal-Intelligence-Center - 今日暂无匹配订阅关键词的热点"]
            send_wework(webhook_url, messages, msg_type)
            return

        matched_total = sum(len(v) for v in keyword_results.values())
        logger.info("🎯 关键词匹配到 %d 条热点", matched_total)

        # 为各组生成 AI 摘要，并尝试对高价值条目进行深度阅读
        if ai_config.get("enabled", False):
            # 1. 生成组摘要
            if ai_config.get("enable_group_summary", True):
                for label, group_items in keyword_results.items():
                    summary = summarizer.summarize_group(label, group_items)
                    if summary:
                        group_summaries[label] = summary
            
            # 2. 尝试深度阅读 (Full-text AI)
            if ai_config.get("enable_deep_reading", True):
                top_n = ai_config.get("deep_reading_top_n", 3)
                logger.info("📖 正在对高价值热点进行全文提取与深度提炼...")
                for label, group_items in keyword_results.items():
                    # 仅对每组前 top_n 的条目尝试深度抓取
                    for it in group_items[:top_n]:
                        full_content = extract_full_text(it.url)
                        if full_content:
                            deep_summary = summarizer.summarize_full_text(it.title, full_content)
                            if deep_summary:
                                # 将深度摘要存入 NewsItem 的 content 字段，供 Formatter 显示
                                # 并在标题前标注 [精读]
                                it.title = f"[精读] {it.title}"
                                it.content = deep_summary
            
            if group_summaries:
                logger.info("🤖 已生成 %d 组 AI 聚合摘要", len(group_summaries))

        # 4.3 语义雷达发现 (捕捉遗珠)
        if semantic_engine and keyword_config.groups:
            # 提取所有用户关心的词作为语义基准
            all_interests = []
            for g in keyword_config.groups:
                all_interests.extend(g.normal_words)
            
            if all_interests:
                # 找出未被关键词命中的新闻 (且是各个平台的前几名)
                matched_urls = {item.url for group in keyword_results.values() for item in group}
                candidates = [it for it in all_items if it.url not in matched_urls]
                
                logger.info("🔍 语义雷达正在扫描 %d 条候选资讯...", len(candidates))
                discovered = []
                # 语义扫描较耗时，限制扫描数量 (例如扫描前 100 条)
                for it in candidates[:100]:
                    is_match, score = semantic_engine.check_similarity(it.title, all_interests)
                    if is_match:
                        it.hot_value = f"{it.hot_value} | 相关度:{score:.2f}"
                        discovered.append(it)
                    if len(discovered) >= 10: # 最多额外发现 10 条，防止消息爆炸
                        break
                
                if discovered:
                    label = "✨ 语义发现 (AI 自动捕捉)"
                    keyword_results[label] = discovered
                    logger.info("📡 语义雷达发现了 %d 条潜在相关热点", len(discovered))
                    # 同样为其生成摘要
                    summary = summarizer.summarize_group("语义相关资讯", discovered)
                    if summary:
                        group_summaries[label] = summary

        messages = format_by_keyword(
            keyword_results,
            show_rank=config.get("display", {}).get("show_rank", True),
            show_url=config.get("display", {}).get("show_url", True),
            show_hot_value=config.get("display", {}).get("show_hot_value", True),
            show_summary=show_summary,
            use_markdown=use_markdown,
            group_summaries=group_summaries,
            daily_insight=daily_insight
        )
    else:
        # 无关键词 → 按平台分组推送全部
        messages = format_by_platform(
            platform_results,
            show_rank=config.get("display", {}).get("show_rank", True),
            show_url=config.get("display", {}).get("show_url", True),
            show_hot_value=config.get("display", {}).get("show_hot_value", True),
            max_per_platform=config.get("display", {}).get("max_items_per_platform", 10),
            show_summary=show_summary,
            use_markdown=use_markdown,
            daily_insight=daily_insight
        )

    # 5. 分发推送到各渠道
    notifiers = get_notifiers(config)
    if not notifiers:
        logger.error("❌ 未配置任何有效的通知渠道")
        sys.exit(1)

    logger.info("📤 准备推送 %d 条消息到 %d 个渠道", len(messages), len(notifiers))
    
    for notifier in notifiers:
        channel_name = notifier.__class__.__name__.replace("Notifier", "")
        success = notifier.send(messages)
        if success:
            logger.info("🎉 [%s] 推送完成！", channel_name)
        else:
            logger.error("❌ [%s] 部分内容推送失败", channel_name)

    # 6. 生成可视化看板
    if config.get("display", {}).get("enable_dashboard", True):
        dash_gen = DashboardGenerator(output_dir="output")
        dash_path = dash_gen.generate(keyword_results, daily_insight)
        logger.info("🎨 可视化报告已就绪: %s", os.path.abspath(dash_path))

    # 推送成功后（只要有渠道尝试成功），将本轮新条目加入缓存
    if cache_mgr:
        for item in all_items:
            cache_mgr.mark_seen(item.url)
        cache_mgr.save()
        logger.info("💾 缓存已同步")


if __name__ == "__main__":
    main()
