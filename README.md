# 📡 TrendPulse

> 多平台热点订阅推送工具 —— 自定义关键词，每日精准推送到企业微信

[![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-定时推送-2088FF?logo=github-actions&logoColor=white)](https://github.com/features/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## ✨ 核心功能

- 🌐 **20+ 平台聚合** - 国内热搜 + 国际科技资讯一网打尽
- 🎯 **关键词订阅** - 自定义关注话题，只推送你关心的内容
- 🤖 **企业微信推送** - Markdown 富文本直达手机
- ⏰ **每日定时** - GitHub Actions 免费运行，零服务器成本
- 🔧 **灵活配置** - YAML 配置 + 关键词语法，3 分钟上手

## 📊 支持平台

| 分类 | 平台 |
|------|------|
| 🇨🇳 国内热搜 | 知乎、微博、百度、今日头条、B站、抖音、贴吧 |
| 🇨🇳 国内财经 | 华尔街见闻、财联社、澎湃新闻、凤凰网 |
| 🌍 科技社区 | **Hacker News**、**Product Hunt**、**GitHub Trending** |
| 🌍 社交媒体 | **Reddit Popular** |
| 🌍 国际媒体 | **TechCrunch**、**The Verge**、**Ars Technica**、**BBC News**、**Reuters** |

## 🚀 快速开始

### 30 秒部署

#### 1️⃣ 获取项目代码

点击本仓库右上角 **[Use this template]** → **Create a new repository**

> ⚠️ 推荐 Template 方式，不建议 Fork（避免 Actions 权限问题）

#### 2️⃣ 配置企业微信 Webhook

1. 打开企业微信 → 进入目标群聊
2. 群设置 → **消息推送** → **添加** → 得到 Webhook URL
3. 在你的 GitHub 仓库中：**Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Secret |
|------|--------|
| `WEWORK_WEBHOOK_URL` | 你的企业微信机器人 Webhook URL |
| `WEWORK_MSG_TYPE` | （可选）设为 `text` 发送纯文本，默认 `markdown` |

#### 3️⃣ 自定义关键词

编辑 `config/keywords.txt`，填入你关心的关键词：

```
AI 人工智能 ChatGPT GPT 大模型
Python 开源 GitHub
特斯拉 马斯克 @5
华为 苹果 +手机 !水果
```

#### 4️⃣ 完成！

- 每天北京时间 **07:00** 和 **18:00** 自动推送
- 也可以在 **Actions** 页面手动触发测试

---

## 📝 关键词语法

| 语法 | 示例 | 说明 |
|------|------|------|
| 普通词 | `AI 人工智能` | 命中任一词即推送（OR） |
| 必须词 `+` | `华为 +手机` | 必须同时命中（AND） |
| 过滤词 `!` | `苹果 !水果` | 命中则排除 |
| 数量限制 `@` | `特斯拉 @5` | 最多推送 5 条 |
| 正则 `//` | `/\bGPT\b/` | 精确匹配 |
| 全局过滤 | `[GLOBAL_FILTER]` | 该区域下的词全局排除 |

**完整示例：**

```
[GLOBAL_FILTER]
广告
推广

[WORD_GROUPS]
AI 人工智能 ChatGPT GPT 大模型 LLM
Python 开源 GitHub
科技 互联网 芯片
华为 苹果 +手机 !水果 @10
/\bGPT\b/ 大语言模型
```

## ⚙️ 平台配置

编辑 `config/config.yaml` 的 `platforms` 部分，通过 `enabled: true/false` 开关各平台：

```yaml
platforms:
  - id: "hackernews"
    name: "Hacker News"
    type: "hackernews"
    enabled: true       # ← 改为 false 即关闭
    max_items: 20

  - id: "techcrunch"
    name: "TechCrunch"
    type: "rss"
    url: "https://techcrunch.com/feed/"
    enabled: true
    max_items: 15
```

### 平台类型说明

| type | 说明 | 示例平台 |
|------|------|----------|
| `newsnow` | NewsNow API 抓取 | 知乎、微博、百度、头条 |
| `hackernews` | HN 官方 API | Hacker News |
| `github` | GitHub Trending 页面 | GitHub Trending |
| `reddit` | Reddit JSON API | Reddit Popular |
| `producthunt` | Product Hunt RSS | Product Hunt |
| `rss` | 通用 RSS/Atom | TechCrunch、BBC、Reuters |

## ⏰ 修改推送时间

编辑 `.github/workflows/push.yml` 中的 `cron` 表达式：

```yaml
schedule:
  # 北京时间 = UTC + 8，需要减去 8 小时
  - cron: "0 23 * * *"   # 北京时间 07:00
  - cron: "0 10 * * *"   # 北京时间 18:00
```

> ⚠️ GitHub Actions 时间可能有 ±15 分钟偏差

## 📂 项目结构

```
TrendPulse/
├── .github/workflows/
│   └── push.yml          # GitHub Actions 定时任务
├── config/
│   ├── config.yaml       # 平台与显示配置
│   └── keywords.txt      # 关键词订阅
├── src/
│   ├── models.py         # 数据模型
│   ├── fetcher.py        # 数据抓取（双引擎）
│   ├── filter.py         # 关键词过滤
│   ├── formatter.py      # 消息格式化
│   └── notifier.py       # 企业微信推送
├── main.py               # 主入口
├── requirements.txt      # Python 依赖
└── README.md
```

## 📄 License

MIT License
