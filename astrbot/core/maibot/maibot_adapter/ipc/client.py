"""
IPC 客户端（主进程侧）

负责：
1. 向子进程发送消息（input_queue）
2. 从子进程接收回复（output_queue）
"""

import asyncio
from datetime import datetime
from multiprocessing import Queue
from typing import Any, Callable, Dict, Optional

from .protocol import MessageType, IPCMessage, MessagePayload


class LocalClient:
    """主进程侧的 IPC 客户端"""

    def __init__(
        self,
        input_queue: Queue,
        output_queue: Queue,
        instance_id: str = "default",
    ):
        """
        初始化 IPC 客户端

        Args:
            input_queue: 发送队列（主进程 → 子进程）
            output_queue: 接收队列（子进程 → 主进程）
            instance_id: 实例 ID
        """
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.instance_id = instance_id

        # 回调函数
        self._reply_handler: Optional[Callable] = None
        self._status_handler: Optional[Callable] = None
        self._log_handler: Optional[Callable] = None

    # ========== 发送方法 ==========

    def send_message(self, message_data: Dict[str, Any], stream_id: str) -> None:
        """
        发送用户消息到子进程

        Args:
            message_data: 消息数据（MessageBase 格式的字典）
            stream_id: 流 ID（用于关联回复）
        """
        payload = MessagePayload(
            message_data=message_data,
            stream_id=stream_id,
            instance_id=self.instance_id,
        )

        msg = IPCMessage(
            type=MessageType.MESSAGE,
            payload=payload.to_dict(),
        )

        self.input_queue.put(msg.to_dict())

    def send_ping(self) -> None:
        """发送心跳检测"""
        msg = IPCMessage(type=MessageType.PING, payload={})
        self.input_queue.put(msg.to_dict())

    def send_stop(self) -> None:
        """发送停止命令"""
        msg = IPCMessage(type=MessageType.STOP, payload={})
        self.input_queue.put(msg.to_dict())

    def send_kb_result(self, request_id: str, result: Dict[str, Any]) -> None:
        """
        发送知识库检索结果

        Args:
            request_id: 请求 ID
            result: 检索结果
        """
        payload = {
            "request_id": request_id,
            **result,
        }
        msg = IPCMessage(type=MessageType.KB_RESULT, payload=payload)
        self.input_queue.put(msg.to_dict())

    # ========== 接收方法 ==========

    def register_reply_handler(self, handler: Callable) -> None:
        """
        注册回复处理器

        Args:
            handler: 回调函数，签名: handler(stream_id, segments, processed_plain_text)
        """
        self._reply_handler = handler

    def register_status_handler(self, handler: Callable) -> None:
        """
        注册状态处理器

        Args:
            handler: 回调函数，签名: handler(status, message, error)
        """
        self._status_handler = handler

    def register_log_handler(self, handler: Callable) -> None:
        """
        注册日志处理器

        Args:
            handler: 回调函数，签名: handler(level, message)
        """
        self._log_handler = handler

    async def poll_output(self, timeout: float = 0.1) -> Optional[IPCMessage]:
        """
        非阻塞轮询输出队列

        Args:
            timeout: 超时时间（秒）

        Returns:
            IPCMessage 或 None
        """
        try:
            if self.output_queue.empty():
                await asyncio.sleep(timeout)
                return None

            data = self.output_queue.get_nowait()
            return IPCMessage.from_dict(data)
        except Exception:
            return None

    async def process_output(self, msg: IPCMessage) -> None:
        """
        处理从子进程收到的消息

        Args:
            msg: IPC 消息
        """
        if msg.type == MessageType.REPLY:
            if self._reply_handler:
                payload = msg.payload
                await self._maybe_await(
                    self._reply_handler(
                        payload.get("stream_id"),
                        payload.get("segments", []),
                        payload.get("processed_plain_text", ""),
                    )
                )

        elif msg.type == MessageType.STATUS:
            if self._status_handler:
                payload = msg.payload
                await self._maybe_await(
                    self._status_handler(
                        payload.get("status"),
                        payload.get("message", ""),
                        payload.get("error", ""),
                    )
                )

        elif msg.type == MessageType.LOG:
            if self._log_handler:
                payload = msg.payload
                await self._maybe_await(
                    self._log_handler(
                        payload.get("level"),
                        payload.get("message", ""),
                    )
                )

        elif msg.type == MessageType.PONG:
            # 心跳响应，可以记录或忽略
            pass

    async def _maybe_await(self, result):
        """如果结果是协程，则等待它"""
        if asyncio.iscoroutine(result):
            return await result
        return result
