"""
MaiBot 适配器模块
负责将 AstrBot 的消息格式转换为 MaiBot 的格式,实现消息互通
包含消息路由功能
"""

from .message_converter import convert_astrbot_to_maibot
from .response_converter import convert_maibot_to_astrbot
from .platform_adapter import (
    parse_astrbot_platform,
    parse_astrbot_instance_id,
    MessageRouter,
    AstrBotPlatformAdapter,
    get_astrbot_adapter,
    initialize_adapter,
)

__all__ = [
    "convert_astrbot_to_maibot",
    "convert_maibot_to_astrbot",
    "parse_astrbot_platform",
    "parse_astrbot_instance_id",
    "MessageRouter",
    "AstrBotPlatformAdapter",
    "get_astrbot_adapter",
    "initialize_adapter",
]
