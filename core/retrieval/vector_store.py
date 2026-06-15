"""
向量数据库工厂 — 统一管理和创建向量数据库实例
"""

from pathlib import Path
from typing import List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class VectorStoreFactory:
    """
    向量数据库工厂（当前仅支持 Chroma）

    Chroma 选择理由：
    - 嵌入式部署，零配置（sqlite 文件存储）
    - 校园数据量小（< 1MB 原始 → < 50MB 向量），无需 Milvus 等重型方案
    - LangChain 原生集成，API 简洁
    """

    @staticmethod
    def create(
        persist_dir: str,
        embedding: Embeddings,
        collection_name: str = "campus_knowledge",
        distance_metric: str = "cosine",
    ) -> Chroma:
        """
        创建/加载 Chroma 向量数据库

        Args:
            persist_dir: 持久化目录（如 ./chroma_db）
            embedding: 嵌入模型实例
            collection_name: 集合名称
            distance_metric: 距离度量（cosine | l2 | ip）
        """
        # 自动创建目录
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        return Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding,
            collection_name=collection_name,
            collection_metadata={"hnsw:space": distance_metric},
        )

    @staticmethod
    def from_documents(
        documents: List[Document],
        embedding: Embeddings,
        persist_dir: str,
        collection_name: str = "campus_knowledge",
    ) -> Chroma:
        """
        从文档列表创建向量数据库（入库模式）

        Args:
            documents: 切分后的文档列表
            embedding: 嵌入模型
            persist_dir: 持久化目录
            collection_name: 集合名称
        """
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embedding,
            persist_directory=persist_dir,
            collection_name=collection_name,
            collection_metadata={"hnsw:space": "cosine"},
        )

        return vectorstore
