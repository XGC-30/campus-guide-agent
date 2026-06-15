"""
检索器单元测试
"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from core.retrieval.retriever import CampusRetriever


@pytest.fixture
def mock_vectorstore():
    vs = MagicMock()
    vs.similarity_search_with_relevance_scores.return_value = [
        (Document(page_content="张伟教授研究人工智能", metadata={"category": "教师"}), 0.85),
        (Document(page_content="李娜副教授教数据库", metadata={"category": "教师"}), 0.72),
    ]
    return vs


@pytest.fixture
def retriever(mock_vectorstore):
    return CampusRetriever(vectorstore=mock_vectorstore, initial_k=5)


class TestIntentDetection:
    def test_teacher_intent(self, retriever):
        intents = retriever._detect_intents("张伟教授研究什么方向？")
        assert "教师" in intents

    def test_food_intent(self, retriever):
        intents = retriever._detect_intents("一餐有什么好吃的？")
        assert "美食" in intents

    def test_route_intent(self, retriever):
        intents = retriever._detect_intents("怎么去计算机楼？")
        assert "路线" in intents

    def test_multi_intent(self, retriever):
        intents = retriever._detect_intents("计算机楼附近的食堂有什么好吃的？")
        assert len(intents) > 1

    def test_fallback_to_general(self, retriever):
        intents = retriever._detect_intents("今天天气怎么样？")
        assert intents == ["综合"]


class TestEntityExtraction:
    def test_extract_person(self, retriever):
        entities = retriever._extract_entities("张伟老师在哪个办公室？")
        assert entities.get("person") == "张伟"

    def test_extract_place(self, retriever):
        entities = retriever._extract_entities("一餐怎么走？")
        assert entities.get("place") == "一餐"


class TestRetrieval:
    def test_basic_retrieval(self, retriever):
        docs = retriever.retrieve("张伟的研究方向", k=2)
        assert len(docs) == 2
        assert "张伟" in docs[0].page_content

    def test_filtered_retrieval(self, retriever):
        docs = retriever.retrieve("教师的研究方向", k=3, intents=["教师"])
        assert len(docs) > 0
        for doc in docs:
            assert doc.metadata.get("matched_intent") == "教师"
