"""
翻译模块 - 为国际资讯提供自动中文翻译
采用基于 Google Translate 镜像 API 的轻量级实现，无需 API Key。
"""

import logging
import re
from urllib.parse import quote
import requests
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# 翻译服务地址（Google 镜像）
# 这些是常用的公开翻译接口
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=zh-CN&dt=t&q={text}"


def translate_text(text: str) -> str:
    """
    将文本翻译为中文。
    """
    if not text or not text.strip():
        return text

    # 判断是否包含中文字符，如果包含则认为不需要翻译
    if re.search(r'[\u4e00-\u9fa5]', text):
        return text

    try:
        url = TRANSLATE_URL.format(text=quote(text))
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        # Google Translate API 返回格式: [[["翻译文本", "源文本", ...]], ...]
        data = resp.json()
        translated_parts = [part[0] for part in data[0] if part[0]]
        translated_text = "".join(translated_parts)
        
        return translated_text
    except Exception as e:
        logger.warning("翻译失败 (%s): %s", text[:20], e)
        return text


def translate_batch(texts: list[str], max_workers: int = 5) -> list[str]:
    """
    并发批量翻译。
    """
    if not texts:
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(translate_text, texts))
    
    return results
