"""
发送处理模块（MaiBot → AstrBot）

负责：
1. 拦截 MaiBot 的回复消息
2. 转换为 AstrBot 的 MessageChain 格式
3. 通过 IPC 发送到主进程
"""

from .reply_handler import ReplyHandler, create_reply_handler
from .converter import (
    MaiBotToAstrBot,
    seg_to_dict_list,
    convert_maibot_to_astrbot,
)

__all__ = [
    "ReplyHandler",
    "create_reply_handler",
    "MaiBotToAstrBot",
    "seg_to_dict_list",
    "convert_maibot_to_astrbot",
]
