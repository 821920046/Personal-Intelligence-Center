"""
AI 引擎模块 - 提供通用的 LLM 调用能力
支持 SiliconFlow / Gemini / OpenAI 兼容接口
内置全局请求节流 + 指数退避重试机制
"""

import logging
import os
import time
import threading
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)

# ── 默认配置 ──
# SiliconFlow 作为默认平台（免费、中文能力强、速率宽松）
_DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
_DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"

# SiliconFlow 免费 Embedding 模型（中文优化）
_SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"

# Google 原生 API v1beta 基础路径（仅在使用 Google API 时生效）
_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_GOOGLE_EMBEDDING_MODELS = ["text-embedding-004", "embedding-001"]

# 重试配置
_MAX_RETRIES = 3
_BASE_DELAY = 3.0

# 全局节流配置（SiliconFlow 比 Gemini 宽松，1 秒即可）
_MIN_REQUEST_INTERVAL = 1.0

# 全局节流锁和上次请求时间戳
_throttle_lock = threading.Lock()
_last_request_time = 0.0


def _is_google_native(base_url: str) -> bool:
    """判断是否走 Google 原生协议"""
    return "googleapis.com" in base_url and not base_url.rstrip("/").endswith("/openai")


def _throttle() -> None:
    """全局请求节流"""
    global _last_request_time
    with _throttle_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            wait = _MIN_REQUEST_INTERVAL - elapsed
            time.sleep(wait)
        _last_request_time = time.time()


def _post_with_retry(url: str, headers: dict, payload: dict, timeout: int = 30) -> requests.Response:
    """带全局节流 + 指数退避重试的 HTTP POST 请求"""
    last_resp = None
    for attempt in range(_MAX_RETRIES):
        _throttle()
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = _BASE_DELAY * (2 ** attempt)
            logger.warning(
                "请求返回 %d，%d/%d 次重试，等待 %.1f 秒...",
                resp.status_code, attempt + 1, _MAX_RETRIES, delay,
            )
            last_resp = resp
            time.sleep(delay)
            continue
        return resp
    return last_resp  # type: ignore[return-value]


class AIEngine:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.model = model
        raw_url = base_url or os.environ.get("AI_BASE_URL", "")
        self.base_url = raw_url.rstrip("/") if raw_url else _DEFAULT_BASE_URL
        self._verified_embedding_model: Optional[str] = None
        logger.info("AI 引擎初始化: model=%s, base_url=%s", self.model, self.base_url)

    # ──────────────────── 文本生成 ────────────────────

    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None

        try:
            if _is_google_native(self.base_url):
                # Google 原生协议
                url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7},
                }
            else:
                # OpenAI 兼容协议（SiliconFlow / DeepSeek / 自建反代等）
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                }

            resp = _post_with_retry(url, headers, payload, timeout=30)

            if resp.status_code in (404, 429):
                logger.error("AI 生成内容失败: %d (%s)", resp.status_code, url)
                return None

            resp.raise_for_status()
            data = resp.json()

            # 兼容 Google 原生和 OpenAI 两种返回格式
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            return None

        except Exception as e:
            logger.error("AI 生成内容失败: %s", e)
            return None

    # ──────────────────── 向量 Embedding ────────────────────

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示"""
        if not self.api_key:
            return None

        try:
            if _is_google_native(self.base_url) or (
                "googleapis.com" in self.base_url
            ):
                # Google 原生 Embedding（多模型探测）
                return self._get_google_embedding(text)
            else:
                # OpenAI 兼容 Embedding（SiliconFlow / 其他）
                return self._get_openai_embedding(text)

        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None

    def _get_openai_embedding(self, text: str) -> Optional[List[float]]:
        """通过 OpenAI 兼容接口获取 Embedding（SiliconFlow 等）"""
        # SiliconFlow 使用 BAAI/bge-large-zh-v1.5（免费中文向量模型）
        emb_model = _SILICONFLOW_EMBEDDING_MODEL if "siliconflow" in self.base_url else "text-embedding-3-small"

        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"input": text, "model": emb_model}

        resp = _post_with_retry(url, headers, payload, timeout=20)
        if resp.status_code in (404, 429):
            logger.error("获取 Embedding 失败: %d (%s)", resp.status_code, url)
            return None

        resp.raise_for_status()
        data = resp.json()
        if "data" in data and len(data["data"]) > 0:
            return data["data"][0]["embedding"]
        return None

    def _get_google_embedding(self, text: str) -> Optional[List[float]]:
        """通过 Google 原生接口获取 Embedding（多模型探测）"""
        native_base = self.base_url.rstrip("/").replace("/openai", "")
        headers = {"Content-Type": "application/json"}
        payload = {"content": {"parts": [{"text": text}]}}

        if self._verified_embedding_model:
            return self._call_google_embedding(
                native_base, self._verified_embedding_model, headers, payload
            )

        for emb_model in _GOOGLE_EMBEDDING_MODELS:
            result = self._call_google_embedding(native_base, emb_model, headers, payload)
            if result is not None:
                self._verified_embedding_model = emb_model
                logger.info("✅ Embedding 模型验证成功: %s", emb_model)
                return result
            logger.warning("Embedding 模型 %s 不可用，尝试下一个...", emb_model)

        logger.error("所有 Google Embedding 模型均不可用")
        return None

    def _call_google_embedding(
        self, native_base: str, emb_model: str, headers: dict, payload: dict
    ) -> Optional[List[float]]:
        """调用 Google 原生 Embedding 端点（单模型）"""
        url = f"{native_base}/models/{emb_model}:embedContent?key={self.api_key}"
        resp = _post_with_retry(url, headers, payload, timeout=20)

        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            logger.warning("Embedding 请求被限流 (429)，模型: %s", emb_model)
            return None

        resp.raise_for_status()
        data = resp.json()
        if "embedding" in data and "values" in data["embedding"]:
            return data["embedding"]["values"]
        return None
