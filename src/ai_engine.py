"""
AI 引擎模块 - 提供通用的 LLM 调用能力 (支持 Gemini/OpenAI 兼容接口)
"""

import logging
import os
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)

# Google 原生 API v1beta 基础路径
_GOOGLE_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _is_google_native(base_url: str) -> bool:
    """判断是否走 Google 原生协议（googleapis 域名且不含 /openai 后缀）"""
    return "googleapis.com" in base_url and not base_url.rstrip("/").endswith("/openai")


def _is_openai_compat(base_url: str) -> bool:
    """判断是否走 OpenAI 兼容协议（含 /openai 后缀 或 非 Google 域名）"""
    return base_url.rstrip("/").endswith("/openai") or "googleapis.com" not in base_url


class AIEngine:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash", base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.model = model
        # 优先使用用户传入的 base_url，其次环境变量，最后回落到 Google 原生端点
        raw_url = base_url or os.environ.get("AI_BASE_URL", "")
        self.base_url = raw_url.rstrip("/") if raw_url else _GOOGLE_API_BASE
        logger.info("AI 引擎初始化: model=%s, base_url=%s", self.model, self.base_url)

    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None

        try:
            if _is_google_native(self.base_url):
                # ── Google 原生协议 ──
                url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7},
                }
            else:
                # ── OpenAI 兼容协议（含 /openai 后缀、自建反代等） ──
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}

            logger.debug("AI generate_content 请求: %s", url)
            resp = requests.post(url, json=payload, headers=headers, timeout=30)

            if resp.status_code == 404:
                logger.error("AI 生成内容失败: 404 端点未找到 (%s)，请检查 AI_BASE_URL 和 model 配置。", url)
                return None

            resp.raise_for_status()
            data = resp.json()

            # 兼容原生和 OpenAI 两种返回结构
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif "choices" in data:
                return data["choices"][0]["message"]["content"].strip()
            return None

        except Exception as e:
            logger.error("AI 生成内容失败: %s", e)
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示 (Embedding)"""
        if not self.api_key:
            return None

        try:
            if _is_google_native(self.base_url):
                # ── Google 原生 Embedding 端点 ──
                url = f"{self.base_url}/models/text-embedding-004:embedContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {"content": {"parts": [{"text": text}]}}
            elif "googleapis.com" in self.base_url and self.base_url.rstrip("/").endswith("/openai"):
                # ── Google API 的 OpenAI 兼容层 → 回退到原生 Embedding 路径 ──
                native_base = self.base_url.rstrip("/").replace("/openai", "")
                url = f"{native_base}/models/text-embedding-004:embedContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {"content": {"parts": [{"text": text}]}}
            else:
                # ── 第三方 OpenAI 标准 Embeddings 端点 ──
                url = f"{self.base_url}/embeddings"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"input": text, "model": "text-embedding-3-small"}

            logger.debug("AI get_embedding 请求: %s", url)
            resp = requests.post(url, json=payload, headers=headers, timeout=20)

            if resp.status_code == 404:
                logger.error("获取 Embedding 失败: 404 端点未找到 (%s)，请确认 AI 配置。", url)
                return None

            resp.raise_for_status()
            data = resp.json()

            if "embedding" in data and "values" in data["embedding"]:
                return data["embedding"]["values"]
            elif "data" in data and len(data["data"]) > 0:
                return data["data"][0]["embedding"]
            return None

        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None
