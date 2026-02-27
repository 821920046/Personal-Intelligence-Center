"""
AI 引擎模块 - 提供通用的 LLM 调用能力 (支持 Gemini/OpenAI 兼容接口)
"""

import logging
import os
from typing import Optional, List
import requests

logger = logging.getLogger(__name__)

class AIEngine:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash", base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.model = model
        # 默认支持 Gemini API 格式，如果 base_url 包含 openai 则切换逻辑
        self.base_url = base_url or os.environ.get("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1/models")
        
    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None
            
        try:
            if "googleapis" in self.base_url:
                # Gemini 协议
                url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 1000,
                    }
                }
                resp = requests.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                # OpenAI 兼容协议
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                return data['choices'][0]['message']['content'].strip()
                
        except Exception as e:
            logger.error("AI 生成内容失败: %s", e)
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示 (Embedding)"""
        if not self.api_key:
            return None
        try:
            if "googleapis" in self.base_url:
                # Gemini Embedding
                url = f"https://generativelanguage.googleapis.com/v1/models/text-embedding-004:embedContent?key={self.api_key}"
                payload = {
                    "content": {"parts": [{"text": text}]}
                }
                resp = requests.post(url, json=payload, timeout=20)
                resp.raise_for_status()
                return resp.json()['embedding']['values']
            else:
                # OpenAI Embedding
                url = f"{self.base_url.replace('/chat/completions', '')}/embeddings"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"input": text, "model": "text-embedding-3-small"}
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                resp.raise_for_status()
                return resp.json()['data'][0]['embedding']
        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None
