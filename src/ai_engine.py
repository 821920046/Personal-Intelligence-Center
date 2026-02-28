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
        # 使用通用传入的 base_url，如果没填则默认为原生 Google 根路径
        # 不再强制后缀加 /openai，而是在后续请求具体构建时区分
        self.base_url = (base_url or os.environ.get("AI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")).rstrip('/')
        
    def generate_content(self, prompt: str) -> Optional[str]:
        """生成文本内容"""
        if not self.api_key:
            logger.warning("AI_API_KEY 未设置，跳过 AI 处理")
            return None
            
        try:
            # 判断逻辑：根据 base_url 后缀或者域名类型决定通讯协议
            if self.base_url.endswith("/openai") or ("googleapis.com" not in self.base_url and "/v1beta/openai" in self.base_url):
                # 已经是完整的带有 openai 兼容层的路径
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}
            elif "googleapis.com" in self.base_url:
                # 走原生 Google API 协议
                url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7}
                }
            else:
                # 用户传入自建反代等情况，默认按照三方 OpenAI 标准协议对待
                url = f"{self.base_url}/chat/completions"
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7}

            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if resp.status_code == 404:
                logger.error(f"AI 生成内容失败: 404 端点未找到 ({url})，请查核您的 AI_BASE_URL 是否正确指引。")
                return None
                
            resp.raise_for_status()
            data = resp.json()
            
            # 兼容原生和三方两种返回结构
            if "candidates" in data:
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            elif "choices" in data:
                return data['choices'][0]['message']['content'].strip()
            return None
                
        except Exception as e:
            logger.error("AI 生成内容失败: %s", e)
            return None

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本的向量表示 (Embedding)"""
        if not self.api_key:
            return None
            
        try:
            # 判断是否为 Google 兼容 API 代理 (不论是原生 googleapis 还是某些包含 v1beta 的反代)
            # 例如: https://api.proxy.com/v1beta/openai
            is_google_api = "googleapis.com" in self.base_url or "v1beta" in self.base_url
            
            if is_google_api:
                # 强制回退原生 Embedding 协议路径 (清除 openai 后缀)
                clean_base = self.base_url.replace("/openai", "")
                url = f"{clean_base}/models/text-embedding-004:embedContent?key={self.api_key}"
                payload = {"content": {"parts": [{"text": text}]}}
                
                resp = requests.post(url, json=payload, timeout=20)
                if resp.status_code == 404:
                    logger.error(f"获取 Embedding 失败: 404 端点未找到 ({url})，确保使用有效的 Gemini API。")
                    return None
                    
                resp.raise_for_status()
                data = resp.json()
                if 'embedding' in data and 'values' in data['embedding']:
                    return data['embedding']['values']
                return None
            else:
                # 统一使用常规第三方 OpenAI Embeddings 端点结构
                url = f"{self.base_url}/embeddings"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"input": text, "model": "text-embedding-3-small"}
                
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                if resp.status_code == 404:
                    logger.error(f"获取 Embedding 失败: 404 端点未找到 ({url})，请确认代理地址是否正确匹配 OpenAI 格式。")
                    return None
                    
                resp.raise_for_status()
                data = resp.json()
                if 'data' in data and len(data['data']) > 0:
                    return data['data'][0]['embedding']
                return None
        except Exception as e:
            logger.error("获取 Embedding 失败: %s", e)
            return None
