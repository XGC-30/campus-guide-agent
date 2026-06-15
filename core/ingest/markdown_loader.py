"""
Markdown 知识加载器 — 从本地 Markdown 文件加载校园知识
"""

import glob
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document


class MarkdownLoader:
    """
    Markdown 文件加载器

    从 data/ 目录加载所有 .md 文件，
    自动从文件路径推断分类标签。
    """

    # 路径关键词 → 分类标签映射
    PATH_CATEGORY_MAP = {
        "teacher": "教师",
        "food": "美食",
        "canteen": "美食",
        "食堂": "美食",
        "course": "课程",
        "campus": "校园",
        "faq": "校园",
        "dorm": "校园",
        "library": "校园",
    }

    def __init__(self, data_dir: str = "data", encoding: str = "utf-8"):
        self.data_dir = Path(data_dir)
        self.encoding = encoding

    def _infer_category_from_path(self, file_path: str) -> str:
        """从文件路径推断知识分类"""
        path_lower = file_path.lower()
        for keyword, category in self.PATH_CATEGORY_MAP.items():
            if keyword in path_lower:
                return category
        return "综合"

    def _infer_source_name(self, file_path: str) -> str:
        """从文件路径提取数据来源名称"""
        parts = Path(file_path).parts
        # 取 data_dir 之后的路径作为标识
        try:
            idx = parts.index(self.data_dir.name)
            return "/".join(parts[idx + 1 :])
        except (ValueError, IndexError):
            return Path(file_path).name

    def load(self) -> List[Document]:
        """加载所有 Markdown 文件"""
        pattern = str(self.data_dir / "**" / "*.md")
        md_files = glob.glob(pattern, recursive=True)

        if not md_files:
            raise FileNotFoundError(
                f"在 {self.data_dir} 目录下未找到任何 .md 文件。\n"
                f"请创建 Markdown 知识文件，参考 data/demo_university/ 示例。"
            )

        all_docs: List[Document] = []
        for file_path in md_files:
            try:
                loader = TextLoader(file_path, encoding=self.encoding)
                docs = loader.load()

                category = self._infer_category_from_path(file_path)
                source_name = self._infer_source_name(file_path)

                for doc in docs:
                    doc.metadata["category"] = category
                    doc.metadata["source_type"] = "markdown"
                    doc.metadata["source_name"] = source_name

                all_docs.extend(docs)
            except Exception as e:
                import warnings

                warnings.warn(f"加载文件失败 ({file_path}): {e}")

        return all_docs
