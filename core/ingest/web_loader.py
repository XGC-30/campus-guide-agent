"""
网页 / API 数据加载器 — 从学校网站、小程序等在线数据源加载知识

支持的来源：
- 静态网页（HTML 抓取）
- RSS / JSON API
- 小程序数据接口（需要各大学自行实现适配器）
"""

import json
from typing import List, Optional

import requests
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document


class WebLoader:
    """通用网页加载器"""

    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get("web_timeout", 30)
        self.headers = config.get("web_headers", {
            "User-Agent": "CampusGuideAgent/0.1 (Educational Project)"
        })

    def load_from_urls(self, urls: List[str], category: str = "综合") -> List[Document]:
        """从 URL 列表加载网页内容"""
        try:
            loader = WebBaseLoader(
                web_paths=urls,
                header_template=self.headers,
                requests_per_second=2,
            )
            docs = loader.load()

            for doc in docs:
                doc.metadata["category"] = category
                doc.metadata["source_type"] = "web"

            return docs
        except Exception as e:
            import warnings
            warnings.warn(f"网页加载失败: {e}")
            return []

    def load_from_api(self, url: str, params: Optional[dict] = None, category: str = "综合") -> List[Document]:
        """从 REST API 加载数据"""
        try:
            resp = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            # 尝试自动展开 JSON 数组或对象
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 常见: {"data": [...]} 或 {"results": [...]}
                items = data.get("data") or data.get("results") or [data]
            else:
                items = [data]

            docs = []
            for item in items:
                if isinstance(item, dict):
                    content = json.dumps(item, ensure_ascii=False, indent=2)
                else:
                    content = str(item)

                doc = Document(
                    page_content=content,
                    metadata={
                        "category": category,
                        "source_type": "api",
                        "source_name": url,
                    }
                )
                docs.append(doc)

            return docs
        except Exception as e:
            import warnings
            warnings.warn(f"API 加载失败 ({url}): {e}")
            return []
