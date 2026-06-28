# Campus Guide Personal Agent — 任务拆解

> 基于 `docs/PRD.md` v0.1 拆解
> 日期：2026-06-23

---

## 任务总览

```
Phase 1           Phase 2            Phase 3           Phase 4            Phase 5            Phase 6
程序记忆重构       工作记忆+编排器      情景记忆持久化      Embedding 服务化    通知推送系统        容器化部署
────12 tasks──→  ───10 tasks──→    ───8 tasks──→    ───9 tasks──→    ───9 tasks──→    ───10 tasks──→
  3 天              3 天              2 天              3 天               2 天              2 天
```

**并行机会**：Phase 1 中 T1-T4 可与 T5-T8 并行；Phase 4/5 可部分并行；Phase 6 中的 T56-T58 可单独先行。

---

## Phase 1: 程序记忆重构（3 天）

> **目标**：把 `core/tools/` 改造成程序记忆的 Skill 系统，建立 Skill 基类 + 注册中心 + 知识型程序的双层架构。
> **不破坏**：现有的检索/LLM/切分全部保持可用，本次只新增和迁移。

### 1.1 Skill 抽象层（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T1 | 定义 Skill 基类 | 继承 `BaseTool`，新增 `parameters`（pydantic Field schema）、`version`、`requires_auth`、`async execute()`、`validate()`、`to_openai_tool_spec()`。兼容旧 `invoke()` 方法。 | `core/memory/procedural_memory/base.py` | 无 |
| T2 | 定义 SkillResult 类型 | dataclass：`success: bool`, `data: Any`, `error: Optional[str]`, `metadata: dict`。统一所有 Skill 的返回值格式。 | `core/memory/procedural_memory/base.py` | 无 |
| T3 | 扩展 ToolRegistry → SkillRegistry | 继承原 `ToolRegistry`，新增：按分类索引、按意图匹配（`match_by_description(query) -> List[Skill]`）、按 capability 筛选（"可执行" / "纯文本"）、`to_openai_tools_spec()` 批量导出 | `core/memory/procedural_memory/registry.py` | T1, T2 |
| T4 | 迁移 RoutePlanner 为 Skill 格式 | 不改业务逻辑，加 `pydantic.Field` 参数 schema、`requires_auth=False`、`version="1.0.0"`，适配新接口。放在 `skills/` 下。 | `core/memory/procedural_memory/skills/route_planner.py` | T1, T2 |

### 1.2 知识型程序（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T5 | 实现 KnowledgeProcedureStore | 从 `data/procedures/` 目录加载纯文本流程 Markdown，走现有的 `MarkdownLoader + CampusTextSplitter` 切分 + `EmbedderFactory` 嵌入，存入独立的 Chroma collection（`procedural_knowledge`）。 | `core/memory/procedural_memory/knowledge_procedures.py` | 无 |
| T6 | 实现过程记忆双路检索 | `retrieve(query, k=5)` → 先从 SkillRegistry 匹配可执行技能；再从 Chroma 检索纯文本流程。返回 `{"skills": [...], "text_procedures": [...]}`。LLM 后续根据结果判断走 skill 执行还是纯文本回答。 | `core/memory/procedural_memory/knowledge_procedures.py` | T3, T5 |
| T7 | 编写示例程序知识 Markdown | 创建 3 个纯文本流程文档用于测试：学生证补办、转专业申请、助学贷款指南。 | `data/procedures/*.md` | 无 |

### 1.3 初始 Skills（1.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T8 | 实现 ScholarshipGuide | 纯文本型 Skill，不调外部 API。`execute()` 从语义记忆检索最新的奖学金政策，用 LLM 生成个人化答案。 | `core/memory/procedural_memory/skills/scholarship.py` | T1, T2 |
| T9 | 实现 QuerySchedule | Mock 教务 API 的技能骨架。`requires_auth=True`，参数包含 `student_id`、`semester`。用 mock 数据返回，留好对接接口。 | `core/memory/procedural_memory/skills/course_query.py` | T1, T2 |
| T10 | 实现 NotifySubscribe | 管理学生通知订阅：`subscribe(topic)`、`unsubscribe(topic)`、`list_subscriptions()`。写入情景记忆的 subscriptions 表（Phase 3 才完成，先写接口）。 | `core/memory/procedural_memory/skills/notification.py` | T1, T2 |
| T11 | 编写 Skill 单元测试 | 覆盖：Skill 注册/查找/匹配、`to_openai_tool_spec()` 格式正确、KnowledgeProcedureStore 检索返回、RoutePlanner Skill 参数校验。 | `tests/test_procedural_memory.py` | T3, T4, T5, T6 |
| T12 | 更新 `init_db.py` 支持程序知识入库 | 增加 `--procedures` flag，调用 `KnowledgeProcedureStore` 初始化。 | `scripts/init_db.py` (修改) | T5 |

