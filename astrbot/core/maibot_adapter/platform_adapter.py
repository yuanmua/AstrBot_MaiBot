"""
AstrBot 平台适配器
存储消息事件，供回复时使用

工作流程：
1. maibot_process.py 收到消息时，调用 set_event() 存储事件
2. 子进程处理完成后，通过 output_queue 发送回复
3. maibot_instance.py 的 _handle_instance_reply() 调用 get_event() 获取事件并发送回复
"""

import asyncio
from typing import Dict, Optional, TYPE_CHECKING

from astrbot.api import logger

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
        return parts[0]
    elif len(parts) == 2:
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

    parts = platform[5:].split(":", 1)

    if len(parts) == 1:
        return "default"
    elif len(parts) == 2:
        return parts[0]

    return None


class AstrBotPlatformAdapter:
    """AstrBot 平台适配器 - 存储消息事件，供回复时使用"""

    _instance_manager: Optional["MaibotInstanceManager"] = None
    _reply_callback: Optional[callable] = None  # 子进程中使用，回复准备好后调用

    def __init__(self):
        # 存储待处理的事件：{stream_id: AstrMessageEvent}
        self._events: Dict[str, "AstrMessageEvent"] = {}
        self._events_lock = asyncio.Lock()

    @classmethod
    def set_instance_manager(cls, manager: "MaibotInstanceManager") -> None:
        """设置实例管理器"""
        cls._instance_manager = manager
        logger.info(f"[AstrBot 适配器] 已设置实例管理器")

    def set_event(self, stream_id: str, event: "AstrMessageEvent"):
        """存储事件，供回复时使用"""
        self._events[stream_id] = event
        logger.debug(f"[AstrBot 适配器] 存储事件: stream_id={stream_id[:16]}...")

    def get_event(self, stream_id: str) -> Optional["AstrMessageEvent"]:
        """获取事件"""
        return self._events.get(stream_id)

    def remove_event(self, stream_id: str):
        """移除事件"""
        if stream_id in self._events:
            del self._events[stream_id]
            logger.debug(f"[AstrBot 适配器] 移除事件: stream_id={stream_id[:16]}...")


# 全局单例
_global_adapter: Optional[AstrBotPlatformAdapter] = None


def get_astrbot_adapter() -> AstrBotPlatformAdapter:
    """获取全局 AstrBot 适配器实例"""
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = AstrBotPlatformAdapter()
    return _global_adapter


async def initialize_adapter(
    instance_manager: Optional["MaibotInstanceManager"] = None,
) -> AstrBotPlatformAdapter:
    """初始化全局适配器

    Args:
        instance_manager: 实例管理器

    Returns:
        AstrBotPlatformAdapter 实例
    """
    adapter = get_astrbot_adapter()

    if instance_manager:
        adapter.set_instance_manager(instance_manager)

    logger.info(f"[AstrBot 适配器] 初始化完成")
    return adapter


def set_reply_callback(callback: callable) -> None:
    """设置回复回调函数（子进程中使用）

    当 monkey patch 拦截到回复消息时，会调用此回调将回复发送给主进程

    Args:
        callback: 回调函数，签名: callback(message, stream_id)
    """
    AstrBotPlatformAdapter._reply_callback = callback
    logger.info(f"[AstrBot 适配器] 回复回调已设置")


__all__ = [
    "parse_astrbot_platform",
    "parse_astrbot_instance_id",
    "AstrBotPlatformAdapter",
    "get_astrbot_adapter",
    "initialize_adapter",
    "set_reply_callback",
]
