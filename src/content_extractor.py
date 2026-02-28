"""
正文提取模块 - 利用 trafilatura 提取网页核心正文
"""

import logging
from typing import Optional
import trafilatura

logger = logging.getLogger(__name__)

def extract_full_text(url: str) -> Optional[str]:
    """
    抓取并提取指定 URL 的网页正文内容。
    """
    if not url:
        return None
        
    try:
        # 1. 下载网页，增加自定义 User-Agent 避免 403
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        # 尝试先用自带工具库抓取
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            # 如果被防御机制拦截导致下载失败，切换备用 requests 发包机制伪装绕过
            import requests
            try:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                downloaded = resp.text
            except Exception as http_err:
                logger.warning("尝试代理请求依然无法下载网页内容: %s - %s", url, http_err)
                return None
            
        # 2. 提取正文 (剔除广告、导航等干扰)
        # include_comments=False 避免评论干扰
        # include_tables=True 保留表格信息
        content = trafilatura.extract(
            downloaded, 
            include_comments=False, 
            include_tables=True,
            no_fallback=False
        )
        
        if not content:
            logger.warning("未能从网页中提取到有效正文: %s", url)
            return None
            
        return content.strip()
        
    except Exception as e:
        logger.error("网页正文提取异常 [%s]: %s", url, e)
        return None
