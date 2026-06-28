# 产品需求文档 — Campus Guide Personal Agent

> **版本**: v0.1 (草案)
> **日期**: 2026-06-23
> **状态**: 待评审

---

## 1. 产品概述

### 1.1 产品定位

Campus Guide Personal Agent 是一套面向高校新生的**个人专属 AI 助手系统**。每位学生拥有一个独立运行的 Agent 容器，通过学习学生的个人兴趣、历史行为和学校知识，提供个性化的校园生活指引——涵盖教师查询、美食推荐、办事流程、奖学金政策、课程通知等场景。

### 1.2 核心理念

从共享服务（一个 RAG API 服务扛全校负载）转变为个人 Agent（每人一个独立 Agent 容器），从根本上消除高并发瓶颈，同时实现真正的个性化。

### 1.3 关键目标

| 目标 | 说明 |
|------|------|
| **零幻觉** | 所有回答必须基于学校真实知识库，禁止模型编造 |
| **个人化** | Agent 越用越懂你，记住每个人的偏好和历史 |
| **主动性** | 学院通知直接送达学生 Agent，按学生关注度排序推送 |
| **可扩展** | 新技能（外卖、地图、教务系统）可插拔注册 |
| **低成本** | 共享基础设施（Embedding 服务、LLM Gateway），Agent 容器本身轻量 |

---

## 2. 目标用户

| 用户角色 | 需求 | 使用方式 |
|---------|------|---------|
| **本科生（主要用户）** | 查教师信息、食堂推荐、办事流程、奖学金政策 | 微信小程序 / Web |
| **研究生** | 查导师详情、科研项目、实验室位置 | 微信小程序 / Web |
| **学院/教务处（管理方）** | 发布通知、管理知识库、查看学生咨询统计 | 管理后台 |
| **IT 运维** | 监控 Agent 运行状态、版本更新、故障恢复 | 运维控制台 |

---

## 3. 系统架构

### 3.1 顶层架构

```
┌──────────────────────────────────────────────────────────────────┐
│                     学院管理端（通知发布 / 知识库管理）              │
└─────────────────────────┬────────────────────────────────────────┘
                          │ HTTP / WebSocket
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                        通知总线（Redis Pub/Sub）                    │
│             按分类（奖学金/选课/食堂/活动）分发消息                  │
└────┬─────────┬──────────┬──────────┬──────────┬─────────────────┘
     │         │          │          │          │
     ▼         ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Agent A │ │ Agent B │ │ Agent C │ │ Agent D │ │ Agent N │
│ 学生张三 │ │ 学生李四 │ │ 学生王五 │ │ 学生赵六 │ │   ...   │
│ Docker  │ │ Docker  │ │ Docker  │ │ Docker  │ │ Docker  │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │            │           │           │
     └──────┬────┴─────┬─────┴──────┬────┴─────┬─────┘
            │          │             │          │
            ▼          ▼             ▼          ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │BGE Embed │ │ Chroma   │ │LLM Gatew.│ │ 个人记忆  │
     │服务(GPU) │ │ 集群(只读)│ │DashScope │ │ SQLite   │
     │          │ │          │ │+Ollama   │ │ 每人一份  │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘
     ──────── 共享基础设施层（学校服务器部署） ──────────
```

### 3.2 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Agent 运行时 | Python 3.11 + FastAPI | 每个学生一个独立进程 |
| 工作记忆 | 内存环形缓冲区 | 最近 20 轮对话 |
| 情景记忆 | SQLite（每人一个文件） | 历史查询、偏好、反馈 |
| 语义记忆 | Chroma + BGE-large-zh-v1.5 | 学校知识向量库（共享只读） |
| 程序记忆 | Skill 注册表 + Chroma | 可执行技能 + 纯文本程序知识 |
| Embedding 服务 | FastAPI + ONNX Runtime / vLLM | 共享 GPU 推理（gRPC/REST） |
| LLM 接入 | DashScope API（主）+ Ollama（备份） | API 超时自动降级 |
| 通知总线 | Redis Pub/Sub | 学院→Agent 消息分发 |
| 容器编排 | Docker Compose → K8s | Agent 按需扩缩 |
| 前端 | Streamlit / 微信小程序 | Web 和移动端双入口 |

