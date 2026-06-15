"""
通义千问 Ollama 本地模式

优势：
- 完全离线，零费用
- 数据不出本机，隐私安全
- 校园网无需外网访问

前置条件：
1. 安装 Ollama: https://ollama.com
2. 拉取模型: ollama pull qwen2.5:7b
"""

from typing import Optional

from langchain_ollama import ChatOllama

from core.llm.base import LLMProvider


class QwenOllama(LLMProvider):
    """Qwen 本地部署（Ollama）"""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.3,
        num_predict: int = 2048,
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=num_predict,
        )
        self.system_prompt = system_prompt

    def generate(self, query: str, context: str, **kwargs) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        prompt = (
            f"{self.system_prompt or ''}\n\n"
            f"使用以下校园知识来回答问题：\n\n"
            f"{context}\n\n"
            f"用户问题：{query}"
        )
        messages.append(HumanMessage(content=prompt))

        response = self.llm.invoke(messages)
        return response.content

    def __repr__(self) -> str:
        return f"<QwenOllama model={self.model}>"
