"""
接收处理模块（AstrBot → MaiBot）

负责：
1. 接收 AstrBot 的消息事件
2. 转换为 MaiBot 的 MessageBase 格式
3. 通过 IPC 发送到子进程
"""

from .message_handler import RecvMessageHandler
from .converter import AstrBotToMaiBot

__all__ = [
    "RecvMessageHandler",
    "AstrBotToMaiBot",
]