---

## 4. 记忆系统设计

### 4.1 四记忆模型

采用 Tulving 记忆分类法，将 Agent 的知识系统划分为四个层次，由**工作记忆**统一协调。

```
                      ┌─────────────────────────┐
                      │    用户当前输入的问题      │
                      └────────────┬────────────┘
                                   ▼
                      ┌─────────────────────────┐
                      │      ★ 工作记忆 ★         │
                      │  (Working Memory)         │
                      │                           │
                      │  当前会话上下文(N轮对话)    │
                      │  正在处理的意图             │
                      │  正在引用的文档片段          │
                      │  临时推理结果               │
                      └────┬────┬────┬────┬───────┘
                           │    │    │    │
              ┌────────────┘    │    │    └────────────┐
              ▼                 ▼    ▼                  ▼
     ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
     │ ★ 情景记忆 ★  │  │ ★ 语义记忆 ★   │  │  ★ 程序记忆 ★      │
     │ (Episodic)   │  │ (Semantic)   │  │  (Procedural)    │
     │              │  │              │  │                   │
     │ 个人专属       │  │ 学校客观知识   │  │ 可执行技能(Skills)│
     │ SQLite 持久化  │  │ Chroma 共享   │  │ + 纯文本流程      │
     │              │  │ 只读副本       │  │                   │
     │ 历史对话记录   │  │ 教师名录      │  │ 奖学金申请步骤     │
     │ 个人偏好       │  │ 食堂菜单      │  │ 选课操作流程       │
     │ 关注话题       │  │ 政策原文      │  │ 地图导航           │
     │ 反馈历史       │  │ 校园地图      │  │ 外卖下单           │
     │ 人际关系       │  │ 课程信息      │  │ 密码重置           │
     └──────────────┘  └──────────────┘  └──────────────────┘
```

### 4.2 工作记忆（Working Memory）

**作用**：Agent 当下的"意识"，协调其他三类记忆的输入输出。

**技术实现**：

```python
@dataclass
class WorkingMemory:
    # 当前对话上下文（环形缓冲区）
    conversation_history: deque[Message]  # maxlen=20

    # 当前意图
    current_intent: Optional[str]

    # 当前引用的知识片段
    referenced_chunks: List[Document]

    # 临时推理缓存（本次请求内的中间结果）
    reasoning_cache: Dict[str, Any]
```

**运作流程**：

```
1. 用户输入 → 工作记忆记录
2. 意图识别 → 工作记忆设定 current_intent
3. 语义记忆检索 → 结果加入 referenced_chunks
4. 程序记忆匹配 → 如果有 Skill，执行；否则返回文本步骤
5. 情景记忆检索 → 补充个人上下文
6. LLM 推理 → 生成回答
7. 回答写入 conversation_history
8. 情景记忆异步更新（用户的选择/反馈）
```

### 4.3 情景记忆（Episodic Memory）

**作用**：记录学生的个人经历——问过什么、关心什么、反馈过什么。

**存储方案**：每人一个 SQLite 文件，路径 `memory_data/{student_id}/episodic.db`

**核心表结构**：

