"""
嵌入模型工厂 — 统一创建各种嵌入模型

支持：
- HuggingFace 本地模型（BGE 系列，推荐中文场景）
- DashScope 通义千问 Embedding API
"""

from langchain_core.embeddings import Embeddings


class EmbedderFactory:
    """嵌入模型工厂"""

    @staticmethod
    def create(model_name: str, device: str = "cpu", normalize: bool = True) -> Embeddings:
        """
        创建嵌入模型实例

        Args:
            model_name: 模型名称
                - BAAI/bge-small-zh-v1.5  (轻量 ~0.4GB)
                - BAAI/bge-large-zh-v1.5 (精确 ~1.3GB)
                - BAAI/bge-m3              (多语言 ~2.2GB)
            device: 运行设备 (cpu | cuda)
            normalize: 是否对向量做归一化（推荐 True）
        """
        # 本地 HuggingFace 模型（默认）
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={
                "normalize_embeddings": normalize,
                "batch_size": 32,
            },
        )

    @staticmethod
    def create_dashscope(api_key: str = None, model: str = "text-embedding-v3") -> Embeddings:
        """
        创建通义千问 Embedding API（不需要本地 GPU）

        Args:
            api_key: DashScope API Key
            model: text-embedding-v1 | text-embedding-v2 | text-embedding-v3
        """
        import os
        from langchain_community.embeddings import DashScopeEmbeddings

        key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")
        return DashScopeEmbeddings(model=model, dashscope_api_key=key)
