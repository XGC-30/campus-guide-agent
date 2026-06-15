"""
工具基类 — 所有外部工具的统一接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """外部工具基类

    工具是 RAG 系统的"手"——让 Agent 不只是"说"，
    还能"做"：规划路线、查天气、调用第三方 API 等。
    """

    @abstractmethod
    def invoke(self, query: str, **kwargs) -> str:
        """执行工具，返回格式化结果"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    def description(self) -> str:
        """工具描述（用于 Agent 自动选择工具时阅读）"""
        return self.__doc__ or self.name

    def is_available(self) -> bool:
        """检查工具是否可用（API Key 等）"""
        return True
