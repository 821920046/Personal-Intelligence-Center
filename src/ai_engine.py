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
        
        # 默认使用官方新版的囊括 openai 兼容协议的 endpoint，以便能够一站式统一处理参数与避免路径 404
        default_base = "https://generativelanguage.googleapis.com/v1beta/openai"
        self.base_url = (base_url or os.environ.get("AI_BASE_URL", default_base)).rstrip('/')
        
        # 对于国内反代：如果包含 googleapis 但是没有加 v1beta/openai 后缀，强制修复它
        if "generativelanguage.googleapis.com" in self.base_url and not self.base_url.endswith("openai"):
            self.base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        
    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None
            
        try:
            # 统一走 OpenAI 兼容协议
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                # "max_tokens": 1000  # 如果需要可放开限制
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 404:
                logger.error(f"AI 生成内容失败: 404 端点未找到 ({url})，请检查代理地址是否正确匹配 OpenAI 格式。")
                return None
                
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
            # 统一使用 OpenAI 的 Embeddings 端点结构
            url = f"{self.base_url.replace('/chat/completions', '')}/embeddings"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 如果使用 Gemini 官方提供的兼容 endpoint，则它对应的模型别名
            # 需要在传递时进行适配。对于 OpenAI，可默认为 text-embedding-3-small
            embed_model = "text-embedding-004" if "googleapis" in self.base_url else "text-embedding-3-small"
            
            payload = {"input": text, "model": embed_model}
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            resp.raise_for_status()
            
            data = resp.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['embedding']
            return None
        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None
