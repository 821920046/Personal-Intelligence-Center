import sys
import os
import re
from html import unescape

# 模拟环境以测试清洗逻辑
def _clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'<svg[^>]*>.*?</svg>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<(p|br|div)[^>]*>', '\n', text)
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    cleaned = unescape(text).strip()
    cleaned = re.sub(r'[a-z0-9\-]+="[^"]*"\s*', ' ', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def test_svg_cleaning():
    dirty_text = 'VectifyAI/PageIndex" data-view-component="true" class="Link"><svg aria-hidden="true" ...>...</svg>[Python]'
    cleaned = _clean_html(dirty_text)
    print(f"Original: {dirty_text}")
    print(f"Cleaned:  {cleaned}")
    assert "svg" not in cleaned.lower()
    assert "data-view-component" not in cleaned
    assert "class=" not in cleaned
    print("Test passed!")

if __name__ == "__main__":
    test_svg_cleaning()
