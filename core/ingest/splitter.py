"""
校园知识文档切分器 — 两轮切分策略

第一轮：语义边界切分（按 Markdown 标题层级）
第二轮：字符级保护切分（防止超长 chunk）
"""

from typing import Dict, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)


# ── 默认标题层级映射 ──────────────────────────────────────
# 注意：不要用 "category" 作为 key，避免覆盖文件路径推断的分类标签。
# 分类标签（教师/美食/校园）由 markdown_loader.py 从文件路径推断，
# 然后在 splitter._infer_category() 中重新赋值。
DEFAULT_HEADERS = [
    ("#", "chapter"),       # 章节名：学院 / 食堂名称
    ("##", "section"),      # 节名：具体教师 / 具体窗口
    ("###", "subsection"),  # 小节：详情 / 推荐菜
]


class CampusTextSplitter:
    """
    两轮切分器

    设计理念：
    1. 先按标题切，保住语义完整性（每个教师/窗口 = 一个 chunk）
    2. 再按字符切兜底，防止超长（课程介绍等长内容）

    可配置：不同内容类型可用不同的 chunk 参数
    """

    def __init__(
        self,
        default_chunk_size: int = 500,
        default_chunk_overlap: int = 80,
        overrides: Optional[Dict[str, Dict[str, int]]] = None,
        headers: Optional[List[tuple]] = None,
    ):
        self.default_chunk_size = default_chunk_size
        self.default_chunk_overlap = default_chunk_overlap
        self.overrides = overrides or {}
        self.headers = headers or DEFAULT_HEADERS

        # 第一轮：Markdown 标题分割器
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers,
            strip_headers=False,
        )

    def _get_params_for_category(self, category: str) -> tuple:
        """根据文档分类获取 chunk 参数"""
        if category in self.overrides:
            ov = self.overrides[category]
            return ov.get("chunk_size", self.default_chunk_size), ov.get(
                "chunk_overlap", self.default_chunk_overlap
            )
        return self.default_chunk_size, self.default_chunk_overlap

    def _infer_category(self, doc: Document) -> str:
        """从文档元数据中推断分类"""
        # 优先从 header 元数据取
        for key in ("category", "大类", "sub_category", "小类"):
            val = doc.metadata.get(key)
            if val:
                return str(val)

        # 从 source 路径推断
        source = doc.metadata.get("source", "")
        if "teacher" in source or "教师" in source:
            return "教师"
        elif "food" in source or "美食" in source or "食堂" in source:
            return "美食"
        elif "course" in source or "课程" in source:
            return "课程"
        return "校园"

    def split(self, raw_docs: List[Document]) -> List[Document]:
        """
        执行两轮切分

        Args:
            raw_docs: 原始文档列表

        Returns:
            切分后的文档列表（每个 chunk 都是一个独立的语义单元）
        """
        # ── 第一轮：按 Markdown 标题层级切 ──
        header_split_docs: List[Document] = []
        for doc in raw_docs:
            splits = self.header_splitter.split_text(doc.page_content)
            for split in splits:
                # 继承原始元数据
                metadata = doc.metadata.copy()
                metadata.update(split.metadata)
                split.metadata = metadata
                header_split_docs.append(split)

        # ── 第二轮：按字符级切（兜底过长内容）──
        final_docs: List[Document] = []
        for doc in header_split_docs:
            category = self._infer_category(doc)
            chunk_size, chunk_overlap = self._get_params_for_category(category)

            # 给短文档打上分类标签
            doc.metadata["category"] = category

            if len(doc.page_content) <= chunk_size:
                # 内容不超过 chunk_size，无需再切
                final_docs.append(doc)
            else:
                # 超过阈值，按字符级再切一次
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=["\n\n", "\n", "。", "，", " ", ""],
                    length_function=len,
                )
                sub_splits = text_splitter.split_documents([doc])
                final_docs.extend(sub_splits)

        return final_docs
