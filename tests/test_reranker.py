"""
重排器测试
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document


class TestReranker:
    """注意：需要先下载模型才能运行这些测试
    python scripts/download_models.py --rerank-only
    """

    @pytest.mark.slow
    def test_rerank_orders_by_relevance(self):
        """测试重排后相关内容排在前面"""
        try:
            from core.retrieval.reranker import BGEReranker
            reranker = BGEReranker(device="cpu", verbose=False)
        except Exception:
            pytest.skip("重排模型未下载")

        query = "一餐有什么好吃的？"
        docs = [
            Document(
                page_content="一餐的麻辣香锅是全校最好吃的，人均 15 元，在二楼左侧。",
                metadata={"category": "美食"},
            ),
            Document(
                page_content="计算机楼位于校园东区，靠近行政楼。",
                metadata={"category": "校园"},
            ),
            Document(
                page_content="图书馆开放时间是周一至周五 8:00-22:00。",
                metadata={"category": "校园"},
            ),
        ]

        reranked = reranker.rerank(query, docs, top_k=2)
        assert len(reranked) == 2
        assert "美食" in reranked[0].metadata.get("category", "")

    @pytest.mark.slow
    def test_rerank_saves_scores(self):
        """测试重排后在 metadata 中存储分数"""
        try:
            from core.retrieval.reranker import BGEReranker
            reranker = BGEReranker(device="cpu", verbose=False)
        except Exception:
            pytest.skip("重排模型未下载")

        query = "张伟老师的研究方向"
        docs = [
            Document(
                page_content="张伟教授研究方向是人工智能和自然语言处理。",
                metadata={"category": "教师"},
            ),
            Document(
                page_content="王强老师教计算机网络课程。",
                metadata={"category": "教师"},
            ),
        ]

        reranked = reranker.rerank(query, docs, top_k=2)
        assert "rerank_score" in reranked[0].metadata
        assert reranked[0].metadata["rerank_score"] > 0
