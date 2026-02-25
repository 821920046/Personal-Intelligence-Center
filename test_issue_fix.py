import sys
import os

# 确保能导入 src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.formatter import _safe_byte_truncate, _format_item, _split_to_messages
from src.models import NewsItem

def test_truncate():
    print("--- 测试字节级安全截断 ---")
    text = "你好世界 Hello World"
    # "你好世界" 每个字 3 字节，共 12 字节
    # 如果截断到 4 字节，应该只保留 "你" (3字节)
    res = _safe_byte_truncate(text, 4)
    print(f"截断前: {text} | 截断到 4 字节: '{res}'")
    assert res == "你"
    
    res = _safe_byte_truncate(text, 5)
    print(f"截断到 5 字节: '{res}'")
    assert res == "你"

    res = _safe_byte_truncate(text, 6)
    print(f"截断到 6 字节: '{res}'")
    assert res == "你好"
    print("✅ 截断逻辑正确\n")

def test_large_item():
    print("--- 测试超长单项消息分段 ---")
    header = "Header"
    # 构造一个单项内容就超过 4000 字节的 NewsItem
    long_content = "中" * 2000 # 6000 字节
    item = NewsItem(
        title="测试超长标题",
        url="https://example.com",
        platform="Test",
        platform_id="test",
        rank=1,
        content=long_content
    )
    
    # 格式化
    line = _format_item(item, True, True, True, True)
    print(f"格式化后单行长度 (bytes): {len(line.encode('utf-8'))}")
    
    # 分段
    messages = _split_to_messages(header, [line])
    print(f"分段数量: {len(messages)}")
    for i, msg in enumerate(messages):
        msg_len = len(msg.encode('utf-8'))
        print(f"消息 {i+1} 长度: {msg_len} bytes")
        assert msg_len <= 4096
    
    print("✅ 分段逻辑正确 (能处理顽固长行)\n")

if __name__ == "__main__":
    try:
        test_truncate()
        test_large_item()
        print("🎉 所有测试通过！")
    except AssertionError as e:
        print(f"❌ 测试失败")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 运行错误: {e}")
        sys.exit(1)
