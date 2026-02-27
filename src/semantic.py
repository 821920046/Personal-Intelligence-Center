"""
语义模块 - 提供基于向量 Embedding 的相似度计算与过滤
"""

import logging
from typing import List, Optional, Dict
import math

from src.ai_engine import AIEngine
from src.models import NewsItem

logger = logging.getLogger(__name__)

class SemanticEngine:
    def __init__(self, ai_engine: AIEngine, threshold: float = 0.65):
        self.ai = ai_engine
        self.threshold = threshold
        self.cache: Dict[str, List[float]] = {}

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm_a = math.sqrt(sum(a * a for a in v1))
        norm_b = math.sqrt(sum(b * b for b in v2))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """获取向量封装 (带缓存)"""
        if text in self.cache:
            return self.cache[text]
        
        vector = self.ai.get_embedding(text)
        if vector:
            self.cache[text] = vector
        return vector

    def check_similarity(self, target_text: str, interest_texts: List[str]) -> tuple[bool, float]:
        """
        检查目标文本是否与兴趣列表中的任何一项语义相关。
        返回 (是否命中, 最高相似度得分)
        """
        target_vec = self.get_text_embedding(target_text)
        if not target_vec:
            return False, 0.0

        max_score = 0.0
        for interest in interest_texts:
            interest_vec = self.get_text_embedding(interest)
            if not interest_vec:
                continue
            
            score = self._cosine_similarity(target_vec, interest_vec)
            if score > max_score:
                max_score = score

        return (max_score >= self.threshold), max_score
