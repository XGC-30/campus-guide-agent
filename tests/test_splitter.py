"""
切分器测试
"""

import pytest
from langchain_core.documents import Document

from core.ingest.splitter import CampusTextSplitter


class TestCampusTextSplitter:
    @pytest.fixture
    def splitter(self):
        return CampusTextSplitter(default_chunk_size=500, default_chunk_overlap=80)

    def test_short_doc_passes_through(self, splitter):
        """短文档不应该被二次切分"""
        doc = Document(
            page_content="张伟教授研究人工智能。",
            metadata={"category": "教师"},
        )
        result = splitter.split([doc])
        assert len(result) == 1

    def test_header_splitting(self, splitter):
        """按 Markdown 标题切分"""
        doc = Document(
            page_content="# 计算机学院\n\n## 张伟\n研究方向：AI\n\n## 李娜\n研究方向：DB",
            metadata={},
        )
        result = splitter.split([doc])
        assert len(result) >= 2

    def test_long_doc_splits(self, splitter):
        """长文档被字符级切分"""
        long_content = "这是一个研究方向。" * 100
        doc = Document(
            page_content=long_content,
            metadata={"category": "课程"},
        )
        result = splitter.split([doc])
        assert len(result) > 1

    def test_category_inference(self, splitter):
        """分类推断"""
        doc = Document(
            page_content="测试内容",
            metadata={"source": "data/demo_university/teachers/test.md"},
        )
        result = splitter.split([doc])
        assert result[0].metadata.get("category") == "教师"

    def test_category_override(self, splitter):
        """分数覆盖生效"""
        splitter_with_override = CampusTextSplitter(
            default_chunk_size=500,
            overrides={"教师": {"chunk_size": 200, "chunk_overlap": 50}},
        )
        # 短内容不会触发二次切分，主要验证配置能正常加载
        doc = Document(
            page_content="张伟教授",
            metadata={"category": "教师"},
        )
        result = splitter_with_override.split([doc])
        assert len(result) == 1
