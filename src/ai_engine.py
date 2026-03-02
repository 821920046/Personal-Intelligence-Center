"""
AI 引擎模块 - 提供通用的 LLM 调用能力 (支持 Gemini/OpenAI 兼容接口)
内置指数退避重试机制，应对 429 限流。
"""

import logging
import os
import time
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)

# Google 原生 API v1beta 基础路径
_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

# 重试配置
_MAX_RETRIES = 3
_BASE_DELAY = 2.0  # 首次重试等待秒数，后续指数增长

# Embedding 模型候选列表（按优先级排列，依次尝试）
_EMBEDDING_MODELS = ["text-embedding-004", "embedding-001"]


def _is_google_native(base_url: str) -> bool:
    """判断是否走 Google 原生协议（googleapis 域名且不含 /openai 后缀）"""
    return "googleapis.com" in base_url and not base_url.rstrip("/").endswith("/openai")


def _post_with_retry(url: str, headers: dict, payload: dict, timeout: int = 30) -> requests.Response:
    """
    带指数退避重试的 HTTP POST 请求。
    仅对 429 (Too Many Requests) 和 5xx 进行重试。
    """
    last_resp = None
    for attempt in range(_MAX_RETRIES):
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            delay = _BASE_DELAY * (2 ** attempt)
            logger.warning(
                "请求返回 %d，%d/%d 次重试，等待 %.1f 秒... (%s)",
                resp.status_code, attempt + 1, _MAX_RETRIES, delay, url,
            )
            last_resp = resp
            time.sleep(delay)
            continue
        return resp
    # 所有重试耗尽，返回最后一次响应
    return last_resp  # type: ignore[return-value]


class AIEngine:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash", base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.model = model
        raw_url = base_url or os.environ.get("AI_BASE_URL", "")
        self.base_url = raw_url.rstrip("/") if raw_url else _GOOGLE_API_BASE
        # 缓存已验证可用的 Embedding 模型名称
        self._verified_embedding_model: Optional[str] = None
        logger.info("AI 引擎初始化: model=%s, base_url=%s", self.model, self.base_url)

    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容（内置重试机制）"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None

        try:
            if _is_google_native(self.base_url):
                url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7},
                }
            else:
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}

            logger.debug("AI generate_content 请求: %s", url)
            resp = _post_with_retry(url, headers, payload, timeout=30)

            if resp.status_code == 404:
                logger.error("AI 生成内容失败: 404 端点未找到 (%s)", url)
                return None
            if resp.status_code == 429:
                logger.error("AI 生成内容失败: 429 限流，已用尽重试次数")
                return None

            resp.raise_for_status()
            data = resp.json()

            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            return None

        except Exception as e:
            logger.error("AI 生成内容失败: %s", e)
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示（自动尝试多个 Embedding 模型）"""
        if not self.api_key:
            return None

        try:
            if _is_google_native(self.base_url) or (
                "googleapis.com" in self.base_url and self.base_url.rstrip("/").endswith("/openai")
            ):
                native_base = self.base_url.rstrip("/").replace("/openai", "")
                headers = {"Content-Type": "application/json"}
                payload = {"content": {"parts": [{"text": text}]}}

                # 如果已验证过可用模型，直接使用
                if self._verified_embedding_model:
                    return self._call_google_embedding(
                        native_base, self._verified_embedding_model, headers, payload
                    )

                # 依次尝试候选模型
                for emb_model in _EMBEDDING_MODELS:
                    result = self._call_google_embedding(native_base, emb_model, headers, payload)
                    if result is not None:
                        self._verified_embedding_model = emb_model
                        logger.info("✅ Embedding 模型验证成功: %s", emb_model)
                        return result
                    logger.warning("Embedding 模型 %s 不可用，尝试下一个...", emb_model)

                logger.error("所有 Embedding 模型均不可用: %s", _EMBEDDING_MODELS)
                return None
            else:
                url = f"{self.base_url}/embeddings"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"input": text, "model": "text-embedding-3-small"}

                resp = _post_with_retry(url, headers, payload, timeout=20)
                if resp.status_code in (404, 429):
                    logger.error("获取 Embedding 失败: %d (%s)", resp.status_code, url)
                    return None

                resp.raise_for_status()
                data = resp.json()
                if "data" in data and len(data["data"]) > 0:
                    return data["data"][0]["embedding"]
                return None

        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None

    def _call_google_embedding(
        self, native_base: str, emb_model: str, headers: dict, payload: dict
    ) -> Optional[List[float]]:
        """调用 Google 原生 Embedding 端点（单模型）"""
        url = f"{native_base}/models/{emb_model}:embedContent?key={self.api_key}"
        resp = _post_with_retry(url, headers, payload, timeout=20)

        if resp.status_code == 404:
            return None  # 模型不存在，交给调用方尝试下一个
        if resp.status_code == 429:
            logger.warning("Embedding 请求被限流 (429)，模型: %s", emb_model)
            return None

        resp.raise_for_status()
        data = resp.json()
        if "embedding" in data and "values" in data["embedding"]:
            return data["embedding"]["values"]
        return None
