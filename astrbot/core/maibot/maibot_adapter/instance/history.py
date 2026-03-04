"""
MaiBot 对话历史保存模块

在主进程侧将 MaiBot 的对话（用户消息 + MaiBot 回复）保存到 AstrBot 会话系统，
使 AstrBot 前端能查看对话历史记录。

参考 InternalAgentSubStage._save_to_history() 的保存格式，
保持与 AstrBot 原生对话历史一致。
"""

import json
from typing import Optional, TYPE_CHECKING

from astrbot.core.log import LogManager

if TYPE_CHECKING:
    from astrbot.core.conversation_mgr import ConversationManager
    from astrbot.core.platform.astr_message_event import AstrMessageEvent

logger = LogManager.GetLogger("maibot_history")


async def save_maibot_history(
    conv_manager: "ConversationManager",
    event: "AstrMessageEvent",
    unified_msg_origin: str,
    reply_text: str,
    instance_id: str = "default",
) -> None:
    """保存 MaiBot 对话历史到 AstrBot 会话系统

    将用户消息和 MaiBot 回复构建为与 internal.py _save_to_history 一致的格式，
    追加到当前会话的对话历史中。

    Args:
        conv_manager: AstrBot 会话管理器
        event: AstrBot 消息事件（包含用户消息）
        unified_msg_origin: 统一消息来源标识符
        reply_text: MaiBot 的回复文本
        instance_id: MaiBot 实例 ID（仅用于日志）
    """
    if not reply_text:
        logger.debug(f"[{instance_id}] 回复为空，跳过历史记录保存")
        return

    try:
        # 获取用户消息文本
        user_message = getattr(event, "message_str", "") or ""

        # 构建新的历史记录条目
        # 格式与 internal.py 的 Message.model_dump() 输出一致：
        # [{"role": "user", "content": [...]}, {"role": "assistant", "content": [...]}]
        new_entries = [
            {
                "role": "user",
                "content": [{"type": "text", "text": user_message}],
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": reply_text}],
            },
        ]

        # 获取当前会话的对话 ID，不存在则新建
        conv_id = await conv_manager.get_curr_conversation_id(unified_msg_origin)
        if not conv_id:
            conv_id = await conv_manager.new_conversation(unified_msg_origin)
            logger.info(f"[{instance_id}] 为 {unified_msg_origin[:16]} 新建对话: {conv_id}")

        # 获取现有历史并追加
        conv = await conv_manager.get_conversation(
            unified_msg_origin=unified_msg_origin,
            conversation_id=conv_id,
        )

        history = []
        if conv and conv.history:
            existing = json.loads(conv.history) if isinstance(conv.history, str) else conv.history
            if isinstance(existing, list):
                history = existing

        history.extend(new_entries)

        # 更新会话历史
        await conv_manager.update_conversation(
            unified_msg_origin=unified_msg_origin,
            conversation_id=conv_id,
            history=history,
        )

        logger.info(
            f"[{instance_id}] 对话历史已保存: "
            f"unified_msg_origin={unified_msg_origin[:16]}, "
            f"记录数={len(history)}"
        )

    except Exception as e:
        logger.error(f"[{instance_id}] 保存对话历史失败: {e}", exc_info=True)
