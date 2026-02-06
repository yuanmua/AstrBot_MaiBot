"""
AstrBot 知识库检索模块

使用 Planner 提供的关键词进行知识库检索，并行查询后合并去重返回结果。
"""

import asyncio
import time
from typing import Optional, List, Set
from astrbot.core.maibot.src.common.logger import get_logger
from astrbot.core.maibot.src.chat.knowledge.knowledge_base_adapter import get_kb_adapter, KBRetrievalResult

logger = get_logger("astrbot_knowledge_retrieval")


def _merge_results(all_results: List[List[KBRetrievalResult]], max_results: int = 5) -> List[KBRetrievalResult]:
    """合并多个查询的结果，去重并按分数排序

    Args:
        all_results: 多个查询的结果列表
        max_results: 最大返回结果数

    Returns:
        合并去重后的结果列表
    """
    # 使用内容前200字符作为去重key
    seen_contents: Set[str] = set()
    merged: List[KBRetrievalResult] = []

    # 先收集所有结果
    all_items: List[KBRetrievalResult] = []
    for results in all_results:
        if results:
            all_items.extend(results)

    # 按分数降序排序
    all_items.sort(key=lambda x: x.score, reverse=True)

    # 去重
    for item in all_items:
        content_key = item.content[:200] if item.content else ""
        if content_key and content_key not in seen_contents:
            seen_contents.add(content_key)
            merged.append(item)
            if len(merged) >= max_results:
                break

    return merged


async def build_astrbot_knowledge_prompt(
    message: str,
    sender: str,
    target: str,
    chat_stream,
    unknown_words: Optional[List[str]] = None,
    question: Optional[str] = None,
    kb_keywords: Optional[List[str]] = None,
) -> str:
    """构建 AstrBot 知识库检索结果

    Args:
        message: 聊天历史记录
        sender: 发送者名称
        target: 目标消息内容
        chat_stream: 聊天流对象
        unknown_words: Planner 提供的未知词语列表（未使用，保留兼容）
        question: Planner 提供的问题（未使用，保留兼容）
        kb_keywords: Planner 提供的知识库检索关键词列表

    Returns:
        str: 知识库检索结果字符串
    """
    start_time = time.time()

    # 构造日志前缀（提前构造，方便后续日志输出）
    try:
        group_info = chat_stream.group_info
        user_info = chat_stream.user_info
        if group_info is not None and getattr(group_info, "group_name", None):
            stream_name = group_info.group_name.strip() or str(group_info.group_id)
        elif user_info is not None and getattr(user_info, "user_nickname", None):
            stream_name = user_info.user_nickname.strip() or str(user_info.user_id)
        else:
            stream_name = chat_stream.stream_id
    except Exception:
        stream_name = chat_stream.stream_id
    log_prefix = f"[{stream_name}] " if stream_name else ""

    logger.info(f"{log_prefix}知识库检索任务启动，kb_keywords={kb_keywords}")

    # 检查适配器是否可用
    adapter = get_kb_adapter()
    if adapter is None:
        logger.info(f"{log_prefix}AstrBot 知识库适配器未配置，跳过检索")
        return ""

    try:
        # 收集查询关键词（直接使用 Planner 提供的 kb_keywords）
        queries: List[str] = []
        if kb_keywords:
            for kw in kb_keywords:
                if isinstance(kw, str) and kw.strip():
                    cleaned = kw.strip()
                    if cleaned not in queries:
                        queries.append(cleaned)

        # 如果没有关键词，跳过检索
        if not queries:
            logger.info(f"{log_prefix}Planner 未提供 kb_keywords，跳过知识库检索")
            return ""

        # 限制关键词数量
        queries = queries[:5]
        logger.info(f"{log_prefix}开始知识库检索，关键词: {queries}")

        # 并行执行所有查询
        async def retrieve_single(query: str) -> List[KBRetrievalResult]:
            try:
                return await adapter.retrieve(query)
            except Exception as e:
                logger.error(f"{log_prefix}查询 '{query}' 失败: {e}")
                return []

        all_results = await asyncio.gather(*[retrieve_single(q) for q in queries])

        # 合并结果
        merged_results = _merge_results(all_results, max_results=5)

        if not merged_results:
            end_time = time.time()
            logger.info(f"{log_prefix}知识库检索无结果，耗时: {(end_time - start_time):.3f}秒")
            return "资料库中没有参考结果，不回答或者含糊掩盖过去，不要编造数据"

        # 格式化检索结果
        formatted = []
        for i, r in enumerate(merged_results, 1):
            formatted.append(f"第{i}条资料：{r.content} (相关度: {r.score:.2f}, 来源: {r.kb_name})")
            logger.debug(f"第{i}条资料：{r.content[:50]}... (相关度: {r.score:.2f}, 来源: {r.kb_name})")

        end_time = time.time()
        logger.info(
            f"{log_prefix}知识库检索成功，{len(queries)}个关键词，返回 {len(formatted)} 条结果，耗时: {(end_time - start_time):.3f}秒"
        )

        return "以下是从资料库中检索到的相关信息：\n" + "\n".join(formatted) + "\n请参考这些资料进行回复。\n"

    except Exception as e:
        logger.error(f"{log_prefix}知识库检索异常: {e}")
        return ""
