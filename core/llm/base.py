"""
LLM 抽象接口 — 所有 LLM 后端的统一基类
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Iterator, Optional


class LLMProvider(ABC):
    """LLM 提供者基类"""

    @abstractmethod
    def generate(self, query: str, context: str, **kwargs) -> str:
        """同步生成回答"""
        ...

    async def agenerate(self, query: str, context: str, **kwargs) -> str:
        """异步生成回答（子类可选实现）"""
        raise NotImplementedError("该模型不支持异步调用")

    def stream(self, query: str, context: str, **kwargs) -> Iterator[str]:
        """流式生成（子类可选实现）"""
        # 默认回退到非流式
        yield self.generate(query, context, **kwargs)

    async def astream(self, query: str, context: str, **kwargs) -> AsyncIterator[str]:
        """异步流式生成（子类可选实现）"""
        raise NotImplementedError("该模型不支持异步流式调用")
