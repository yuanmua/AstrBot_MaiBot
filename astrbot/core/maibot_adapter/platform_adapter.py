"""
AstrBot 平台适配器
将 MaiBot 的消息发送请求路由回 AstrBot 的平台系统
"""

import asyncio
from typing import Dict, Any, Optional
from collections import defaultdict

from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.maibot_adapter.response_converter import convert_maibot_to_astrbot


class AstrBotPlatformAdapter:
    """AstrBot 平台适配器 - 拦截 MaiBot 的消息发送并路由到 AstrBot"""

    def __init__(self):
        # 存储待发送的消息：{(platform, user_id, group_id): [MessageChain]}
        self._pending_messages: Dict[tuple, list] = defaultdict(list)
        self._message_lock = asyncio.Lock()
        # 存储真实平台映射：{(user_id, group_id): real_platform}
        self._platform_mapping: Dict[tuple, str] = {}

    def register_platform_mapping(self, user_id: str, group_id: Optional[str], real_platform: str):
        """注册真实平台映射"""
        key = (user_id, group_id)
        self._platform_mapping[key] = real_platform
        logger.debug(f"[AstrBot 适配器] 注册平台映射: {key} -> {real_platform}")

    def get_real_platform(self, user_id: str, group_id: Optional[str]) -> str:
        """获取真实平台"""
        key = (user_id, group_id)
        return self._platform_mapping.get(key, "unknown")

    async def send_message(self, message_sending) -> bool:
        """
        拦截 MaiBot 的消息发送请求

        Args:
            message_sending: MaiBot 的 MessageSending 对象

        Returns:
            bool: 是否成功拦截并存储
        """
        try:
            # 获取消息信息（message_info 是对象，不是字典）
            message_info = message_sending.message_info

            user_id = message_info.user_info.user_id if message_info.user_info else None
            group_id = message_info.group_info.group_id if message_info.group_info else None

            # 从平台映射表获取真实平台
            real_platform = self.get_real_platform(user_id, group_id)

            # 转换 MaiBot 消息为 AstrBot MessageChain
            message_chain = convert_maibot_to_astrbot(message_sending.message_segment)

            # 存储消息
            key = (real_platform, user_id, group_id)
            async with self._message_lock:
                self._pending_messages[key].append(message_chain)

            logger.debug(
                f"[AstrBot 适配器] 已拦截 MaiBot 消息: {message_sending.processed_plain_text[:50]} -> {real_platform}"
            )
            return True

        except Exception as e:
            logger.error(f"[AstrBot 适配器] 拦截消息失败: {e}", exc_info=True)
            return False

    async def get_pending_messages(
        self, platform: str, user_id: str, group_id: Optional[str] = None, remove: bool = True
    ) -> list:
        """
        获取待发送的消息

        Args:
            platform: 真实平台名称
            user_id: 用户 ID
            group_id: 群组 ID（可选）
            remove: 是否移除消息（默认True）

        Returns:
            list[MessageChain]: 待发送的消息列表
        """
        key = (platform, user_id, group_id)
        async with self._message_lock:
            if remove:
                messages = self._pending_messages.pop(key, [])
            else:
                messages = self._pending_messages.get(key, []).copy()
        return messages

    def clear_pending_messages(self, platform: str, user_id: str, group_id: Optional[str] = None):
        """清除待发送的消息"""
        key = (platform, user_id, group_id)
        if key in self._pending_messages:
            del self._pending_messages[key]


# 全局单例
_global_adapter: Optional[AstrBotPlatformAdapter] = None


def get_astrbot_adapter() -> AstrBotPlatformAdapter:
    """获取全局 AstrBot 适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = AstrBotPlatformAdapter()
    return _global_adapter
