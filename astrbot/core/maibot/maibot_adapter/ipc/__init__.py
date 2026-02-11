"""
IPC 进程间通信模块

封装主进程与子进程之间的 Queue 通信，提供统一的消息收发接口。
"""

from .protocol import MessageType, IPCMessage
from .client import LocalClient
from .server import LocalServer

__all__ = [
    "MessageType",
    "IPCMessage",
    "LocalClient",
    "LocalServer",
]