**Phase 1 完成标志**：
- ✅ `from core.memory.procedural_memory import SkillRegistry` 可用
- ✅ RoutePlanner 作为 Skill 可被注册和调用
- ✅ `KnowledgeProcedureStore` 能检索纯文本流程
- ✅ 11 个新增测试通过

---

## Phase 2: 工作记忆 + 编排器（3 天）

> **目标**：实现工作记忆（对话上下文 + 临时推理缓存）和四记忆编排器，重构 `CampusRAGPipeline` 接入记忆系统。让对话不再是单次问答。

### 2.1 工作记忆（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T13 | 定义 Message 类型 | dataclass：`role`（user/assistant/system/tool）、`content`、`timestamp`、`metadata`。 | `core/memory/working_memory.py` | 无 |
| T14 | 实现 WorkingMemory | 环形缓冲区 `deque[Message](maxlen=20)`、`current_intent`、`referenced_chunks`、`reasoning_cache: Dict[str, Any]`。方法：`add_message()`、`get_context(n)`、`clear_reasoning()`。为后续流式响应预留 `get_messages_as_langchain()`。 | `core/memory/working_memory.py` | T13 |
| T15 | 实现意图缓存 | 工作记忆在 3 轮对话内复用上一次意图（如学生追问"还有哪些？"时不重新做意图识别，直接沿用上次分类）。 | `core/memory/working_memory.py` | T14 |
| T16 | 编写工作记忆单元测试 | 覆盖：消息追加/溢出、上下文获取、意图缓存命中/过期、推理缓存 set/get | `tests/test_working_memory.py` | T14, T15 |

### 2.2 编排器（1.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T17 | 实现 MemoryOrchestrator | 协调四记忆的调用顺序：`1.工作记忆记录输入` → `2.意图识别（优先取缓存）` → `3.语义记忆检索` → `4.程序记忆匹配` → `5.情景记忆查历史` → `6.LLM生成` → `7.工作记忆记录输出`。每个步骤有 hook 点（日志/监控）。 | `core/memory/orchestrator.py` | T14, Phase 1 |
| T18 | 重构 CampusRAGPipeline.invoke() | 删掉硬编码的关键词工具调用。改为调用 `MemoryOrchestrator.process(query)`。保留 RAG 检索逻辑，但通过编排器驱动。 | `core/pipeline/rag_chain.py` (修改) | T17 |
| T19 | 实现工具调用决策 | 编排器在步骤 4 中：如果程序记忆返回匹配的 Skill（score > 阈值），写入 reasoning_cache；LLM 生成时把匹配的 Skill 列表注入 system prompt，由 LLM 决定是否调用、怎么调用。 | `core/memory/orchestrator.py` | T17 |
| T20 | 实现上下文窗口管理 | 工作记忆超过 maxlen 时，不丢弃最新 N 轮。旧消息压缩为摘要（调用 LLM 做轻量总结），存入情景记忆 `conversations` 表的 summary 字段。 | `core/memory/working_memory.py` | T14 |

### 2.3 集成测试（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T21 | 编写编排器集成测试 | 端到端：用户输入 → 编排器输出，验证意图识别 + 语义检索 + 程序记忆匹配的链式调用。mock 外部 LLM 和向量库。 | `tests/test_orchestrator.py` | T17-T20 |
| T22 | 确保现有 14 个测试仍通过 | 重构后运行全部测试，修复 regression。 | 无新增 | T18 |

