"""
IPC 消息协议定义

定义主进程与子进程之间通信的消息类型和格式。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


class MessageType:
    """消息类型常量"""

    # ========== 主进程 → 子进程 ==========
    MESSAGE = "message"                    # 用户消息
    PING = "ping"                          # 心跳检测
    STOP = "stop"                          # 停止命令
    KB_RESULT = "kb_retrieve_result"       # 知识库检索结果

    # ========== 子进程 → 主进程 ==========
    STATUS = "status"                      # 状态更新
    LOG = "log"                            # 日志消息
    REPLY = "message_reply"                # 回复消息
    PONG = "pong"                          # 心跳响应
    KB_REQUEST = "kb_retrieve_request"     # 知识库检索请求
    MESSAGE_RESULT = "message_result"      # 消息处理结果


@dataclass
class IPCMessage:
    """IPC 消息格式"""

    type: str                              # 消息类型
    payload: Dict[str, Any]                # 消息载荷
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于 Queue 传输）"""
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPCMessage":
        """从字典创建实例"""
        return cls(
            type=data.get("type", "unknown"),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
        )


@dataclass
class MessagePayload:
    """用户消息载荷"""

    message_data: Dict[str, Any]           # 消息数据（MessageBase 格式）
    stream_id: str                         # 流 ID（用于关联回复）
    instance_id: Optional[str] = None      # 实例 ID

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_data": self.message_data,
            "stream_id": self.stream_id,
            "instance_id": self.instance_id,
        }


@dataclass
class ReplyPayload:
    """回复消息载荷"""

    stream_id: str                         # 流 ID
    instance_id: str                       # 实例 ID
    segments: list                         # 消息段列表（字典格式）
    processed_plain_text: str = ""         # 处理后的纯文本
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stream_id": self.stream_id,
            "instance_id": self.instance_id,
            "segments": self.segments,
            "processed_plain_text": self.processed_plain_text,
            "timestamp": self.timestamp,
        }


@dataclass
class StatusPayload:
    """状态更新载荷"""

    instance_id: str
    status: str                            # running, error, stopped, etc.
    message: str = ""
    error: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "timestamp": self.timestamp,
        }
