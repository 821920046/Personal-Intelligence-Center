"""
缓存模块 - 用于存储已发送的新闻 URL，实现消息去重
"""

import json
import logging
import time
from pathlib import Path
from hashlib import md5

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_file: str | Path, expire_days: int = 7):
        self.cache_file = Path(cache_file)
        self.expire_days = expire_days
        self.expire_seconds = expire_days * 24 * 3600
        self.data: dict[str, float] = self._load()

    def _load(self) -> dict[str, float]:
        """从文件加载缓存"""
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 清理过期条目
                now = time.time()
                return {k: v for k, v in data.items() if now - v < self.expire_seconds}
        except Exception as e:
            logger.error("加载缓存失败: %s", e)
            return {}

    def save(self):
        """保存当前缓存到文件"""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("保存缓存失败: %s", e)

    def is_seen(self, url: str) -> bool:
        """检查 URL 是否已发送过"""
        if not url:
            return False
        # 对超长 URL 进行哈希处理
        key = md5(url.encode("utf-8")).hexdigest() if len(url) > 100 else url
        return key in self.data

    def mark_seen(self, url: str):
        """将 URL 标记为已发送"""
        if not url:
            return
        key = md5(url.encode("utf-8")).hexdigest() if len(url) > 100 else url
        self.data[key] = time.time()