**Phase 2 完成标志**：
- ✅ `MemoryOrchestrator.process(query)` 返回完整四记忆协调的结果
- ✅ 工具调用不再硬编码，由程序记忆匹配 + LLM 决策
- ✅ 多轮对话上下文保留（工作记忆环形缓冲区）
- ✅ 全部现有测试 + 新增测试通过

---

## Phase 3: 情景记忆持久化（2 天）

> **目标**：每人一个 SQLite 文件，持久化对话历史、偏好、订阅。让 Agent 能"记住你是谁"。

### 3.1 存储层（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T23 | 实现 EpisodicMemory 核心类 | `__init__(student_id, data_dir="memory_data/")` → 创建/打开 `{student_id}/episodic.db`。内部用 `sqlite3`（不引入 ORM 依赖）。 | `core/memory/episodic_memory.py` | 无 |
| T24 | 实现表初始化 | 按 PRD 定义创建 4 张表：`conversations`, `preferences`, `subscriptions`, `feedback`。带 migration 版本号（`PRAGMA user_version`）。 | `core/memory/episodic_memory.py` | T23 |
| T25 | 实现对话读写 | `save_conversation(query, response, intent, skills)`、`get_recent_conversations(limit=10)`、`search_conversations(keyword)`。写入时先写内存队列 + 异步线程落盘。 | `core/memory/episodic_memory.py` | T23, T24 |
| T26 | 实现偏好存储 | `set_preference(key, value)`、`get_preference(key)`、`get_all_preferences()`。支持 JSON 值。 | `core/memory/episodic_memory.py` | T23, T24 |

### 3.2 偏好学习（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T27 | 实现话题自动推断 | 分析最近 30 条对话，统计高频分类 → 自动生成订阅建议。返回 `[(topic, confidence), ...]`，不自动写入。 | `core/memory/episodic_memory.py` | T25 |
| T28 | 实现个人上下文生成 | `get_personal_context()` → 返回一段文本摘要（偏好 + 最近 3 次对话概要），注入 LLM system prompt 实现个性化。 | `core/memory/episodic_memory.py` | T25, T26, T27 |

### 3.3 集成 + 测试（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T29 | 将情景记忆接入编排器 | 在 `MemoryOrchestrator` 步骤 5 调用 `EpisodicMemory.get_personal_context()`，注入 LLM prompt。步骤 8 异步写入对话记录。 | `core/memory/orchestrator.py` (修改) | T28, Phase 2 |
| T30 | 编写情景记忆单元测试 | 覆盖：建表、读写对话、偏好存取、话题推断、个人上下文生成。用 tempfile 做隔离测试。 | `tests/test_episodic_memory.py` | T25-T28 |

**Phase 3 完成标志**：
- ✅ 学生对话被持久化到 SQLite
- ✅ 下次对话时 Agent 记得之前的偏好和历史
- ✅ `get_personal_context()` 返回有意义的内容

---

## Phase 4: Embedding 共享服务（3 天）

> **目标**：把 BGE Embedding 和 Re-Ranker 从每个 Agent 进程中拆出来，变成单独的 FastAPI 服务，Agent 通过 HTTP/gRPC 调用。

### 4.1 服务端（1.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T31 | 实现 Embedding Service 核心 | FastAPI app，启动时加载 BGE-large-zh-v1.5 模型（CPU/CUDA 自适应），提供 `/health`、`/embed`、`/embed_batch` 端点。使用请求队列避免 GPU OOM。 | `core/memory/embedding_service/server.py` | 无 |
| T32 | 实现 Re-Ranker 端点 | FastAPI 同级服务，`/rerank` 端点：接受 `query` + `documents: List[str]`，返回 scores。同样加载一次模型常驻。可选与 embedding 合并为一个 service。 | `core/memory/embedding_service/server.py` | T31 |
| T33 | 实现模型热加载 | `/reload` 端点：hot-swap 模型（用于升级 BGE 版本），不中断服务。 | `core/memory/embedding_service/server.py` | T31 |
| T34 | 实现超时 + 连接池 | gunicorn + uvicorn workers，每个 worker 加载一份模型。配置 worker 数量 = GPU 显存 / 单模型大小。 | `core/memory/embedding_service/server.py` | T31 |

