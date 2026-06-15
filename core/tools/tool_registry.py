"""
工具注册器 — 统一管理所有外部工具

设计理念：
  插件式架构，各大学可以注册自己的自定义工具。
  例如：某大学可能有自己的校车实时查询 API、图书馆座位预约 API 等。

使用方式：
  registry = ToolRegistry(config)
  registry.register(RoutePlanner)
  result = registry.get("route_planner").invoke("怎么去图书馆")
"""

from typing import Any, Dict, Optional, Type

from core.tools.base import BaseTool


class ToolRegistry:
    """工具注册器"""

    def __init__(self, config: dict):
        self.config = config
        self._tools: Dict[str, BaseTool] = {}

        # 自动注册内置工具
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""
        tools_cfg = self.config.get("tools", {})

        # 路线规划工具
        route_cfg = tools_cfg.get("route_planner", {})
        if route_cfg.get("enabled", False):
            from core.tools.route_planner import RoutePlanner

            merged_cfg = {**route_cfg, "pois": self.config.get("pois", {})}
            self.register_instance(RoutePlanner(merged_cfg))

    def register(self, tool_cls: Type[BaseTool], **kwargs):
        """注册一个工具类"""
        instance = tool_cls(**kwargs)
        self._tools[instance.name] = instance

    def register_instance(self, tool: BaseTool):
        """注册已实例化的工具"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(name)

    def list_available(self) -> Dict[str, bool]:
        """列出所有工具及其可用状态"""
        return {name: tool.is_available() for name, tool in self._tools.items()}

    def invoke_tool(self, name: str, query: str, **kwargs) -> str:
        """调用指定工具"""
        tool = self._tools.get(name)
        if not tool:
            return f"⚠️ 工具 '{name}' 未注册"
        if not tool.is_available():
            return f"⚠️ 工具 '{name}' 不可用（缺少 API Key 或配置）"
        return tool.invoke(query, **kwargs)

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        tools = self.list_available()
        lines = [f"ToolRegistry ({len(tools)} tools):"]
        for name, available in tools.items():
            status = "✅" if available else "❌"
            lines.append(f"  {status} {name}")
        return "\n".join(lines)
