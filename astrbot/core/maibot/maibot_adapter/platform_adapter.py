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
    from astrbot.core.maibot.maibot_adapter.maibot_instance import MaibotInstanceManager


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
        sender_name = event.get_sender_name() if hasattr(event, 'get_sender_name') else "unknown"
        logger.info(f"[AstrBot 适配器] 📥 存储事件: stream_id={stream_id[:16] if stream_id else 'None'}, sender={sender_name}, 当前事件数: {len(self._events)}")

    def get_event(self, stream_id: str) -> Optional["AstrMessageEvent"]:
        """获取事件"""
        event = self._events.get(stream_id)
        if event:
            sender_name = event.get_sender_name() if hasattr(event, 'get_sender_name') else "unknown"
            logger.info(f"[AstrBot 适配器] 📤 获取事件成功: stream_id={stream_id[:16] if stream_id else 'None'}, sender={sender_name}")
        else:
            logger.warning(f"[AstrBot 适配器] ❌ 获取事件失败: stream_id={stream_id[:16] if stream_id else 'None'} 不存在于事件缓存")
            # 打印当前缓存的所有 stream_id（只打印前5个）
            cached_ids = list(self._events.keys())[:5]
            logger.warning(f"[AstrBot 适配器] 当前缓存的事件: {cached_ids}... (共{len(self._events)}个)")
        return event

    def remove_event(self, stream_id: str):
        """移除事件"""
        if stream_id in self._events:
            del self._events[stream_id]
            logger.info(f"[AstrBot 适配器] 🗑️ 移除事件: stream_id={stream_id[:16] if stream_id else 'None'}, 剩余事件数: {len(self._events)}")
        else:
            logger.warning(f"[AstrBot 适配器] ⚠️ 尝试移除不存在的事件: stream_id={stream_id[:16] if stream_id else 'None'}")


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




__all__ = [
    "parse_astrbot_platform",
    "parse_astrbot_instance_id",
    "AstrBotPlatformAdapter",
    "get_astrbot_adapter",
    "initialize_adapter",
]