### 4.2 客户端（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T35 | 实现 EmbeddingClient | 封装 `httpx.AsyncClient`，带连接池复用。`embed(texts)`、`rerank(query, docs)`。请求失败自动重试（tenacity，指数退避）。 | `core/memory/embedding_service/client.py` | T31, T32 |
| T36 | 实现 EmbedderFactory 服务模式 | 在现有 `EmbedderFactory` 中增加 `create_remote(endpoint_url)` 模式，返回 `RemoteEmbedder`（实现 LangChain 的 `Embeddings` 接口）。 | `core/retrieval/embedder.py` (修改) | T35 |
| T37 | 重构 Chroma/Retriever 使用远程 Embedding | `CampusRAGPipeline` 初始化时，如果配置 `embedding.mode=remote`，使用 `EmbeddingClient` 而不是本地模型。本地模式保留兼容。 | `core/pipeline/rag_chain.py` (修改) | T36 |

### 4.3 测试（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T38 | 编写 Embedding Service 集成测试 | 启动 service → 调 `/health` → `/embed` 验证 shape → `/rerank` 验证排序。用 `TestClient`。 | `tests/test_embedding_service.py` | T31-T34 |
| T39 | 编写 EmbeddingClient 测试 | Mock service 端点，验证重试逻辑、连接复用、超时处理。 | `tests/test_embedding_client.py` | T35 |

**Phase 4 完成标志**：
- ✅ `python embedding_service/server.py` 独立启动，GPU 模型常驻
- ✅ Agent 通过 HTTP 调用 embedding/reranker，不加载本地模型
- ✅ 本地模式仍可用（向后兼容）

---

## Phase 5: 通知推送系统（2 天）

> **目标**：学院管理员发布通知 → Redis Pub/Sub 分发 → Agent 按学生偏好推送/存档。

### 5.1 通知总线（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T40 | 实现 NotificationPublisher | REST API：`POST /api/notifications` 接受通知 JSON（PRD 定义格式），验证后 publish 到 Redis channel `notification:{category}`。同时写入通知归档表。 | `core/memory/notification/publisher.py` | 无 |
| T41 | 实现 NotificationSubscriber | Redis Pub/Sub 监听器。Agent 启动时根据情景记忆 `subscriptions` 表订阅对应 channel。异步守护线程处理消息。 | `core/memory/notification/subscriber.py` | Phase 3 (需要 subscriptions 表) |
| T42 | 实现 NotificationRouter | 每条通知进来 → 查该学生的订阅列表 + 偏好 → 判断优先级（高关注→推送 / 低关注→静默存档 / 离线→暂存）。 | `core/memory/notification/router.py` | T41, Phase 3 |

### 5.2 Agent 侧集成（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T43 | Agent 启动时初始化通知订阅 | `Agent.__init__` → 读情景记忆订阅列表 → 连接 Redis → 订阅 channels。无 Redis 时降级为轮询模式。 | `core/memory/orchestrator.py` (修改) | T41, T42 |
| T44 | 通知入工作记忆 | 高优先级通知到达 → 作为 system 消息插入工作记忆环形缓冲区 → 下次学生打开对话自动显示。 | `core/memory/working_memory.py` (修改) | T42, T14 |
| T45 | 实现通知历史查询 | `GET /api/notifications?student_id=xxx` → 返回最近通知列表（已推 + 静默），支持按分类筛选。 | `core/memory/notification/router.py` | T42 |

### 5.3 管理端 + 测试（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T46 | 实现管理员通知发布页面 | FastAPI 路由 + 简单 HTML form：选分类、填标题/内容、上传附件、选目标群体（全部/按学院/按年级）。 | `core/memory/notification/publisher.py` | T40 |
| T47 | 编写通知系统测试 | 覆盖：发布→订阅接收→路由决策（高关注推送/静默/暂存）。用 `fakeredis`。 | `tests/test_notification.py` | T40-T45 |
| T48 | 编写 NotifySubscribe Skill 集成测试 | 学生说 "关注奖学金通知" → 调用 Skill → subscriptions 表新增记录 → 下次通知命中。 | `tests/test_procedural_memory.py` (追加) | T10, T47 |

