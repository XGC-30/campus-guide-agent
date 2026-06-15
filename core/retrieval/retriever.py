"""
智能意图路由检索器

核心功能：
1. 意图识别 — 判断用户问的是教师/美食/路线/校园
2. 分类过滤检索 — 只在相关分类中搜索，避免噪音
3. 关键词解析 — 提取人名、地名等关键实体

设计理念：
  问"李娜的办公室在哪？" → 只在"教师"分类检索，不会被食堂信息干扰
  问"一餐有什么好吃的？" → 只在"美食"分类检索，不会返回教师信息
"""

from typing import Dict, List, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document


class CampusRetriever:
    """
    校园智能检索器

    工作流程：
    1. 分析用户问题 → 识别意图和关键实体
    2. 根据意图路由到对应知识分类
    3. 执行向量检索
    4. 返回结果（交给 Reranker 做重排）
    """

    # 意图关键词配置（可从 config 覆盖）
    DEFAULT_INTENT_KEYWORDS: Dict[str, List[str]] = {
        "教师": [
            "老师", "教授", "导师", "教师", "课程", "上课",
            "办公室", "研究方向", "论文", "科研", "课题组",
            "职称", "副教授", "讲师", "院士",
        ],
        "美食": [
            "吃", "食堂", "饭", "美食", "餐厅", "推荐", "好吃",
            "早餐", "午餐", "晚餐", "外卖", "奶茶", "咖啡", "窗口",
            "小吃", "麻辣", "面", "饭", "面", "粉", "煲",
            "一餐", "二餐", "三餐", "风味", "人均",
        ],
        "路线": [
            "怎么去", "怎么走", "路线", "导航", "在哪里",
            "怎么到", "多远", "附近", "旁边", "对面",
            "步行", "骑车", "公交",
        ],
        "校园": [
            "图书馆", "教学楼", "宿舍", "操场", "体育馆",
            "报到", "新生", "校历", "选课", "社团", "学费",
            "校园卡", "校车", "快递", "自习", "校医院",
        ],
    }

    def __init__(
        self,
        vectorstore: Chroma,
        intent_keywords: Optional[Dict[str, List[str]]] = None,
        initial_k: int = 10,
    ):
        self.vectorstore = vectorstore
        self.intent_keywords = intent_keywords or self.DEFAULT_INTENT_KEYWORDS
        self.initial_k = initial_k

    def _detect_intents(self, query: str) -> List[str]:
        """
        分析用户意图（支持多意图）

        Returns:
            按相关性排序的意图列表，如 ["教师", "路线"] 或 ["美食"]
        """
        scores: Dict[str, int] = {}
        query_lower = query.lower()

        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[intent] = score

        if not scores:
            return ["综合"]

        # 按分数降序排列
        return sorted(scores, key=scores.get, reverse=True)

    def _extract_entities(self, query: str) -> Dict[str, str]:
        """
        提取关键实体（简单规则匹配，可扩展为 NER 模型）

        Returns:
            {"person": "李娜", "place": "一餐", ...}
        """
        entities = {}

        # 提取人名（简单规则："X老师"、"X教授"）
        import re

        person_patterns = [
            r"([^\s]{1,4})(老师|教授|导师|讲师)",
            r"([^\s]{1,3})(的)(办公室|课程|邮箱)",
        ]
        for pattern in person_patterns:
            match = re.search(pattern, query)
            if match:
                entities["person"] = match.group(1)
                break

        # 提取地名（简单规则）
        place_patterns = [
            r"(一餐|二餐|三餐|四餐|五餐)",
            r"(第一食堂|第二食堂|第三食堂)",
            r"(计算机楼|教学楼|图书馆|行政楼|体育馆|宿舍)",
        ]
        for pattern in place_patterns:
            match = re.search(pattern, query)
            if match:
                entities["place"] = match.group(1)
                break

        return entities

    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        intents: Optional[List[str]] = None,
        threshold: float = 0.0,
    ) -> List[Document]:
        """
        执行智能检索

        Args:
            query: 用户问题
            k: 检索数量（默认 self.initial_k）
            intents: 手动指定意图分类（自动检测）
            threshold: 相似度阈值，低于此分数的结果丢弃

        Returns:
            检索到的 Document 列表
        """
        k = k or self.initial_k
        detected_intents = intents or self._detect_intents(query)

        # ── 按分类路由检索 ──
        all_results: List[Document] = []
        seen_ids = set()

        if "综合" in detected_intents or len(detected_intents) > 1:
            # 多意图或综合：各类各取几个
            per_cat = max(1, k // max(len(detected_intents), 1))
            for intent in detected_intents:
                if intent == "综合":
                    # 综合不设 filter，全库检索
                    results = self.vectorstore.similarity_search_with_relevance_scores(
                        query, k=per_cat
                    )
                    for doc, score in results:
                        doc_id = doc.metadata.get("source", "") + doc.page_content[:50]
                        if doc_id not in seen_ids and score >= threshold:
                            doc.metadata["retrieval_score"] = score
                            doc.metadata["matched_intent"] = intent
                            all_results.append(doc)
                            seen_ids.add(doc_id)
                else:
                    results = self.vectorstore.similarity_search_with_relevance_scores(
                        query, k=per_cat, filter={"category": intent}
                    )
                    for doc, score in results:
                        doc_id = doc.metadata.get("source", "") + doc.page_content[:50]
                        if doc_id not in seen_ids and score >= threshold:
                            doc.metadata["retrieval_score"] = score
                            doc.metadata["matched_intent"] = intent
                            all_results.append(doc)
                            seen_ids.add(doc_id)
        else:
            # 单意图：精确过滤检索
            target_intent = detected_intents[0]
            results = self.vectorstore.similarity_search_with_relevance_scores(
                query, k=k, filter={"category": target_intent}
            )
            for doc, score in results:
                if score >= threshold:
                    doc.metadata["retrieval_score"] = score
                    doc.metadata["matched_intent"] = target_intent
                    all_results.append(doc)

        # ── 如果实体匹配到，提升相关文档的排名 ──
        entities = self._extract_entities(query)
        if entities:
            all_results = self._boost_entity_matches(all_results, entities)

        return all_results[:k]

    def _boost_entity_matches(self, docs: List[Document], entities: Dict[str, str]) -> List[Document]:
        """对包含关键实体的文档做轻微加权重排"""
        for doc in docs:
            boost = 0.0
            content = doc.page_content
            for entity_val in entities.values():
                if entity_val and entity_val in content:
                    boost += 0.1
            if hasattr(doc.metadata.get("retrieval_score", 0), "__float__"):
                doc.metadata["retrieval_score"] = doc.metadata.get("retrieval_score", 0) + boost

        # 按分数重排
        return sorted(docs, key=lambda d: d.metadata.get("retrieval_score", 0), reverse=True)
