"""
AstrBot 平台适配器
将 MaiBot 的消息发送请求路由回 AstrBot 的平台系统
"""

import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING
from collections import defaultdict

from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.maibot_adapter.response_converter import convert_maibot_to_astrbot

if TYPE_CHECKING:
    from astrbot.core.platform.astr_message_event import AstrMessageEvent


def parse_astrbot_platform(platform: str) -> Optional[str]:
    """解析 AstrBot 平台标识，返回 stream_id

    Args:
        platform: 平台标识，如 "astr:{stream_id}"

    Returns:
        stream_id 字符串，如果无法解析则返回 None
    """
    if platform and platform.startswith("astr:"):
        return platform[5:]  # 去掉 "astr:" 前缀
    return None


class AstrBotPlatformAdapter:
    """AstrBot 平台适配器 - 拦截 MaiBot 的消息发送并路由回 AstrBot"""

    def __init__(self):
        # 存储待发送的消息：{stream_id: AstrMessageEvent}
        self._events: Dict[str, "AstrMessageEvent"] = {}
        self._events_lock = asyncio.Lock()

    def set_event(self, stream_id: str, event: "AstrMessageEvent"):
        """设置当前正在处理的 AstrMessageEvent"""
        self._events[stream_id] = event
        logger.debug(f"[AstrBot 适配器] 设置事件: stream_id={stream_id[:16]}...")

    def get_event(self, stream_id: str) -> Optional["AstrMessageEvent"]:
        """获取当前正在处理的 AstrMessageEvent"""
        return self._events.get(stream_id)

    def remove_event(self, stream_id: str):
        """移除事件"""
        if stream_id in self._events:
            del self._events[stream_id]
            logger.debug(f"[AstrBot 适配器] 移除事件: stream_id={stream_id[:16]}...")

    async def send_message(self, message_sending) -> bool:
        """
        拦截 MaiBot 的消息发送请求，直接发送回 AstrBot 平台

        Args:
            message_sending: MaiBot 的 MessageSending 对象

        Returns:
            bool: 是否成功拦截并发送
        """
        try:
            # 获取消息信息
            message_info = message_sending.message_info

            # 从 platform 中解析 stream_id
            platform = getattr(message_info, 'platform', None)
            stream_id = parse_astrbot_platform(platform)

            if not stream_id:
                logger.warning(f"[AstrBot 适配器] 无法解析平台标识: {platform}")
                return False

            # 获取当前事件
            current_event = self.get_event(stream_id)
            if not current_event:
                logger.warning(f"[AstrBot 适配器] 没有当前事件 stream_id={stream_id[:16]}...")
                return False

            # 转换 MaiBot 消息为 AstrBot MessageChain
            message_chain = convert_maibot_to_astrbot(message_sending.message_segment)

            # 直接通过 AstrBot 发送
            await current_event.send(message_chain)

            logger.info(
                f"[AstrBot 适配器] 直接发送消息: {getattr(message_sending, 'processed_plain_text', '')[:50]} -> stream_id={stream_id[:16]}..."
            )

            # 移除事件
            self.remove_event(stream_id)

            return True

        except Exception as e:
            logger.error(f"[AstrBot 适配器] 发送消息失败: {e}", exc_info=True)
            return False


# 全局单例
_global_adapter: Optional[AstrBotPlatformAdapter] = None


def get_astrbot_adapter() -> AstrBotPlatformAdapter:
    """获取全局 AstrBot 适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = AstrBotPlatformAdapter()
    return _global_adapter
