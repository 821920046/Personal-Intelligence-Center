# 🧠 AetherNode (元神节点) | 私人智能情报中心

> **AetherNode**: An AI-native autonomous intelligence sentinel that observes, digests, and distills the global digital pulse into personalized wisdom.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Browser%20Scraping-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev)
[![AI Powered](https://img.shields.io/badge/AI-Gemini%20/%20GPT-orange?logo=google-gemini&logoColor=white)]()
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ 核心黑科技 (Core Features)

**AetherNode** 彻底重构了你获取信息的方式。它不仅是一个订阅工具，更是你的数字替身，在浩如烟海的噪音中为你精准捕捉有价值的信号。

### 1. 🔍 语义雷达 (Semantic Radar)
不再死板匹配词条。利用 **向量嵌入 (Embedding)** 技术，即便标题里没有你的关键词，只要意思沾边（例如“氢能”之于“新能源”），AetherNode 也会精准捕捉并标记为 `✨ 语义发现`。

### 2. 📖 深度精读 (Deep Reading)
告别标题党。系统会自动抓取新闻后的网页正文，让 AI 读完几千字后再为你输出一份 300 字的深度提炼。你在消息窗口内，就能掌握整个事件的来龙去脉。

### 3. 🤖 AI 三重提炼 (Tri-Tier Synthesis)
- **今日洞察 (Daily Insight)**：全网热点的全局综述，一句话看清今日焦点。
- **组摘要 (Group Summary)**：针对你关心的每个关键词组，生成浓缩动态。
- **全文综述 (Full-text AI)**：深度精读条目的模块化分析。

### 4. 🌐 强力抓取引擎 (Hybrid Scraper)
- **双模态架构**：优先轻量 API，失败时自动唤起 **Playwright 无头浏览器**。
- **全网覆盖**：知乎、微博、GitHub、Hacker News、Reddit、RSS 等 20+ 平台。
- **自动翻译**：国际资讯全量翻译为中文，消除语言障碍。

### 5. 🎨 绝美可视化看板 (Dashboard)
每次运行自动生成一个 **Apple 审美风格** 的静态 HTML 报告。完美适配深色模式，让回顾热点成为一种视觉享受。

---

## 📲 多渠道分发 (Delivery Channels)

支持同时推送到以下终端：
- **企业微信 (WeWork)**：Markdown 富文本推送。
- **Bark (iOS)**：苹果全家桶即时弹窗。
- **钉钉 (DingTalk)**：群机器人通知。

---

## 🚀 快速开始 (Quick Start)

### 1️⃣ 环境准备
```bash
git clone https://github.com/YourUsername/AetherNode.git
cd AetherNode
pip install -r requirements.txt
playwright install chromium
```

### 2️⃣ 配置文件
- `config/keywords.txt`: 填入你关心的关键词。
- `config/config.yaml`: 配置 API KEY 和通知渠道。

### 3️⃣ 运行
```bash
python main.py
```

---

## 📂 项目架构

```text
├── config/
│   ├── config.yaml       # 核心配置 (AI/通知/平台)
│   ├── keywords.txt      # 关键词订阅
│   └── cache.json        # 消息去重缓存
├── src/
│   ├── ai_engine.py      # AI 后端 (Gemini/GPT/Embedding)
│   ├── summarizer.py     # AI 摘要逻辑
│   ├── semantic.py       # 语义向量雷达
│   ├── content_extractor.py # 网页正文抓取
│   ├── playwright_engine.py # 无头浏览器驱动
│   ├── fetcher.py        # 多平台数据抓取
│   ├── dashboard.py      # HTML 看板生成
│   └── notifier.py       # 多渠道通知系统
└── main.py              # 主入口
```

---

## 📄 开源协议

基于 **MIT License** 开源。
