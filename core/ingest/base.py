"""
数据源插件基类 — 各大学可自定义爬虫/加载器
"""

from abc import ABC, abstractmethod
from typing import List

from langchain_core.documents import Document


class DataSourcePlugin(ABC):
    """数据源插件基类

    各大学通过继承此类实现自定义数据加载逻辑。
    例如：爬取校内论坛、小程序 API 数据、教务系统等。
    """

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def load(self) -> List[Document]:
        """加载数据，返回 Document 列表"""
        ...

    @abstractmethod
    def validate(self) -> bool:
        """验证数据源是否可用（网络连通性、API 密钥等）"""
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"<DataSourcePlugin: {self.name}>"
