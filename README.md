# 🎓 Campus Guide Agent

> **为每所大学打造专属 AI 新生指南**
>
> 基于 LangChain + 通义千问 + BGE Re-Ranker 的 RAG 系统，让每所大学都能快速搭建自己的智能校园助手。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/LLM-Qwen2.5-orange" alt="LLM">
  <img src="https://img.shields.io/badge/Status-Alpha-yellow" alt="Status">
</p>

---

## ✨ 功能亮点

- 🧠 **智能 RAG 问答** — 检索增强生成，回答基于真实校园知识，不编造
- 🎯 **意图识别路由** — 问老师不会搜到美食，问食堂不会返回教学楼
- 🔄 **Re-Ranker 精排** — BGE Cross-Encoder 重排，10→3 精准筛选
- 🗺️ **路线规划** — 接入高德地图 API，步行路线一目了然
- 🇨🇳 **中文优化** — Qwen 2.5 + BGE 中文嵌入/重排模型，理解力更强
- 🔌 **插件化** — 各大学可自定义数据源爬虫（论坛/小程序/API）
- 🏫 **多大学支持** — 独立 YAML 配置，一套代码服务所有大学
- 💻 **本地 + API 双模式** — Ollama 本地免费运行，或通义千问 API
- 🎨 **Web + CLI** — Streamlit Web UI 开箱即用，也支持命令行

---

## 🚀 5 分钟上手

### 前置准备

```bash
# 1. 克隆项目
git clone https://github.com/yourname/campus-guide-agent.git
cd campus-guide-agent

# 2. 安装依赖
pip install -e ".[webui]"

# 3. 安装 Ollama（免费本地模式）
# 下载: https://ollama.com
ollama pull qwen2.5:7b

# 4. 下载嵌入和重排模型（首次运行，约 2.4GB）
python scripts/download_models.py
```

### 启动服务

```bash
# 初始化知识库（将 Markdown 文件向量化入库）
python scripts/init_db.py

# 启动 Web 界面（Chainlit）
chainlit run app/chainlit_app.py

# 或使用命令行
python -m app.cli
```

然后在浏览器打开 http://localhost:8000，开始和「小园」对话！

## 🏗️ 系统架构

```
用户问题
    ↓
┌─ 复杂度路由器 ───────────────────────────┐
│  _detect_intents(query)                  │
│  单意图 → ⚡ fast path / 多意图 → 🐢 slow │
└──────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─ FAST PATH ───────────┐  ┌─ SLOW PATH ────────────────┐
│ 单类向量检索 (BGE)    │  │ 多类交叉检索 (各取 top-5)  │
│ → Rerank (top-3)     │  │ → Rerank (top-5)            │
│ → 生成回答           │  │ → 工具调用                  │
│ ~200ms               │  │ → 综合生成回答              │
└───────────────────────┘  └─────────────────────────────┘
         ↓                          ↓
┌─ 可观测性 ────────────────────────────────────┐
│  stdout log: route / intents / latency / docs │
└───────────────────────────────────────────────┘
```

| 模块 | 状态 | 说明 |
|---|---|---|
| 复杂度自适应路由 | ✅ | 关键词匹配，单/多意图分流 |
| 向量检索 (BGE-large-zh-v1.5) | ✅ | 中文语义检索 SOTA |
| BGE Re-Ranker 精排 | ✅ | Cross-Encoder 重排，10→3 |
| LLM 生成 (Qwen 2.5) | ✅ | Ollama 本地 / DashScope API |
| 来源引用 | ✅ | Chainlit 原生引用组件 |
| 流式输出 | ✅ | Chainlit 逐字流式 |
| 工具调用 (高德路线规划) | ⚠️ | 关键词触发 → 计划改为 LLM function calling |
| Hybrid Search (向量+BM25) | 📋 | BGE 中文够用，有需求再加 |
| Agent Loop (ReAct) | 📋 | 95% 场景单跳，复杂场景升级时开启 |
| 输入/输出 Guardrail | 📋 | demo 阶段无暴露面，上线前加 |
| 评测体系 | 📋 | 计划：20 条用例 + 关键词命中率 + 延迟 |

---

## 💬 对话示例

```
你> 一餐有什么好吃的？

小园> 🍜 一餐值得推荐的好吃的可不少！

**🏆 麻辣香锅**（二楼左转第 3 个窗口）
校园性价比之王！自选菜品称重，人均 12-15 元吃到撑。
推荐搭配：午餐肉 + 豆皮 + 土豆片 + 金针菇（中辣刚好）
排队：饭点约 15 分钟

**🥟 手工水饺**（一楼右侧第 2 窗口）
阿姨每天现包，皮薄馅大。推荐三鲜馅！
小份 12 个/10 元，大份 20 个/15 元

**🍲 瓦罐汤**（一楼最左边）
瓦罐煨 4 小时，冬天来一碗排骨藕汤（15 元）超暖~

还有什么想了解的吗？😊

---

你> 张伟老师办公室在哪？

小园> 张伟教授的办公室在 **计算机楼 301** 🏢

办公时间是：
- 周二 14:00-16:00
- 周四 10:00-12:00

他的研究方向是人工智能和自然语言处理，在 ACL、EMNLP 等顶会发表 50 余篇论文。
每周组会在周三下午 2 点，也在计算机楼 301。

邮箱：zhangwei@demo.edu.cn
```

