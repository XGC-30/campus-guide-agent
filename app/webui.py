"""
Streamlit Web UI — 校园新生指南 Web 界面

启动方式:
  streamlit run app/webui.py

首次使用:
  python scripts/init_db.py --university demo_university
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="校园新生指南 · 小园",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# CSS 样式
# ============================================================
st.markdown("""
<style>
    .stChatMessage { padding: 1rem; border-radius: 12px; }
    .main-header { text-align: center; padding: 1rem 0; }
    .stButton button {
        border-radius: 20px; padding: 0.3rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 初始化
# ============================================================
@st.cache_resource
def init_pipeline(university: str):
    """缓存 RAG 管道（避免重复加载模型）"""
    from core.pipeline.rag_chain import CampusRAGPipeline
    return CampusRAGPipeline(university)


# ============================================================
# 侧边栏
# ============================================================
with st.sidebar:
    st.title("🎓 校园新生指南")
    st.markdown("你好！我是 **小园** 🤗")
    st.caption("你的校园生活百事通")

    # 大学选择
    from core.config import list_universities
    universities = list_universities()
    if not universities:
        universities = ["demo_university"]
    university = st.selectbox("🏫 选择大学", universities, index=0)

    st.divider()

    # 快捷入口
    st.subheader("💡 试试这样问我")
    quick_questions = {
        "👨‍🏫 教师": "计算机学院的张伟教授研究什么方向？",
        "🍜 美食": "一餐有什么好吃的推荐？",
        "📚 图书馆": "图书馆几点关门？怎么预约座位？",
        "🗺️ 路线": "从宿舍区怎么去计算机楼？",
        "🎒 报到": "新生报到需要带什么材料？",
    }

    for label, question in quick_questions.items():
        if st.button(f"{label}", use_container_width=True):
            st.session_state.pending_question = question

    st.divider()

    # 状态信息
    with st.expander("📊 系统状态"):
        try:
            pipeline = init_pipeline(university)
            st.caption(f"LLM: {pipeline.llm}")
            st.caption(f"重排器: {'✅ 就绪' if pipeline.reranker else '❌ 未启用'}")
            st.caption(f"工具: {len(pipeline.tools)} 个")
        except Exception as e:
            st.caption(f"⚠️ {e}")

    # 新建对话
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ============================================================
# 主界面
# ============================================================
st.markdown('<h1 class="main-header">🎓 校园新生指南</h1>', unsafe_allow_html=True)
st.caption("有什么想问的？教师、美食、路线、校园生活……我帮你搞定！")

# 对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = ""

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=msg.get("avatar")):
        st.markdown(msg["content"])

# 处理快捷提问
if st.session_state.pending_question:
    prompt = st.session_state.pending_question
    st.session_state.pending_question = ""
else:
    prompt = st.chat_input("问小园关于校园的一切...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt, "avatar": "👤"})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🎓"):
        try:
            pipeline = init_pipeline(university)

            with st.spinner("🤔 小园正在翻书..."):
                response = pipeline.invoke(prompt)

            st.markdown(response)
            st.session_state.messages.append(
                {"role": "assistant", "content": response, "avatar": "🎓"}
            )
        except Exception as e:
            error_msg = f"⚠️ 出错了: {e}"
            st.error(error_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg, "avatar": "🎓"}
            )

# ============================================================
# 底部
# ============================================================
st.divider()
st.caption(
    "💡 提示：数据来自 `data/` 目录的 Markdown 文件。"
    "添加新知识只需在对应分类下创建 .md 文件，然后重新运行 `python scripts/init_db.py`。"
)
