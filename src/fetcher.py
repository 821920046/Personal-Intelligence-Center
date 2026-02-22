"""
数据抓取模块 - 双引擎架构
Engine A: NewsNow API（国内平台热搜）
Engine B: 直接抓取（国际平台 API / RSS）
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from html import unescape

import feedparser
import requests

from src.models import NewsItem, PlatformConfig

logger = logging.getLogger(__name__)

# 全局请求配置
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
RETRY_DELAY = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _request_with_retry(url: str, headers: dict | None = None, timeout: int = REQUEST_TIMEOUT) -> requests.Response:
    """带重试的 HTTP GET 请求"""
    _headers = {"User-Agent": USER_AGENT}
    if headers:
        _headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=_headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_error = e
            logger.warning("请求失败 [%s] 第 %d/%d 次: %s", url, attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    raise ConnectionError(f"请求 {url} 失败，已重试 {MAX_RETRIES} 次: {last_error}")


# ============================================================
# Engine A: NewsNow API - 国内平台热搜
# ============================================================

NEWSNOW_API_BASE = "https://newsnow.busiyi.world/api"


def _fetch_newsnow(platform: PlatformConfig) -> list[NewsItem]:
    """通过 NewsNow API 抓取国内平台热搜"""
    url = f"{NEWSNOW_API_BASE}/{platform.id}"
    try:
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        # NewsNow API 返回格式：列表，每项含 title / url / (可选 mobileUrl)
        entries = data if isinstance(data, list) else data.get("items", data.get("data", []))

        for i, entry in enumerate(entries[:platform.max_items]):
            title = entry.get("title", "").strip()
            if not title:
                continue

            item_url = entry.get("url", "") or entry.get("mobileUrl", "")
            hot = entry.get("hot", "") or entry.get("extra", {}).get("hot", "")

            items.append(NewsItem(
                title=title,
                url=item_url,
                platform=platform.name,
                platform_id=platform.id,
                rank=i + 1,
                hot_value=str(hot) if hot else "",
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items

    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


# ============================================================
# Engine B: 直接抓取 - 国际平台
# ============================================================

def _fetch_hackernews(platform: PlatformConfig) -> list[NewsItem]:
    """Hacker News 官方 Firebase API"""
    try:
        resp = _request_with_retry("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids: list[int] = resp.json()[:platform.max_items]

        items: list[NewsItem] = []

        def _get_story(sid: int, rank: int) -> NewsItem | None:
            try:
                r = _request_with_retry(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                story = r.json()
                if not story or story.get("type") != "story":
                    return None
                return NewsItem(
                    title=story.get("title", ""),
                    url=story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    platform=platform.name,
                    platform_id=platform.id,
                    rank=rank,
                    hot_value=f"{story.get('score', 0)} points",
                )
            except Exception:
                return None

        # 并发获取每条故事详情
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(_get_story, sid, i + 1): i for i, sid in enumerate(story_ids)}
            results: list[tuple[int, NewsItem | None]] = []
            for future in as_completed(futures):
                idx = futures[future]
                results.append((idx, future.result()))

        results.sort(key=lambda x: x[0])
        items = [item for _, item in results if item is not None]

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items

    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_github_trending(platform: PlatformConfig) -> list[NewsItem]:
    """GitHub Trending 页面 HTML 解析"""
    try:
        resp = _request_with_retry("https://github.com/trending")
        html = resp.text

        items: list[NewsItem] = []
        # 解析 article.Box-row 中的仓库信息
        repo_pattern = re.compile(
            r'<h2 class="h3[^"]*">\s*<a href="(/[^"]+)"[^>]*>\s*'
            r'(?:<span[^>]*>[^<]*</span>\s*/\s*)?'
            r'<span[^>]*>([^<]+)</span>',
            re.DOTALL,
        )
        star_pattern = re.compile(r'(\d[\d,]*)\s*stars today', re.IGNORECASE)

        blocks = html.split('class="Box-row"')[1:]  # 跳过第一个分割片段
        for i, block in enumerate(blocks[:platform.max_items]):
            repo_match = repo_pattern.search(block)
            if not repo_match:
                continue

            repo_path = repo_match.group(1).strip()
            repo_name = repo_match.group(2).strip()
            full_name = repo_path.strip("/")

            # 提取描述
            desc_match = re.search(r'<p class="[^"]*col-9[^"]*">([^<]+)</p>', block)
            desc = desc_match.group(1).strip() if desc_match else ""

            # 提取今日 Star
            star_match = star_pattern.search(block)
            stars_today = star_match.group(1) if star_match else ""

            title = f"{full_name}: {desc}" if desc else full_name

            items.append(NewsItem(
                title=title,
                url=f"https://github.com{repo_path}",
                platform=platform.name,
                platform_id=platform.id,
                rank=i + 1,
                hot_value=f"⭐ {stars_today} today" if stars_today else "",
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items

    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_reddit(platform: PlatformConfig) -> list[NewsItem]:
    """Reddit Popular - 公开 JSON API"""
    try:
        resp = _request_with_retry(
            "https://www.reddit.com/r/popular.json?limit=30",
            headers={"User-Agent": "TrendPulse/1.0"},
        )
        data = resp.json()
        posts = data.get("data", {}).get("children", [])

        items: list[NewsItem] = []
        for i, post in enumerate(posts[:platform.max_items]):
            post_data = post.get("data", {})
            title = post_data.get("title", "").strip()
            if not title:
                continue

            subreddit = post_data.get("subreddit", "")
            permalink = post_data.get("permalink", "")
            ups = post_data.get("ups", 0)

            items.append(NewsItem(
                title=f"[r/{subreddit}] {title}",
                url=f"https://www.reddit.com{permalink}" if permalink else "",
                platform=platform.name,
                platform_id=platform.id,
                rank=i + 1,
                hot_value=f"⬆ {ups:,}" if ups else "",
                category=subreddit,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items

    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_producthunt(platform: PlatformConfig) -> list[NewsItem]:
    """Product Hunt RSS Feed"""
    return _fetch_rss_generic(platform)


def _fetch_rss_generic(platform: PlatformConfig) -> list[NewsItem]:
    """通用 RSS/Atom Feed 抓取"""
    if not platform.url:
        logger.warning("⚠️  [%s] 未配置 RSS URL，跳过", platform.name)
        return []

    try:
        resp = _request_with_retry(platform.url)
        feed = feedparser.parse(resp.text)

        items: list[NewsItem] = []
        for i, entry in enumerate(feed.entries[:platform.max_items]):
            title = unescape(entry.get("title", "")).strip()
            if not title:
                continue

            link = entry.get("link", "")
            # 提取摘要（纯文本，去除 HTML 标签）
            summary = entry.get("summary", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:100]

            items.append(NewsItem(
                title=title,
                url=link,
                platform=platform.name,
                platform_id=platform.id,
                rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items

    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


# ============================================================
# 引擎分发器
# ============================================================

# 平台类型 → 抓取函数映射
_FETCHER_MAP: dict[str, Callable[[PlatformConfig], list[NewsItem]]] = {
    "newsnow": _fetch_newsnow,
    "hackernews": _fetch_hackernews,
    "github": _fetch_github_trending,
    "reddit": _fetch_reddit,
    "producthunt": _fetch_producthunt,
    "rss": _fetch_rss_generic,
}


def fetch_all(platforms: list[PlatformConfig], max_workers: int = 6) -> dict[str, list[NewsItem]]:
    """
    并发抓取所有已启用平台的热点数据。

    Args:
        platforms: 平台配置列表
        max_workers: 最大并发线程数

    Returns:
        {平台ID: [NewsItem, ...]} 字典
    """
    enabled = [p for p in platforms if p.enabled]
    if not enabled:
        logger.warning("没有启用的平台")
        return {}

    logger.info("📡 开始抓取 %d 个平台...", len(enabled))
    results: dict[str, list[NewsItem]] = {}

    def _do_fetch(p: PlatformConfig) -> tuple[str, list[NewsItem]]:
        fetcher_fn = _FETCHER_MAP.get(p.type)
        if not fetcher_fn:
            logger.error("❌ 未知平台类型: %s (platform=%s)", p.type, p.id)
            return p.id, []
        return p.id, fetcher_fn(p)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_do_fetch, p): p for p in enabled}
        for future in as_completed(futures):
            try:
                platform_id, items = future.result()
                results[platform_id] = items
            except Exception as e:
                p = futures[future]
                logger.error("❌ [%s] 线程异常: %s", p.name, e)
                results[p.id] = []

    total = sum(len(v) for v in results.values())
    logger.info("📡 抓取完成！共 %d 条数据，来自 %d 个平台", total, len(results))
    return results