```sql
-- 对话历史
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    intent TEXT,
    satisfaction INTEGER,       -- 用户反馈：1-5
    referenced_skills TEXT      -- 本次回答调用了哪些技能
);

-- 个人偏好
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,    -- 如 "fav_canteen", "concerned_topics"
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 关注话题（用于通知优先级排序）
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,          -- 如 "奖学金", "选课", "食堂"
    keywords TEXT,                -- 具体关注点
    priority INTEGER DEFAULT 5,   -- 1-10
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 反馈记录
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id),
    feedback_type TEXT,           -- "correct" / "incorrect" / "irrelevant"
    detail TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**关键设计决策**：
- 先写入内存 + 异步落盘，避免对话延迟
- 定期压缩（删除 > 6 个月的无关对话）
- 偏好自动推断：学生多次问同一话题 → 系统建议订阅

### 4.4 语义记忆（Semantic Memory）

**作用**：学校的客观知识——教师信息、食堂菜单、奖学金政策等。

**实现**：基于现有的 RAG 管道（Chroma + BGE Embedding + BGE Re-Ranker），改为**共享只读服务**。

**与当前代码的关系**：

```
core/retrieval/retriever.py  →  改为 RPC 客户端，调用共享 Embedding 服务
core/retrieval/reranker.py   →  移到共享服务端
core/pipeline/rag_chain.py   →  Agent 内部的检索编排逻辑保留
```

**共享 Embedding 服务**：

```python
# embedding_service.py（学校服务器部署，GPU）
@app.post("/embed")
async def embed(texts: List[str]):
    embeddings = model.encode(texts, normalize_embeddings=True)
    return {"embeddings": embeddings.tolist()}

@app.post("/rerank")
async def rerank(query: str, documents: List[str]):
    scores = reranker.compute_score([(query, doc) for doc in documents])
    return {"scores": scores}
```

### 4.5 程序记忆（Procedural Memory）

**作用**：知道"怎么做"——可执行的技能 + 纯文本流程知识。

**设计原则**：

```
                      ┌─ 有对应 API？──→ Skill 执行器（调外部系统）
                      │
用户需要"怎么做" ────┤
                      │
                      └─ 没有 API？ ──→ 纯文本步骤（LLM 读文档回答）
```

**技能注册表**（继承现有 `ToolRegistry`）：

```python
class Skill(BaseTool):
    """所有技能的基类"""
    name: str                         # 唯一标识
    description: str                  # 用于 LLM 意图匹配的描述
    parameters: Dict[str, Field]      # 参数定义
    version: str = "1.0.0"
    requires_auth: bool = False       # 是否需要学号认证

    async def execute(self, **params) -> Result: ...
    async def validate(self, **params) -> bool: ...
    def to_openai_tool_spec(self) -> dict: ...  # 用于 LLM function calling
```

**初始技能清单**：

| 技能 | 分类 | 外部依赖 | 优先级 |
|------|------|---------|--------|
| `query_schedule` | 课表查询 | 教务系统 API | P0 |
| `plan_route` | 路线规划 | 高德地图 API | P0 |
| `search_teacher` | 教师查询 | 语义记忆（无外部依赖） | P0 |
| `scholarship_guide` | 奖学金指引 | 纯文本流程 | P0 |
| `report_loss` | 挂失/补办 | 校园卡系统 API | P1 |
| `order_food` | 食堂点餐/外卖 | 食堂系统 API | P1 |
| `reset_password` | 密码重置 | 统一认证 API | P1 |
| `ask_leave` | 请假流程 | 学工系统 API | P2 |
| `book_room` | 自习室/实验室预约 | 预约系统 API | P2 |
| `notify_subscribe` | 通知订阅管理 | 系统自身 | P0 |

**知识型程序（纯文本）**：无 API 对接的校园流程，走 RAG 检索。

```
data/procedures/
├── 学生证补办流程.md
├── 转专业申请流程.md
├── 休学/复学流程.md
├── 助学贷款申请指南.md
├── 校园卡充值指南.md
└── 宿舍调换流程.md
```

---

## 5. 通知系统

### 5.1 发布订阅模型

```
学院管理员
    │  POST /api/notifications
    ▼
┌──────────────────────┐
│  通知发布 API         │
│  分类: 奖学金/选课/   │
│  食堂/活动/紧急       │
│  目标: all/订阅者/指定 │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  通知总线              │
│  Redis Pub/Sub        │
│  Channel: notification│
│  :{category}          │
└──────────┬───────────┘
           │
           ▼  Agent 订阅自己关心的分类
