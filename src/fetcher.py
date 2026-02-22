"""
数据抓取模块 - 双引擎架构
Engine A: 直接调用各国内平台原始 API
Engine B: 国际平台（官方 API / RSS）
"""

from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from html import unescape
from urllib.parse import quote

import feedparser
import requests

from src.models import NewsItem, PlatformConfig

logger = logging.getLogger(__name__)

# 全局请求配置
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAY = 2
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def _request_with_retry(
    url: str,
    headers: dict | None = None,
    timeout: int = REQUEST_TIMEOUT,
    raise_on_fail: bool = True,
) -> requests.Response:
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

    if raise_on_fail:
        raise ConnectionError(f"请求 {url} 失败，已重试 {MAX_RETRIES} 次: {last_error}")
    return None  # type: ignore


# ============================================================
# Engine A: 国内平台 - 直接调用原始 API
# ============================================================

def _fetch_zhihu(platform: PlatformConfig) -> list[NewsItem]:
    """知乎热榜 - 官方 API"""
    try:
        url = "https://www.zhihu.com/api/v3/feed/topstory/hot-list-web?limit=20&desktop=true"
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        for i, entry in enumerate(data.get("data", [])[:platform.max_items]):
            target = entry.get("target", {})
            title = target.get("title_area", {}).get("text", "").strip()
            if not title:
                continue
            link = target.get("link", {}).get("url", "")
            hot = target.get("metrics_area", {}).get("text", "")

            items.append(NewsItem(
                title=title, url=link, platform=platform.name,
                platform_id=platform.id, rank=i + 1, hot_value=hot,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_weibo(platform: PlatformConfig) -> list[NewsItem]:
    """微博热搜 - 移动端 API（更稳定）"""
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        realtime = data.get("data", {}).get("realtime", [])
        for i, entry in enumerate(realtime[:platform.max_items]):
            title = entry.get("note", "").strip() or entry.get("word", "").strip()
            if not title:
                continue
            word = entry.get("word", title)
            hot_num = entry.get("num", 0)

            items.append(NewsItem(
                title=title,
                url=f"https://s.weibo.com/weibo?q=%23{quote(word)}%23",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
                hot_value=f"{hot_num:,}" if hot_num else "",
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_baidu(platform: PlatformConfig) -> list[NewsItem]:
    """百度热搜 - 从 HTML 中提取嵌入 JSON"""
    try:
        url = "https://top.baidu.com/board?tab=realtime"
        resp = _request_with_retry(url)
        html = resp.text

        # 百度热搜将数据嵌入到 <!--s-data:...--> 注释中
        match = re.search(r'<!--s-data:(.*?)-->', html, re.DOTALL)
        if not match:
            logger.error("❌ [%s] 无法解析页面数据", platform.name)
            return []

        data = json.loads(match.group(1))
        cards = data.get("data", {}).get("cards", [])
        if not cards:
            return []

        content = cards[0].get("content", [])
        items: list[NewsItem] = []
        for i, entry in enumerate(content[:platform.max_items]):
            if entry.get("isTop"):
                continue
            title = entry.get("word", "").strip() or entry.get("query", "").strip()
            if not title:
                continue
            raw_url = entry.get("rawUrl", "") or entry.get("url", "")

            items.append(NewsItem(
                title=title, url=raw_url, platform=platform.name,
                platform_id=platform.id, rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_toutiao(platform: PlatformConfig) -> list[NewsItem]:
    """今日头条 - 官方热榜 API"""
    try:
        url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        for i, entry in enumerate(data.get("data", [])[:platform.max_items]):
            title = entry.get("Title", "").strip()
            if not title:
                continue
            cluster_id = entry.get("ClusterIdStr", "")

            items.append(NewsItem(
                title=title,
                url=f"https://www.toutiao.com/trending/{cluster_id}/" if cluster_id else "",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_bilibili(platform: PlatformConfig) -> list[NewsItem]:
    """B站热搜 - 搜索热词 API"""
    try:
        url = "https://s.search.bilibili.com/main/hotword?limit=30"
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        for i, entry in enumerate(data.get("list", [])[:platform.max_items]):
            title = entry.get("show_name", "").strip() or entry.get("keyword", "").strip()
            if not title:
                continue
            keyword = entry.get("keyword", title)

            items.append(NewsItem(
                title=title,
                url=f"https://search.bilibili.com/all?keyword={quote(keyword)}",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_douyin(platform: PlatformConfig) -> list[NewsItem]:
    """抖音热搜 - 需先获取 Cookie"""
    try:
        # 获取 Cookie
        cookie_resp = requests.get("https://www.douyin.com/", headers={"User-Agent": USER_AGENT}, timeout=10)
        cookies = cookie_resp.headers.get("set-cookie", "")

        url = "https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1"
        resp = _request_with_retry(url, headers={"Cookie": cookies, "Referer": "https://www.douyin.com/"})
        data = resp.json()

        items: list[NewsItem] = []
        word_list = data.get("data", {}).get("word_list", [])
        for i, entry in enumerate(word_list[:platform.max_items]):
            title = entry.get("word", "").strip()
            if not title:
                continue
            sid = entry.get("sentence_id", "")

            items.append(NewsItem(
                title=title,
                url=f"https://www.douyin.com/hot/{sid}" if sid else "",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_wallstreetcn(platform: PlatformConfig) -> list[NewsItem]:
    """华尔街见闻 - 7x24 快讯 API"""
    try:
        url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"
        resp = _request_with_retry(url)
        data = resp.json()

        items: list[NewsItem] = []
        for i, entry in enumerate(data.get("data", {}).get("items", [])[:platform.max_items]):
            title = entry.get("content_text", "").strip()[:80]
            if not title:
                continue
            uri = entry.get("uri", "")

            items.append(NewsItem(
                title=title,
                url=f"https://wallstreetcn.com/live/{uri}" if uri else "",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


# ============================================================
# Engine B: 国际平台
# ============================================================

def _fetch_hackernews(platform: PlatformConfig) -> list[NewsItem]:
    """Hacker News 官方 Firebase API"""
    try:
        resp = _request_with_retry("https://hacker-news.firebaseio.com/v0/topstories.json")
        story_ids: list[int] = resp.json()[:platform.max_items]

        items: list[NewsItem] = []

        def _get_story(sid: int, rank: int) -> NewsItem | None:
            try:
                r = _request_with_retry(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    raise_on_fail=False,
                )
                if r is None:
                    return None
                story = r.json()
                if not story or story.get("type") != "story":
                    return None
                return NewsItem(
                    title=story.get("title", ""),
                    url=story.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    platform=platform.name, platform_id=platform.id,
                    rank=rank, hot_value=f"{story.get('score', 0)}⬆",
                )
            except Exception:
                return None

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
    """GitHub Trending - 页面 HTML 解析"""
    try:
        resp = _request_with_retry("https://github.com/trending")
        html = resp.text
        items: list[NewsItem] = []

        # 按 article 标签分割
        articles = re.findall(r'<article class="Box-row[^"]*">(.*?)</article>', html, re.DOTALL)
        if not articles:
            # 备用：按 Box-row 分割
            articles = html.split('class="Box-row')
            articles = articles[1:] if len(articles) > 1 else []

        for i, article in enumerate(articles[:platform.max_items]):
            # 提取仓库路径 href="/owner/repo"
            href_match = re.search(r'<a\s+href="(/[^/]+/[^"]+)"', article)
            if not href_match:
                continue
            repo_path = href_match.group(1).strip()
            full_name = repo_path.strip("/")

            # 提取描述
            desc = ""
            desc_match = re.search(r'<p[^>]*>([^<]+)</p>', article)
            if desc_match:
                desc = desc_match.group(1).strip()

            # 提取今日 Star
            stars_today = ""
            star_match = re.search(r'([\d,]+)\s*stars?\s*today', article, re.IGNORECASE)
            if star_match:
                stars_today = star_match.group(1)

            title = f"{full_name}: {desc}" if desc else full_name

            items.append(NewsItem(
                title=title,
                url=f"https://github.com{repo_path}",
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
                hot_value=f"⭐{stars_today} today" if stars_today else "",
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_reddit(platform: PlatformConfig) -> list[NewsItem]:
    """Reddit Popular - 需要合适的 User-Agent"""
    try:
        resp = _request_with_retry(
            "https://www.reddit.com/r/popular.json?limit=30&t=day",
            headers={
                "User-Agent": "TrendPulse/1.0 (GitHub Actions; +https://github.com/821920046/TrendPulse)",
                "Accept": "application/json",
            },
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
                platform=platform.name, platform_id=platform.id,
                rank=i + 1,
                hot_value=f"⬆{ups:,}" if ups else "",
                category=subreddit,
            ))

        logger.info("✅ [%s] 抓取到 %d 条", platform.name, len(items))
        return items
    except Exception as e:
        logger.error("❌ [%s] 抓取失败: %s", platform.name, e)
        return []


def _fetch_rss_generic(platform: PlatformConfig) -> list[NewsItem]:
    """通用 RSS/Atom Feed 抓取"""
    if not platform.url:
        logger.warning("⚠️  [%s] 未配置 RSS URL，跳过", platform.name)
        return []

    try:
        resp = _request_with_retry(platform.url)
        feed = feedparser.parse(resp.content)

        items: list[NewsItem] = []
        for i, entry in enumerate(feed.entries[:platform.max_items]):
            title = unescape(entry.get("title", "")).strip()
            if not title:
                continue
            link = entry.get("link", "")

            items.append(NewsItem(
                title=title, url=link,
                platform=platform.name, platform_id=platform.id,
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

_FETCHER_MAP: dict[str, Callable[[PlatformConfig], list[NewsItem]]] = {
    "zhihu": _fetch_zhihu,
    "weibo": _fetch_weibo,
    "baidu": _fetch_baidu,
    "toutiao": _fetch_toutiao,
    "bilibili": _fetch_bilibili,
    "douyin": _fetch_douyin,
    "wallstreetcn": _fetch_wallstreetcn,
    "hackernews": _fetch_hackernews,
    "github": _fetch_github_trending,
    "reddit": _fetch_reddit,
    "producthunt": _fetch_rss_generic,
    "rss": _fetch_rss_generic,
}


def fetch_all(platforms: list[PlatformConfig], max_workers: int = 6) -> dict[str, list[NewsItem]]:
    """
    并发抓取所有已启用平台的热点数据。

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
