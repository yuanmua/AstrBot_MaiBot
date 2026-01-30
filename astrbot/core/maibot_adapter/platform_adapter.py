"""
AstrBot 平台适配器
将 MaiBot 的消息发送请求路由回 AstrBot 的平台系统
包含消息路由功能

支持两种模式：
1. TCP 模式：通过 maim_message 服务器发送消息（传统模式）
2. IPC 模式：通过进程间队列直接发送消息给子进程（多实例模式）
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional, TYPE_CHECKING

from astrbot.api import logger
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.maibot_adapter.response_converter import convert_maibot_to_astrbot

if TYPE_CHECKING:
    from astrbot.core.platform.astr_message_event import AstrMessageEvent
    from astrbot.core.maibot_instance.maibot_instance import MaibotInstanceManager


def parse_astrbot_platform(platform: str) -> Optional[str]:
    """解析 AstrBot 平台标识，返回 stream_id

    Args:
        platform: 平台标识，如 "astr:{stream_id}" 或 "astr:{instance_id}:{stream_id}"

    Returns:
        stream_id 字符串，如果无法解析则返回 None
    """
    if not platform or not platform.startswith("astr:"):
        return None

    # 移除 "astr:" 前缀
    parts = platform[5:].split(":", 1)

    # 可能的格式：
    # 1. astr:{stream_id} - 旧格式（向后兼容）
    # 2. astr:{instance_id}:{stream_id} - 新格式（多实例支持）
    if len(parts) == 1:
        # 旧格式：astr:{stream_id}
        return parts[0]
    elif len(parts) == 2:
        # 新格式：astr:{instance_id}:{stream_id}
        return parts[1]

    return None


def parse_astrbot_instance_id(platform: str) -> Optional[str]:
    """解析 AstrBot 平台标识中的实例ID

    Args:
        platform: 平台标识，如 "astr:{stream_id}" 或 "astr:{instance_id}:{stream_id}"

    Returns:
        实例ID，如果是旧格式则返回 "default"，如果无法解析则返回 None
    """
    if not platform or not platform.startswith("astr:"):
        return None

    # 移除 "astr:" 前缀
    parts = platform[5:].split(":", 1)

    if len(parts) == 1:
        # 旧格式：astr:{stream_id}，默认使用 "default" 实例
        return "default"
    elif len(parts) == 2:
        # 新格式：astr:{instance_id}:{stream_id}
        return parts[0]

    return None


class AstrBotPlatformAdapter:
    """AstrBot 平台适配器 - 拦截 MaiBot 的消息发送并路由回 AstrBot

    支持两种消息路由模式：
    1. IPC 模式（默认，多实例）：主进程发送消息给子进程，子进程处理后返回回复内容
    2. TCP 模式（兼容）：通过 maim_message 服务器发送消息
    """

    # 类变量，控制是否使用 IPC 模式
    # 多实例模式下应为 True，单实例/传统模式下可为 False
    _use_ipc_mode: bool = True
    _instance_manager: Optional["MaibotInstanceManager"] = None
    _reply_callback: Optional[callable] = None  # 用于 IPC 模式，回复准备好后调用

    def __init__(self, data_root: str = "data/maibot"):
        # 存储待发送的消息：{stream_id: AstrMessageEvent}
        self._events: Dict[str, "AstrMessageEvent"] = {}
        self._events_lock = asyncio.Lock()

        # 存储待发送的回复消息（子进程返回）
        self._pending_replies: Dict[str, Any] = {}
        self._pending_replies_lock = asyncio.Lock()

    @classmethod
    def set_instance_manager(cls, manager: "MaibotInstanceManager") -> None:
        """设置实例管理器（用于 IPC 模式）"""
        cls._instance_manager = manager
        logger.info(f"[AstrBot 适配器] 已设置实例管理器，IPC 模式: {cls._use_ipc_mode}")

    @classmethod
    def set_ipc_mode(cls, enabled: bool) -> None:
        """设置是否使用 IPC 模式"""
        cls._use_ipc_mode = enabled
        logger.info(f"[AstrBot 适配器] IPC 模式已{'启用' if enabled else '禁用'}")

    async def initialize(self) -> None:
        """初始化适配器"""
        pass

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

        支持两种模式：
        - IPC 模式：通过进程间队列发送（多实例模式）
        - TCP 模式：通过 maim_message 服务器发送（兼容模式）

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

            # IPC 模式：直接从队列发送消息给 MaiBot 实例
            if self._use_ipc_mode and self._instance_manager:
                return await self._send_message_ipc(message_sending, platform, stream_id)

            # TCP 模式：使用传统方式发送
            return await self._send_message_tcp(message_sending, stream_id)

        except Exception as e:
            logger.error(f"[AstrBot 适配器] 发送消息失败: {e}", exc_info=True)
            return False

    async def _send_message_ipc(self, message_sending, platform: str, stream_id: str) -> bool:
        """IPC 模式发送消息给子进程

        注意：这个方法由主进程调用，用于发送消息给 MaiBot 子进程处理
        不是用于发送回复！回复由子进程中的 MaiBot 直接发送
        """
        try:
            # 从 platform 中解析实例ID
            instance_id = parse_astrbot_instance_id(platform)
            if not instance_id:
                instance_id = "default"

            logger.debug(
                f"[AstrBot 适配器][IPC] 发送消息到实例 {instance_id}: stream_id={stream_id[:16]}..."
            )

            # 通过实例管理器发送消息
            result = await self._instance_manager.send_message(
                instance_id=instance_id,
                message_data={
                    "message_info": {
                        "platform": platform,
                        "stream_id": stream_id,
                    },
                    "message_segment": message_sending.message_segment,
                },
                stream_id=stream_id,
            )

            if result.get("success"):
                logger.info(
                    f"[AstrBot 适配器][IPC] 消息已发送: stream_id={stream_id[:16]}..."
                )
                return True
            else:
                error = result.get("error", "未知错误")
                logger.error(
                    f"[AstrBot 适配器][IPC] 发送失败: stream_id={stream_id[:16]}... error={error}"
                )
                return False

        except Exception as e:
            logger.error(f"[AstrBot 适配器][IPC] 发送消息失败: {e}", exc_info=True)
            return False

    async def _send_message_tcp(self, message_sending, stream_id: str) -> bool:
        """TCP 模式发送消息（传统方式）

        通过 maim_message 服务器发送消息
        """
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
            f"[AstrBot 适配器][TCP] 直接发送消息: {getattr(message_sending, 'processed_plain_text', '')[:50]} -> stream_id={stream_id[:16]}..."
        )

        # 移除事件
        self.remove_event(stream_id)

        return True


# 全局单例
_global_adapter: Optional[AstrBotPlatformAdapter] = None


def get_astrbot_adapter() -> AstrBotPlatformAdapter:
    """获取全局 AstrBot 适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = AstrBotPlatformAdapter()
    return _global_adapter


