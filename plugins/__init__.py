"""
Campus Guide Agent 插件系统

各大学可以在此目录下创建自己的数据源插件。
插件需继承 core.ingest.base.DataSourcePlugin 基类。

示例结构：
  plugins/
    ├── my_university/
    │   ├── __init__.py
    │   ├── canteen_crawler.py   # 食堂数据爬虫
    │   ├── teacher_sync.py      # 教师数据同步
    │   └── forum_scraper.py     # 校园论坛抓取
"""

from core.ingest.base import DataSourcePlugin

__all__ = ["DataSourcePlugin"]