┌──────────────────────┐
│  Agent 内部处理器      │
│                       │
│  1. 查情景记忆订阅列表  │
│  2. 匹配学生关注度      │
│  3. 高关注 → 主动推送   │
│  4. 低关注 → 静默存档   │
│  5. 离线 → 暂存上线弹   │
└──────────────────────┘
```

### 5.2 通知格式

```json
{
    "id": "notif_20260623_001",
    "category": "scholarship",
    "title": "2026 年国家奖学金申请已开放",
    "content": "2026 年国家奖学金申请通道已开放，截止日期为 9 月 30 日...",
    "urgency": "normal",
    "published_at": "2026-06-23T10:00:00+08:00",
    "target_groups": ["all_undergrad"],
    "attachments": [
        {"name": "申请流程.pdf", "url": "https://...", "type": "pdf"}
    ],
    "related_skills": ["scholarship_guide"]
}
```

### 5.3 学生侧体验

Agent 根据情景记忆中学生的订阅和浏览历史，自动决定推送策略：

| 学生画像 | 行为 | 推送策略 |
|---------|------|---------|
| 爱学习的张三 | 常问奖学金、竞赛 | 奖学金通知 → 即时推送 |
| 贪玩的李四 | 常问食堂、外卖 | 食堂通知 → 即时推送，其他静默 |
| 新生王五 | 刚入学，没留下数据 | 默认全部推送，等积累数据 |

---

## 6. 部署方案（方案 A）

### 6.1 容器架构

```yaml
# docker-compose.yml
services:
  # ── 共享基础设施 ──
  embedding-service:
    image: cga/embedding:latest
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1}]

  chroma-cluster:
    image: chromadb/chroma:latest
    environment:
      - IS_PERSISTENT=TRUE
    volumes:
      - chroma_data:/chroma/chroma

  llm-gateway:
    image: cga/llm-gateway:latest
    environment:
      - DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}

  notification-bus:
    image: redis:7-alpine

  # ── Agent 实例 (按需扩容) ──
  agent:
    image: cga/agent:latest
    environment:
      - STUDENT_ID=${STUDENT_ID}
      - AGENT_PORT=${AGENT_PORT}
    volumes:
      - memory_data:/memory_data
    depends_on:
      - embedding-service
      - chroma-cluster
      - llm-gateway
      - notification-bus
    ports:
      - "${AGENT_PORT}:8000"
