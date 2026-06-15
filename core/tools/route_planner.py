"""
路线规划工具 — 接入高德/百度地图 API

支持：
- 步行路线规划
- 校园 POI 精确匹配
- 标志性建筑路线指引

前置条件：
  高德地图 API Key（免费申请: https://lbs.amap.com/）
"""

import re
import urllib.parse
from typing import Dict, Optional

import requests

from core.tools.base import BaseTool


class RoutePlanner(BaseTool):
    """校园路线规划工具"""

    BAIDU_WALKING_URL = "https://api.map.baidu.com/directionlite/v1/walking"
    AMAP_WALKING_URL = "https://restapi.amap.com/v3/direction/walking"
    AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"

    def __init__(self, config: dict):
        self.provider = config.get("provider", "amap")
        self.api_key = config.get("api_key", "")
        self.campus_pois: Dict[str, Dict[str, float]] = config.get("pois", {})

    @property
    def name(self) -> str:
        return f"route_planner_{self.provider}"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _extract_destination(self, query: str) -> Optional[str]:
        """从自然语言问题中提取目的地 POI 名称"""
        # 优先精确匹配
        for poi_name in self.campus_pois:
            if poi_name in query:
                return poi_name

        # 模糊匹配（含部分名称）
        for poi_name in self.campus_pois:
            # "计算机楼" 匹配 "计算机楼" "计算机"
            short = poi_name.rstrip("楼殿堂馆所区区")
            if short and len(short) >= 2 and short in query:
                return poi_name

        return None

    def _format_steps(self, steps: list, max_steps: int = 5) -> str:
        """格式化路线步骤为易读文本"""
        formatted = []
        for i, step in enumerate(steps[:max_steps], 1):
            instruction = step.get("instruction", step.get("road_name", ""))
            distance = step.get("distance", "")
            if instruction:
                dist_str = f"（约{distance}米）" if distance else ""
                formatted.append(f"  {i}. {instruction}{dist_str}")

        if len(steps) > max_steps:
            formatted.append(f"  ...（共 {len(steps)} 步，已省略后续）")

        return "\n".join(formatted)

    def _plan_amap(self, origin: str, dest_name: str) -> Optional[str]:
        """高德地图路径规划"""
        dest_poi = self.campus_pois[dest_name]
        dest_str = f"{dest_poi['lng']},{dest_poi['lat']}"

        # 如果 origin 是 POI 名称，解析为坐标
        if origin in self.campus_pois:
            origin_poi = self.campus_pois[origin]
            origin = f"{origin_poi['lng']},{origin_poi['lat']}"

        params = {
            "key": self.api_key,
            "origin": origin,
            "destination": dest_str,
            "output": "json",
        }

        try:
            resp = requests.get(self.AMAP_WALKING_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return f"⚠️ 路线规划请求失败: {e}"

        if data.get("status") != "1":
            return f"⚠️ 路线规划失败：{data.get('info', '未知错误')}"

        route = data["route"]["paths"][0]
        steps_text = self._format_steps(route["steps"])

        return (
            f"🗺️ **从 {origin} 到 {dest_name} 步行路线**\n\n"
            f"- 📏 距离：约 **{int(route['distance'])}** 米\n"
            f"- ⏱ 预计：约 **{int(int(route['duration']) / 60)}** 分钟\n\n"
            f"**路线指引：**\n{steps_text}"
        )

    def invoke(self, query: str, **kwargs) -> str:
        """
        规划校园路线

        Args:
            query: 用户自然语言问题（如"从宿舍怎么去计算机楼？"）
            origin: 起点（默认使用 kwargs 中的或"当前位置"）

        Returns:
            格式化的路线文本
        """
        if not self.is_available():
            return "⚠️ 路线规划功能未启用，请配置地图 API Key"

        origin = kwargs.get("origin", "当前位置")
        destination = self._extract_destination(query)

        if not destination:
            known_pois = "、".join(list(self.campus_pois.keys())[:8])
            return (
                f"⚠️ 未能识别目的地。\n"
                f"已知校园地点：{known_pois} 等\n"
                f"请尝试使用完整名称，如\"怎么去计算机楼\""
            )

        if self.provider == "amap":
            return self._plan_amap(origin, destination) or ""
        elif self.provider == "baidumap":
            return "⚠️ 百度地图模式开发中，请使用高德地图（provider: amap）"
        else:
            return f"⚠️ 不支持的地图提供商: {self.provider}"
