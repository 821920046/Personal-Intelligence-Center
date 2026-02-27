"""
浏览器引擎模块 - 利用 Playwright 抓取动态网页或处理反爬
"""

import logging
import asyncio
from typing import Optional, Any
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class PlaywrightEngine:
    def __init__(self, headless: bool = True):
        self.headless = headless

    async def fetch_page_content(self, url: str, wait_selector: Optional[str] = None, timeout: int = 30000) -> Optional[str]:
        """
        使用无头浏览器加载网页并返回 HTML 内容
        """
        async with async_playwright() as p:
            try:
                # 启动浏览器 (优先使用 Chromium)
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                logger.info("🌐 正在通过浏览器加载: %s", url)
                await page.goto(url, wait_until="networkidle", timeout=timeout)
                
                if wait_selector:
                    await page.wait_for_selector(wait_selector, timeout=timeout)
                
                # 获取渲染后的页面源码
                content = await page.content()
                await browser.close()
                return content
            except Exception as e:
                logger.error("Playwright 抓取失败 [%s]: %s", url, e)
                return None

def run_playwright_fetch(url: str, wait_selector: Optional[str] = None) -> Optional[str]:
    """同步包装器，供同步代码调用"""
    try:
        engine = PlaywrightEngine()
        return asyncio.run(engine.fetch_page_content(url, wait_selector))
    except Exception as e:
        logger.error("运行 Playwright 同步包装器失败: %s", e)
        return None