```

### 6.2 资源估算

| 组件 | 每个实例资源 | N=1000 学生 | 说明 |
|------|------------|------------|------|
| Agent 容器 | 0.1 CPU / 128MB RAM | 100 CPU / 128GB RAM | 轻量，主要是等待 LLM 响应 |
| Embedding 服务 | 1 GPU / 8GB VRAM | 1-2 GPU | 共享，1000 QPS 绰绰有余 |
| Chroma 集群 | 4 CPU / 16GB RAM | 2-3 节点 | 只读副本水平扩展 |
| LLM Gateway | 1 CPU / 2GB RAM | 2-3 副本 | 无状态，可水平扩展 |
| Redis | 2 CPU / 4GB RAM | 1 主 2 从 | Pub/Sub + 缓存 |
| SQLite 存储 | 每人 ≤10MB | ~10GB | HDD/SSD 均可 |

### 6.3 运维考虑

- Agent 按学号 hash 分片到不同物理节点
- 非活跃 Agent (30 天未登录) → 自动休眠，唤醒时重建
- 每学期初（迎新季）预创建所有新生 Agent
- 健康检查端点 `/health` 返回四记忆组件状态

---

## 7. 与现有代码的关系

### 7.1 可复用的模块

```
保留并增强                   需要重写                    新增
────────────                  ──────                    ────
core/retrieval/retriever.py   app/webui.py              core/memory/
core/retrieval/reranker.py    app/cli.py                 ├── __init__.py
core/ingest/splitter.py       core/pipeline/             ├── working_memory.py
core/ingest/markdown_loader.py  rag_chain.py (需适配)     ├── episodic_memory.py
core/llm/qwen_api.py         config/ (需增加记忆配置)     ├── semantic_memory.py (封装)
core/llm/qwen_ollama.py                                  ├── procedural_memory/
core/tools/ (→ 迁移为 Skill)                              │   ├── __init__.py
core/config.py                                            │   ├── registry.py
                                                          │   ├── base.py
                                                          │   ├── composite.py
                                                          │   ├── skills/*
                                                          │   └── knowledge_procedures.py
                                                          ├── orchestrator.py
                                                          ├── notification/
                                                          │   ├── subscriber.py
                                                          │   ├── publisher.py
                                                          │   └── router.py
                                                          └── embedding_service/
                                                              ├── server.py
                                                              └── client.py
```

### 7.2 迁移策略

| 阶段 | 内容 | 预计时间 |
|------|------|---------|
| **Phase 1** | 重构 `core/tools/` → `procedural_memory/`，写 Skill 基类和注册中心 | 3 天 |
| **Phase 2** | 实现 `working_memory.py` + `orchestrator.py`，重构 RAG 管道接入记忆编排 | 3 天 |
| **Phase 3** | 实现 `episodic_memory.py`（SQLite 持久化） | 2 天 |
| **Phase 4** | 拆出 Embedding Service（FastAPI + GPU），Agent 通过 RPC 调用 | 3 天 |
| **Phase 5** | 通知系统（Redis Pub/Sub + Agent 订阅） | 2 天 |
| **Phase 6** | Docker Compose 部署 + 健康检查 + 监控 | 2 天 |

---

## 8. 成功指标

| 指标 | 目标 | 测量方式 |
|------|------|---------|
| 回答精确率 | ≥ 95% | 用户反馈 + 定期抽样标注 |
| 个人化率 | 第 10 次对话后满意度提升 30% | 情景记忆前后对比 |
| 通知触达率 | 高优先级通知 80% 在 5 分钟内触达 | Agent 推送日志 |
| 知识更新同步 | 学院发布后 ≤ 30 分钟所有 Agent 可用 | 语义记忆版本号检查 |
| 系统可用性 | 99.5% (每月宕机 ≤ 3.6 小时) | 健康检查聚合 |
| 单 Agent 成本 | ≤ ¥5/月 (含 LLM API 费用) | 用量监控 |

---

## 9. 开放问题

1. **个人隐私**：情景记忆存储在服务器端（SQLite），如何处理学生数据隐私？是否支持导出/删除（GDPR 合规）？
2. **Agent 生命周期**：学生毕业后，Agent 数据保留多久？是否可迁移到校友身份？
3. **LLM 成本**：假设每天 20 次对话 × 1000 学生 × 30 天 ≈ 每月 ¥6，000（Qwen-Plus API 模式），是否需要预算计划？
4. **Agent 间协作**：是否需要支持 Agent 间互相通信（例如 A 同学问 "B 同学在哪间自习室"）？这在方案 A 中需要跨 Agent 查询。
5. **多端同步**：如果学生同时在 Web 和小程序上登录，是否需要同步工作记忆？
6. **离线模式**：校园网络不稳定时，Agent 是否应该支持基本的本地回答能力（缩水版模型缓存）？

---

## 10. 附录：术语表

| 术语 | 定义 |
|------|------|
| **工作记忆 (Working Memory)** | 当前对话的临时上下文，环形缓冲区，不持久化 |
| **情景记忆 (Episodic Memory)** | 学生个人的历史交互记录，按人隔离持久化 |
| **语义记忆 (Semantic Memory)** | 学校的客观知识，共享只读向量库 |
| **程序记忆 (Procedural Memory)** | 如何执行任务的技能库 + 知识流程 |
| **Skill** | 可执行的外部工具，继承自 BaseTool，注册在程序记忆中 |
| **知识型程序** | 纯文本描述的办事流程，无 API 对接，走 RAG 检索 |
| **通知总线** | Redis Pub/Sub 实现，学院发布 → Agent 订阅 |
| **Embedding 服务** | 共享的 BGE 模型推理服务（GPU），所有 Agent 通过 RPC 使用 |
| **LLM Gateway** | 统一的 LLM 接入层，管理 API Key、速率限制、自动降级 |