**Phase 5 完成标志**：
- ✅ 管理员 POST 通知 → 关注该话题的学生 Agent 收到推送
- ✅ 不关注的学生静默存档
- ✅ 通知可查询历史

---

## Phase 6: 容器化部署 + 监控（2 天）

> **目标**：Docker Compose 一键启动全套服务，包含健康检查和基础监控。

### 6.1 Docker 化（1 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T49 | 编写 Embedding Service Dockerfile | 基于 `pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime`。预下载 BGE 模型到 image 内。健康检查端点。 | `docker/embedding.Dockerfile` | Phase 4 |
| T50 | 编写 Agent Dockerfile | 基于 `python:3.11-slim`。不含 torch/transformers（通过 HTTP 调 Embedding Service）。环境变量 `STUDENT_ID` 决定该容器服务哪个学生。 | `docker/agent.Dockerfile` | Phase 2-3 |
| T51 | 编写 LLM Gateway Dockerfile | 基于 `python:3.11-slim`。封装 DashScope API（主）+ Ollama（备份），内置熔断器、重试、速率限制。 | `docker/gateway.Dockerfile` | 无 |
| T52 | 编写 docker-compose.yml | 按 PRD 定义：embedding-service + chroma + llm-gateway + redis + agent（多实例，通过 `STUDENT_ID` 环境变量区分）。agent 服务使用 `scale` 或 profile 机制。 | `docker-compose.yml` (根目录) | T49-T51 |
| T53 | 编写 .env.production 模板 | 生产环境变量说明：`DASHSCOPE_API_KEY`、`REDIS_URL`、`GPU_ENABLED`、`MAX_AGENTS`、`LOG_LEVEL`。 | `.env.production.example` | T52 |

### 6.2 健康检查 + 监控（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T54 | 实现 Agent 健康检查 | `GET /health` → 返回 `{"status": "ok", "memories": {"working": ok, "episodic": ok, "semantic": {"embedding_service": ok}, "procedural": {"skills_loaded": 5}}}` | `app/agent_server.py`（新建） | Phase 2-3 |
| T55 | 实现结构化日志 | 用 `loguru` 替换所有 `warnings.warn()` 和 `print()`。统一格式：`{time} | {level} | {student_id} | {correlation_id} | {message}`。每个请求一个 `correlation_id`（uuid）。 | 全局修改 | 无 |
| T56 | 实现基础指标端点 | `GET /metrics` → Prometheus 格式：请求数、延迟分位数（p50/p95/p99）、各记忆组件调用耗时、缓存命中率、LLM API 调用次数/费用。 | `app/agent_server.py` | T54 |
| T57 | 编写 docker-compose.override.yml (dev) | 开发模式：挂载源代码 volume、开启 debug 日志、暴露各服务端口、关闭 GPU 需求。 | `docker-compose.override.yml` | T52 |

### 6.3 文档（0.5 天）

| ID | 任务 | 说明 | 产出文件 | 依赖 |
|----|------|------|---------|------|
| T58 | 编写部署文档 | 覆盖：环境要求（OS/Docker/GPU）、一键启动、大学配置添加、数据目录结构、常见问题排查。 | `docs/DEPLOYMENT.md` | T49-T57 |
| T59 | 编写开发者文档 | 覆盖：本地开发环境搭建、如何新增 Skill、如何接入新大学、测试运行、代码架构概览。 | `docs/DEVELOPMENT.md` | Phase 1-5 |
| T60 | 更新 README.md | 加入 V2 架构图（Mermaid）、快速开始、四记忆说明、Skills 清单、技术栈。 | `README.md` (修改) | T58, T59 |

**Phase 6 完成标志**：
- ✅ `docker-compose up` 一键启动全套服务
- ✅ `GET /health` 返回所有组件状态
- ✅ `GET /metrics` 返回 Prometheus 可消费的指标

---

## 依赖关系图

