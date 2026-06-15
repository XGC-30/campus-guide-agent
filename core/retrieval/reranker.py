"""
BGE Re-ranker 重排器

作用：对向量检索的初步结果做精细排序，提升召回准确率。

为什么需要 Re-ranker？
  向量检索（粗排）：速度快但精度有限，用余弦相似度做近似匹配
  交叉编码器（精排）：将 query 和 doc 同时输入模型做交叉注意力计算，精度高但慢

  最优策略：粗排取 10 个 → 精排取 top-3 → 送给 LLM
  这样既保证了速度（初检 10 个），又保证了质量（精排 3 个最相关的）

模型选择：
  BAAI/bge-reranker-v2-m3 — 中文最佳，支持多语言，1.1GB
  替代：BAAI/bge-reranker-v2-minicpm-layerwise — 更轻量
"""

from typing import List, Optional

import torch
from langchain_core.documents import Document
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class RerankerFactory:
    """重排器工厂"""

    @staticmethod
    def create(model_name: str, device: str = "cpu", verbose: bool = False):
        """创建 BGE Re-ranker 实例"""
        return BGEReranker(model_name=model_name, device=device, verbose=verbose)


class BGEReranker:
    """
    BGE Cross-Encoder 重排器

    使用方式：
        reranker = BGEReranker()
        top3 = reranker.rerank(query, docs_from_vector_search, top_k=3)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        device: str = "cpu",
        verbose: bool = False,
    ):
        self.model_name = model_name
        self.verbose = verbose

        if verbose:
            print(f"🔄 加载重排模型: {model_name} ...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        )
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

        if verbose:
            print(f"   ✅ 重排模型已加载 (device={self.device})")

    @torch.no_grad()
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 3,
        return_scores: bool = False,
    ) -> List[Document]:
        """
        对文档列表做重排序

        Args:
            query: 用户原始问题
            documents: 向量检索返回的候选文档（建议 8-15 个）
            top_k: 最终保留几个最相关的
            return_scores: 是否在 metadata 中保留重排分数

        Returns:
            重排后的 top-k 文档
        """
        if not documents:
            return []

        # 构建 (query, doc) 对
        pairs = [[query, doc.page_content] for doc in documents]

        # Tokenize
        inputs = self.tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        ).to(self.device)

        # 推理
        scores = self.model(**inputs, return_dict=True).logits.view(-1).float()
        scores = torch.sigmoid(scores).cpu().numpy()

        # 排序
        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        top_docs = []
        for doc, score in scored_docs[:top_k]:
            doc = doc.copy()  # 避免修改原对象
            doc.metadata["rerank_score"] = float(score)
            doc.metadata["rerank_model"] = self.model_name
            top_docs.append(doc)

        if self.verbose:
            print(f"\n📊 重排完成 (k={len(documents)} → top-{top_k}):")
            for i, doc in enumerate(top_docs):
                cat = doc.metadata.get("category", "未知")
                content_preview = doc.page_content[:60].replace("\n", " ")
                print(f"  {i+1}. [{cat}] (score={doc.metadata['rerank_score']:.3f}) {content_preview}...")

        return top_docs
