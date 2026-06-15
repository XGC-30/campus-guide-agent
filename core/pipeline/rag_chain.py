"""
RAG 主管道 — 检索增强生成的核心编排器

数据流：
  User Query
    ↓
  意图识别 + 实体提取
    ↓
  ├─→ 分类向量检索 (CampusRetriever)
  │     ↓
  │   BGE Re-ranker 重排 (top-10 → top-3)
  │
  ├─→ 工具调用 (RoutePlanner 等)
  │
  ↓
  组装 Prompt (上下文 + 工具结果 + 用户问题)
    ↓
  Qwen LLM 生成回答
    ↓
  Response
"""

from typing import Optional

from core.config import load_config
from core.llm.base import LLMProvider
from core.llm.qwen_api import QwenDashScope
from core.llm.qwen_ollama import QwenOllama
from core.pipeline.prompt_templates import get_system_prompt
from core.retrieval.embedder import EmbedderFactory
from core.retrieval.reranker import BGEReranker, RerankerFactory
from core.retrieval.retriever import CampusRetriever
from core.retrieval.vector_store import VectorStoreFactory
from core.tools.tool_registry import ToolRegistry


class CampusRAGPipeline:
    """
    Campus RAG 主管道

    使用方式:

        pipeline = CampusRAGPipeline("demo_university")
        response = pipeline.invoke("一餐有什么好吃的？")

    或流式输出:

        for chunk in pipeline.stream("张伟老师的办公室在哪？"):
            print(chunk, end="")
    """

    def __init__(self, university: Optional[str] = None, config: Optional[dict] = None):
        # 加载配置
        self.config = config or load_config(university)
        self.university_name = self.config.get("university", {}).get("name", "")

        model_cfg = self.config["models"]

        # ── 1. 嵌入模型 ──
        emb_cfg = model_cfg["embedding"]
        self.embeddings = EmbedderFactory.create(
            model_name=emb_cfg["model_name"],
            device=emb_cfg.get("device", "cpu"),
            normalize=emb_cfg.get("normalize", True),
        )

        # ── 2. 向量数据库 ──
        vs_cfg = self.config["vectorstore"]
        self.vectorstore = VectorStoreFactory.create(
            persist_dir=vs_cfg["persist_dir"],
            embedding=self.embeddings,
            collection_name=vs_cfg.get("collection_name", "campus_knowledge"),
            distance_metric=vs_cfg.get("distance_metric", "cosine"),
        )

        # ── 3. 检索器 + 重排器 ──
        ret_cfg = self.config.get("retrieval", {})
        self.retriever = CampusRetriever(
            vectorstore=self.vectorstore,
            intent_keywords=self.config.get("intent_keywords"),
            initial_k=ret_cfg.get("initial_k", 10),
        )

        rerank_cfg = model_cfg.get("reranker", {})
        self.reranker: Optional[BGEReranker] = None
        if rerank_cfg.get("model_name"):
            try:
                self.reranker = RerankerFactory.create(
                    model_name=rerank_cfg["model_name"],
                    device=rerank_cfg.get("device", "cpu"),
                    verbose=False,
                )
            except Exception as e:
                import warnings
                warnings.warn(f"重排模型加载失败（将跳过重排步骤）: {e}")
                self.reranker = None

        self.final_k = ret_cfg.get("final_k", 3)

        # ── 4. LLM ──
        llm_cfg = model_cfg["llm"]
        self.llm = self._build_llm(llm_cfg)

        # ── 5. 工具注册器 ──
        self.tools = ToolRegistry(self.config)

    def _build_llm(self, llm_cfg: dict) -> LLMProvider:
        """根据配置构建 LLM"""
        mode = llm_cfg.get("mode", "local")

        if mode == "api":
            api_cfg = llm_cfg.get("dashscope", {})
            return QwenDashScope(
                model=api_cfg.get("model", "qwen-plus"),
                temperature=api_cfg.get("temperature", 0.3),
                max_tokens=api_cfg.get("max_tokens", 2048),
            )
        else:
            ollama_cfg = llm_cfg.get("ollama", {})
            return QwenOllama(
                model=ollama_cfg.get("model", "qwen2.5:7b"),
                base_url=ollama_cfg.get("base_url", "http://localhost:11434"),
                temperature=ollama_cfg.get("temperature", 0.3),
                num_predict=ollama_cfg.get("num_predict", 2048),
            )

    def invoke(self, query: str) -> str:
        """
        执行完整的 RAG 流程（同步）

        Args:
            query: 用户自然语言问题

        Returns:
            小园的回复文本
        """
        # Step 1: 意图识别（由 retriever 内置）
        # Step 2: 分类向量检索
        docs = self.retriever.retrieve(query, k=10)

        # Step 3: Re-ranker 重排
        if self.reranker and docs:
            docs = self.reranker.rerank(query, docs, top_k=self.final_k)

        # Step 4: 构造上下文
        context = "\n\n---\n\n".join(
            f"[{doc.metadata.get('category', '未知')}] {doc.page_content}"
            for doc in docs
        )

        # Step 5: 工具调用（路线规划等）
        tool_result = ""
        if "怎么去" in query or "路线" in query or "在哪" in query or "怎么走" in query:
            route_result = self.tools.invoke_tool("route_planner_amap", query)
            if route_result and "⚠️" not in route_result:
                tool_result = route_result

        # Step 6: 构建 Prompt + LLM 生成
        system_prompt = get_system_prompt(style="full", university_name=self.university_name)
        prompt = system_prompt.format(
            context=context or "（知识库为空，请先入库）",
            tool_result=tool_result or "（无工具辅助信息）",
            query=query,
        )

        response = self.llm.generate(
            query=query,
            context=context,
            system_prompt=prompt,
            tool_result=tool_result,
        )
        return response

    def stream(self, query: str):
        """流式输出（生成器）"""
        # 简化版：非流式生成后逐字返回
        response = self.invoke(query)
        for char in response:
            yield char

    def __repr__(self) -> str:
        status_parts = [
            f"大学: {self.university_name}",
            f"LLM: {self.llm}",
            f"重排器: {'✅' if self.reranker else '❌'}",
            f"工具: {len(self.tools)} 个",
        ]
        return f"<CampusRAGPipeline {' | '.join(status_parts)}>"
