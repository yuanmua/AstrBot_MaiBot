"""
MaiBot 适配器模块
负责将 AstrBot 的消息格式转换为 MaiBot 的格式,实现消息互通
"""

from .message_converter import convert_astrbot_to_maibot
from .response_converter import convert_maibot_to_astrbot, seg_to_dict_list
from .platform_adapter import (
    parse_astrbot_platform,
    parse_astrbot_instance_id,
    AstrBotPlatformAdapter,
    get_astrbot_adapter,
    initialize_adapter,
)
from astrbot.core.maibot.maibot_adapter.maibot_instance import (
    InstanceStatus,
    MaibotInstance,
    MaibotInstanceManager,
    initialize_instance_manager,
    get_instance_manager,
    start_maibot,
    stop_maibot,
    list_instances,
    get_instance_status,
)

__all__ = [
    "convert_astrbot_to_maibot",
    "convert_maibot_to_astrbot",
    "seg_to_dict_list",
    "parse_astrbot_platform",
    "parse_astrbot_instance_id",
    "AstrBotPlatformAdapter",
    "get_astrbot_adapter",
    "initialize_adapter",
    "InstanceStatus",
    "MaibotInstance",
    "MaibotInstanceManager",
    "initialize_instance_manager",
    "get_instance_manager",
    "start_maibot",
    "stop_maibot",
    "list_instances",
    "get_instance_status",
]
