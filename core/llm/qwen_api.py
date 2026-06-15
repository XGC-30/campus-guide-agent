"""
通义千问 DashScope API 模式

优势：
- 不需要本地 GPU / Ollama
- 模型选择更多（turbo/plus/max）
- 性能更强

费用参考（以 qwen-plus 为例）：
  - 输入: ¥0.0008/千 tokens
  - 输出: ¥0.002/千 tokens
  - 新生问答场景每次约 ¥0.003（几乎免费）
"""

import os
from typing import Optional

from langchain_community.chat_models.tongyi import ChatTongyi

from core.llm.base import LLMProvider


class QwenDashScope(LLMProvider):
    """Qwen API 模式（DashScope / 百炼平台）"""

    # 可用模型列表
    AVAILABLE_MODELS = {
        "qwen-turbo": "速度最快，适合简单问答",
        "qwen-plus": "平衡效果与速度（推荐）",
        "qwen-max": "最强效果，复杂推理",
        "qwen-turbo-latest": "最新 Turbo 版本",
    }

    def __init__(
        self,
        model: str = "qwen-plus",
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        key = api_key or os.environ.get("DASHSCOPE_API_KEY", "")

        if not key:
            raise ValueError(
                "请设置 DashScope API Key: \n"
                "  方式 1: 环境变量 export DASHSCOPE_API_KEY=sk-xxx\n"
                "  方式 2: .env 文件 DASHSCOPE_API_KEY=sk-xxx\n"
                "  免费获取: https://dashscope.aliyun.com/"
            )

        self.llm = ChatTongyi(
            model=model,
            dashscope_api_key=key,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.system_prompt = system_prompt

    def generate(self, query: str, context: str, **kwargs) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))

        prompt = (
            f"使用以下校园知识来回答问题：\n\n"
            f"{context}\n\n"
            f"用户问题：{query}"
        )
        messages.append(HumanMessage(content=prompt))

        response = self.llm.invoke(messages)
        return response.content

    def __repr__(self) -> str:
        return f"<QwenDashScope model={self.model}>"
