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
        # 1. 下载网页
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning("无法下载网页内容: %s", url)
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