```
Phase 1 (程序记忆)
  ├── T1 → T2 → T3 → T6
  ├── T1 → T2 → T4
  ├── T1 → T2 → T8, T9, T10
  ├── T5 → T6
  ├── T3, T6, T7 → T11
  └── T5 → T12

Phase 2 (工作记忆+编排器)  ← 依赖 Phase 1 完成
  ├── T13 → T14 → T16
  ├── T14 → T15
  ├── Phase1 + T14 → T17
  ├── T17 → T18
  ├── T17 → T19
  ├── T14 → T20
  ├── T17-T20 → T21
  └── T18 → T22

Phase 3 (情景记忆)  ← 依赖 Phase 1+2 完成
  ├── T23 → T24 → T25, T26
  ├── T25 → T27
  ├── T25, T26, T27 → T28
  ├── T28 → T29 (需 Phase 2)
  └── T25-T28 → T30

Phase 4 (Embedding 服务) ← 可与 Phase 1-3 并行（独立模块）
  ├── T31 → T32, T33, T34
  ├── T31, T32 → T35
  ├── T35 → T36
  ├── T36 → T37
  ├── T31-T34 → T38
  └── T35 → T39

Phase 5 (通知系统)  ← 依赖 Phase 3 (subscriptions 表)
  ├── T40 → T46
  ├── Phase3 → T41
  ├── T41, Phase3 → T42
  ├── T42 → T43
  ├── T42, Phase2 → T44
  ├── T42 → T45
  ├── T40-T45 → T47
  └── T48 (需 Phase 1 T10 + T47)

Phase 6 (部署)  ← 依赖 Phase 1-5 完成
  ├── Phase4 → T49
  ├── Phase2+3 → T50
  ├── T51 (独立)
  ├── T49-T51 → T52
  ├── T52 → T53
  ├── Phase2+3 → T54
  ├── T55 (独立，建议最早做)
  ├── T54 → T56
  ├── T52 → T57
  ├── T49-T57 → T58, T59
  └── T58, T59 → T60
```

---

## 可并行执行的前期任务

以下任务**不依赖任何 Phase**，可立即开始：

| 任务 | 说明 | 优先级 |
|------|------|--------|
| T1, T2 | Skill 基类定义（纯抽象） | ⭐⭐⭐ |
| T5 | KnowledgeProcedureStore（独立模块） | ⭐⭐ |
| T7 | 编写示例程序知识 Markdown | ⭐ |
| T13 | Message 类型定义 | ⭐⭐⭐ |
| T23 | EpisodicMemory SQLite shell | ⭐⭐ |
| T31 | Embedding Service（独立 FastAPI app） | ⭐ |
| T51 | LLM Gateway Dockerfile | ⭐ |
| T55 | loguru 集成（全局改动，建议最早做） | ⭐⭐⭐ |

---

## 任务统计

| 维度 | 数量 |
|------|------|
| 总任务数 | 60 |
| 新增文件 | ~35 |
| 修改文件 | ~10 |
| 删除文件 | 0（保留旧模块兼容） |
| 预估总工时 | 15 天 |

---

## 风险提示

| 风险 | 影响 | 缓解 |
|------|------|------|
| 重构 `rag_chain.py` 引入 regression | Phase 2 后现有功能不可用 | T22 确保全量测试回归 |
| BGE 模型 GPU 部署不稳定 | Phase 4 无法服务化 | 保留本地模式兼容（T37） |
| Redis 依赖增加运维复杂度 | Phase 5 需要 Redis | T43 提供降级轮询模式 |
| Docker 多 Agent 编排 | Phase 6 资源管理复杂 | T57 提供 dev profile 降级 |
| LLM API 费用不可控 | Phase 6 上线后成本超预期 | LLM Gateway 内置费用追踪（T51） |

---

## 版本里程碑

| 版本 | 包含 Phase | 可演示内容 |
|------|-----------|-----------|
| v0.1-alpha | Phase 1+2 | 单 Agent 框架：四记忆编排 + 多轮对话 + 程序记忆技能 |
| v0.2-alpha | Phase 1+2+3 | 个人化 Agent：记住你是谁、你关心什么 |
| v0.3-alpha | Phase 1+2+3+4 | 服务化：BGE Embedding 独立服务、Agent 轻量化 |
| v0.4-beta | Phase 1+2+3+4+5 | 通知推送：学院发布 → 学生 Agent 收到 |
| v1.0-rc | Phase 1-6 全部 | 生产就绪：Docker 部署、监控、文档齐全 |