async def initialize_adapter(
    data_root: str = "data/maibot",
    instance_manager: Optional["MaibotInstanceManager"] = None,
    use_ipc_mode: bool = True,
) -> AstrBotPlatformAdapter:
    """初始化全局适配器

    Args:
        data_root: MaiBot 数据根目录
        instance_manager: 实例管理器（用于 IPC 模式）
        use_ipc_mode: 是否使用 IPC 模式

    Returns:
        AstrBotPlatformAdapter 实例
    """
    adapter = get_astrbot_adapter()

    # 设置 IPC 模式
    adapter.set_ipc_mode(use_ipc_mode)
    if instance_manager:
        adapter.set_instance_manager(instance_manager)

    await adapter.initialize()

    logger.info(f"[AstrBot 适配器] 初始化完成，IPC模式: {use_ipc_mode}")
    return adapter


__all__ = [
    "parse_astrbot_platform",
    "parse_astrbot_instance_id",
    "AstrBotPlatformAdapter",
    "get_astrbot_adapter",
    "initialize_adapter",
    "set_reply_callback",
]


def set_reply_callback(callback: callable) -> None:
    """设置回复回调函数（用于 IPC 模式）

    当 monkey patch 拦截到回复消息时，会调用此回调将回复发送给主进程

    Args:
        callback: 回调函数，签名: callback(message, stream_id)
                  - message: MessageSending 对象
                  - stream_id: 消息流 ID
    """
    AstrBotPlatformAdapter._reply_callback = callback
    logger.info(f"[AstrBot 适配器] 回复回调已设置: {callback is not None}")
