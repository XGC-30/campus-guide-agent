"""
Chainlit Web UI — 替换 Streamlit，原生聊天体验 + 流式 + 引用

启动方式:
  chainlit run app/chainlit_app.py
  chainlit run app/chainlit_app.py --port 8080
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chainlit as cl
from chainlit.input_widget import Select, Switch

from core.config import list_universities, load_config
from core.pipeline.rag_chain import CampusRAGPipeline

# ── 启动时加载 ──
UNIVERSITIES = list_universities() or ["demo_university"]


@cl.on_chat_start
async def on_chat_start():
    """初始化会话"""
    settings = await cl.ChatSettings(
        [
            Select(
                id="university",
                label="🏫 选择大学",
                values=UNIVERSITIES,
                initial_value=UNIVERSITIES[0],
            ),
        ]
    ).send()

    university = settings["university"]
    await setup_pipeline(university)


async def setup_pipeline(university: str):
    """加载管道并缓存到 session"""
    pipeline = CampusRAGPipeline(university)

    cl.user_session.set("pipeline", pipeline)
    cl.user_session.set("university", university)

    tools_count = len(pipeline.tools)
    rerank_status = "✅" if pipeline.reranker else "❌"

    await cl.Message(
        content=f"# 🎓 校园新生指南\n\n"
        f"你好！我是 **小园**，{pipeline.university_name} 的百事通～\n\n"
        f"教师信息、食堂美食、校园设施、报到流程……问我就对了！\n\n"
        f"---\n"
        f"🖥️ LLM: `{pipeline.llm}`\n"
        f"🔄 重排器: {rerank_status}\n"
        f"🔧 工具: {tools_count} 个",
    ).send()

    # 快捷提问
    await cl.Message(
        content="💡 **试试这样问我：**\n\n"
        "- 👨‍🏫 计算机学院的张伟教授研究什么方向？\n"
        "- 🍜 一餐有什么好吃的推荐？\n"
        "- 📚 图书馆几点关门？\n"
        "- 🗺️ 从宿舍区怎么去计算机楼？",
    ).send()


@cl.on_settings_update
async def on_settings_update(settings):
    university = settings["university"]
    current = cl.user_session.get("university")
    if university != current:
        await setup_pipeline(university)


@cl.on_message
async def on_message(msg: cl.Message):
    """处理用户消息"""
    pipeline = cl.user_session.get("pipeline")
    if not pipeline:
        await cl.Message(content="⚠️ 系统未初始化，请刷新页面").send()
        return

    query = msg.content.strip()

    # ── Step 1: 意图识别 ──
    t0 = time.perf_counter()
    intents = pipeline.retriever._detect_intents(query)
    entities = pipeline.retriever._extract_entities(query)
    is_complex = len(intents) > 1

    path_label = "🐢 复杂路径（多意图交叉检索）" if is_complex else "⚡ 快速路径（单意图精准检索）"

    async with cl.Step(name=f"{path_label}") as step:
        step.input = query
        intent_detail = f"意图: {', '.join(intents)}"
        if entities:
            entity_str = ", ".join(f"{k}={v}" for k, v in entities.items())
            intent_detail += f"\n实体: {entity_str}"
        step.output = intent_detail

    # ── Step 2: 检索 + 重排 ──
    t1 = time.perf_counter()
    docs = pipeline.retrieve(query)
    retrieval_ms = (time.perf_counter() - t1) * 1000

    # ── Step 3: 准备来源引用 ──
    source_elements = []
    if docs:
        for i, doc in enumerate(docs[:5]):
            cat = doc.metadata.get("category", "未知")
            src = doc.metadata.get("source", "未知来源")
            score = doc.metadata.get("retrieval_score", 0)
            preview = doc.page_content[:120].replace("\n", " ")
            source_elements.append(
                cl.Text(
                    name=f"📄 来源 {i+1}: [{cat}] {src}",
                    content=f"{preview}...\n\n相关性: {score:.3f}",
                    display="side",
                )
            )

    # ── Step 4: LLM 生成 ──
    t2 = time.perf_counter()
    response = pipeline.invoke(query)
    gen_ms = (time.perf_counter() - t2) * 1000

    # ── Step 5: 流式输出回答 ──
    answer_msg = cl.Message(content="", elements=source_elements)
    await answer_msg.send()

    # ponytail: 逐字流式，真 token-level streaming 留给 LLM provider 重写时
    chunk_size = max(1, len(response) // 40)
    for i in range(0, len(response), chunk_size):
        await answer_msg.stream_token(response[i:i + chunk_size])

    await answer_msg.update()

    # ── 日志：可观测性 ──
    print(
        f"[cga] route={'slow' if is_complex else 'fast'} "
        f"intents={intents} "
        f"docs={len(docs)} "
        f"retrieval={retrieval_ms:.0f}ms "
        f"generate={gen_ms:.0f}ms "
        f"total={(time.perf_counter() - t0) * 1000:.0f}ms "
        f"query={query[:80]}"
    )

    # ── 引用展示 ──
    if docs:
        refs = "\n".join(
            f"- [{doc.metadata.get('category', '?')}] "
            f"{doc.metadata.get('source', '?')}"
            for doc in docs[:3]
        )
        await cl.Message(content=f"📚 **知识来源：**\n{refs}", author="system").send()
