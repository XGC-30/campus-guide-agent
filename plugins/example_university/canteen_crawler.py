"""
示例：食堂数据爬虫插件

这是一个模板，展示如何为你的大学编写自定义数据源。
实际使用时需根据目标网站/小程序的数据接口进行调整。
"""

from typing import List

from langchain_core.documents import Document

from core.ingest.base import DataSourcePlugin


class CanteenCrawler(DataSourcePlugin):
    """
    示例食堂爬虫插件

    实际场景举例：
    - 爬取学校微信公众号文章中的食堂推荐
    - 接入校园小程序美食投票结果
    - 抓取学生论坛"美食版"热门帖子
    """

    def __init__(self, config: dict):
        super().__init__(config)
        # 各大学自定义配置
        self.target_url = config.get("url", "")
        self.api_endpoint = config.get("api_endpoint", "")

    def load(self) -> List[Document]:
        """
        加载食堂数据（示例实现）

        实际开发时替换为：
        1. requests.get() 抓取网页
        2. 调用校园小程序 API
        3. 从本地 CSV/Excel 文件读取
        4. 从数据库同步
        """

        # ── 以下为示例数据 ──
        sample_data = [
            {
                "name": "第一食堂麻辣香锅",
                "location": "一餐二楼",
                "price": "人均 15 元",
                "rating": "⭐⭐⭐⭐⭐",
                "source": "小程序美食榜",
            },
            {
                "name": "第二食堂铁板饭",
                "location": "二餐二楼",
                "price": "人均 20 元",
                "rating": "⭐⭐⭐⭐⭐",
                "source": "小程序美食榜",
            },
        ]

        docs = []
        for item in sample_data:
            content = (
                f"# {item['name']}\n"
                f"位置：{item['location']}\n"
                f"价格：{item['price']}\n"
                f"评分：{item['rating']}\n"
                f"数据来源：{item['source']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "category": "美食",
                        "source_type": "plugin",
                        "source_name": self.name,
                    },
                )
            )

        return docs

    def validate(self) -> bool:
        """验证数据源可用"""
        # 实际实现：测试网络连接、API Key 等
        return True  # 示例始终返回 True
