# 🧠 私人智能情报中心 (Personal Intelligence Center)

> **私人智能情报中心**: 一个懂你意图、能读全文、多端同步的终极热点资讯聚合与 AI 分析系统。

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-抓取增强-45ba4b?logo=playwright&logoColor=white)](https://playwright.dev)
[![AI Powered](https://img.shields.io/badge/AI-Gemini%20/%20GPT-orange?logo=google-gemini&logoColor=white)]()
[![GitHub Actions](https://img.shields.io/badge/Actions-定时任务-2088FF?logo=github-actions&logoColor=white)]()

---

## ✨ 核心黑科技 (Core Features)

本系统不仅是一个爬虫，它更是一个私人的“智能情报大脑”。依托 AI 能力，它实现了从“看到”到“看懂”的跨越。

- 🔍 **语义雷达 (Semantic Radar)**：利用向量嵌入技术，自动捕捉语义相关的隐藏热点。
- 📖 **深度精读 (Deep Reading)**：自动抓取正文全文，AI 为你提供 300 字深度提炼。
- 🤖 **AI 三重综述**：今日洞察、组摘要、全文精读，分层级过滤噪音。
- 🌐 **强抓取引擎**：Playwright 无头浏览器后备，无视 JS 渲染与常见反爬。
- 🎨 **绝美看板**：自动生成 Apple 风格 HTML 报告，支持深色模式。
- 📲 **多端推送**：企业微信、Bark (iOS)、钉钉三端同步。

---

## � 部署指南 (Deployment)

### 方案 A：GitHub Actions 自动运行（推荐，零成本，免服务器）

1. **Fork/使用模板**：
   - 点击右上角 `Use this template` 或 `Fork` 到你的账号。
2. **配置 Secrets**（重要）：
   - 进入 GitHub 仓库 `Settings` -> `Secrets and variables` -> `Actions`。
   - 点击 `New repository secret` 添加以下必要变量：
     - `AI_API_KEY`: 你的 Google Gemini (推荐，免费额度高) 或 OpenAI API Key。
     - `WEWORK_WEBHOOK_URL`: 企业微信机器人 Webhook 地址（如使用此渠道）。
     - `BARK_DEVICE_KEY`: Bark 推送 Key（如使用此渠道）。
3. **启用 Actions**：
   - 进入 `Actions` 页面，手动确认 `Enable Actions`。
   - 默认配置为每天北京时间 **07:00** 和 **18:00** 运行。

### 方案 B：本地手动运行

1. **克隆项目**：
   ```bash
   git clone https://github.com/YourUsername/IntelligenceCenter.git
   cd IntelligenceCenter
   ```
2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
3. **配置环境变量**：
   - 在本地创建 `.env` 文件或直接设置系统环境变量：
     ```bash
     export AI_API_KEY="你的KEY"
     export WEWORK_WEBHOOK_URL="你的URL"
     ```
4. **启动程序**：
   ```bash
   python main.py
   ```

---

## 🛠️ 使用教程 (Usage)

### 1. 配置你想看的内容
编辑 `config/keywords.txt`。支持复杂的匹配语法：
- **普通词**：`华为 苹果` (命中其一即推送)
- **必选词**：`+手机` (必须包含)
- **排除词**：`!水果` (包含则跳过)
- **数量限制**：`@5` (该组最多推 5 条)
- **全局过滤**：在 `[GLOBAL_FILTER]` 下填写的词将全局生效。

### 2. 深度定制系统行为
编辑 `config/config.yaml`：
- **AI 偏好**：在 `ai_summarization` 中开启/关闭 `enable_deep_reading` (深度精读)。
- **语义门槛**：修改 `semantic_radar` 的 `threshold`（值越高过滤越严）。
- **推送渠道**：在 `notifications` 中开关企业微信、Bark 或钉钉。
- **可视化设置**：开启 `enable_dashboard` 即可每次运行生成 HTML 看板。

### 3. 查看可视化看板
运行结束后，打开项目根目录下的 `output/dashboard.html`，即可看到生成的精美网页日报。

---

## 📂 项目架构

```text
├── config/
│   ├── config.yaml       # 系统逻辑配置
│   ├── keywords.txt      # 关键词监控名单
│   └── cache.json        # 自动去重数据
├── src/                  # 核心源代码
├── main.py              # 主入口
└── .github/workflows/   # 云端自动运行脚本
```

---

## 📄 开源协议

基于 **MIT License** 开源。