---

## 📁 项目结构

```
campus-guide-agent/
├── core/                    # 核心框架
│   ├── ingest/              # 知识入库（Markdown/网页/API 加载器 + 两轮切分）
│   ├── retrieval/           # 检索（嵌入/向量库/意图路由/Re-Ranker 重排）
│   ├── llm/                 # LLM（Qwen Ollama 本地 / DashScope API）
│   ├── tools/               # 外部工具（高德地图路线规划等）
│   └── pipeline/            # RAG 管线编排 + 提示词模板
│
├── config/                  # 🏫 可插拔大学配置
│   ├── default.yaml         # 默认配置
│   └── universities/        # 各大学独立配置
│       └── demo_university.yaml
│
├── plugins/                 # 🔌 插件化数据源
│   └── example_university/  # 示例爬虫插件
│
├── data/                    # 知识原始数据（Markdown）
│   └── demo_university/     # 演示大学示例数据
│       ├── teachers/        # 教师信息
│       ├── food/            # 美食指南
│       └── campus/          # 校园设施
│
├── app/
│   ├── cli.py               # 命令行界面
│   └── webui.py             # Streamlit Web 界面
│
├── scripts/
│   ├── init_db.py           # 知识库初始化
│   └── download_models.py   # 模型下载
│
└── tests/                   # 单元测试
```

---

## 🏫 添加你的大学

### 三步接入：

**Step 1: 创建配置文件** `config/universities/my_uni.yaml`

```yaml
university:
  name: "XX 大学"
  short_name: "my_uni"

pois:
  计算机楼: {lat: 30.5, lng: 114.4}
  第一食堂: {lat: 30.51, lng: 114.41}
  # ... 添加你的校园地标
```

**Step 2: 编写知识数据** `data/my_uni/`

```bash
data/my_uni/
├── teachers/
│   ├── 计算机学院.md
│   └── 文学院.md
├── food/
│   └── 美食指南.md
└── campus/
    └── 新生FAQ.md
```

**Step 3: 初始化并启动**

```bash
python scripts/init_db.py --university my_uni
streamlit run app/webui.py
```

### 编写自定义数据源插件

```python
# plugins/my_uni/forum_scraper.py
from core.ingest.base import DataSourcePlugin

class ForumScraper(DataSourcePlugin):
    def load(self):
        # 爬取校园论坛美食版块
        ...
    def validate(self):
        return True
```

---

## 🔧 技术架构

```
用户问题
    ↓
意图识别 (关键词匹配 + 实体提取)
    ↓
├─→ 向量检索 (BGE Embedding + Chroma, 分类过滤, top-10)
│     ↓
│   Re-Ranker 精排 (BGE Cross-Encoder, top-3)
│
├─→ 工具调用 (高德路线规划 / 自定义插件)
│
↓
Prompt 组装 (上下文 + 工具结果 + 系统提示词)
    ↓
Qwen 2.5 生成回答 (Ollama 本地 / DashScope API)
    ↓
用户回复
```

### 两轮文档切分策略

| 轮次 | 方法 | 作用 |
|------|------|------|
| 第一轮 | Markdown 标题层级切分 | 保语义完整性（每个教师/窗口 = 独立 chunk） |
| 第二轮 | RecursiveCharacterTextSplitter | 防超长（按段落→句子→字符兜底） |

### 模型配置

| 组件 | 推荐模型 | 大小 | 说明 |
|------|---------|------|------|
| Embedding | BAAI/bge-large-zh-v1.5 | 1.3GB | 中文检索 SOTA |
| Re-Ranker | BAAI/bge-reranker-v2-m3 | 1.1GB | 交叉编码精排 |
| LLM (本地) | Qwen2.5:7b | 4GB | 免费，需 8GB 以上内存 |
| LLM (API) | qwen-plus | - | ¥0.0008/千 tokens |

---

## 🤝 贡献指南

欢迎贡献！以下是一些可以参与的方向：

- 🏫 **添加你的大学** — PR 提交配置文件 + 知识数据
- 🔌 **编写数据源插件** — 爬虫/API 适配器
- 🐛 **报告 Bug** — 提交 Issue
- 💡 **功能建议** — Discussion 区讨论

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📜 License

MIT © Campus Guide Agent Contributors

---

## 🙏 致谢

本项目使用了以下优秀开源项目：

- [LangChain](https://github.com/langchain-ai/langchain) — LLM 应用框架
- [BGE (BAAI)](https://huggingface.co/BAAI/) — 中文嵌入和重排模型
- [通义千问 (Qwen)](https://github.com/QwenLM/Qwen) — 阿里开源大语言模型
- [Chroma](https://github.com/chroma-core/chroma) — 嵌入式向量数据库
- [Streamlit](https://github.com/streamlit/streamlit) — Python Web UI 框架
- [高德开放平台](https://lbs.amap.com/) — 地图 API
