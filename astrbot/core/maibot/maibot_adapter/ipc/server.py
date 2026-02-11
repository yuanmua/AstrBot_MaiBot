"""
IPC 服务端（子进程侧）

负责：
1. 从主进程接收消息（input_queue）
2. 向主进程发送回复（output_queue）
"""

import asyncio
from datetime import datetime
from multiprocessing import Queue
from typing import Any, Callable, Dict, Optional

from .protocol import MessageType, IPCMessage, ReplyPayload, StatusPayload


class LocalServer:
    """子进程侧的 IPC 服务端"""

    def __init__(
        self,
        input_queue: Queue,
        output_queue: Queue,
        instance_id: str = "default",
    ):
        """
        初始化 IPC 服务端

        Args:
            input_queue: 接收队列（主进程 → 子进程）
            output_queue: 发送队列（子进程 → 主进程）
            instance_id: 实例 ID
        """
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.instance_id = instance_id

        # 消息处理器
        self._message_handler: Optional[Callable] = None
        self._kb_result_handler: Optional[Callable] = None

    # ========== 发送方法 ==========

    def send_reply(
        self,
        stream_id: str,
        segments: list,
        processed_plain_text: str = "",
    ) -> None:
        """
        发送回复消息到主进程

        Args:
            stream_id: 流 ID
            segments: 消息段列表（字典格式）
            processed_plain_text: 处理后的纯文本
        """
        payload = ReplyPayload(
            stream_id=stream_id,
            instance_id=self.instance_id,
            segments=segments,
            processed_plain_text=processed_plain_text,
        )

        msg = IPCMessage(
            type=MessageType.REPLY,
            payload=payload.to_dict(),
        )

        self.output_queue.put(msg.to_dict())

    def send_status(
        self,
        status: str,
        message: str = "",
        error: str = "",
    ) -> None:
        """
        发送状态更新到主进程

        Args:
            status: 状态（running, error, stopped 等）
            message: 状态消息
            error: 错误信息
        """
        payload = StatusPayload(
            instance_id=self.instance_id,
            status=status,
            message=message,
            error=error,
        )

        msg = IPCMessage(
            type=MessageType.STATUS,
            payload=payload.to_dict(),
        )

        self.output_queue.put(msg.to_dict())

    def send_log(self, level: str, message: str) -> None:
        """
        发送日志到主进程

        Args:
            level: 日志级别（info, warning, error 等）
            message: 日志消息
        """
        msg = IPCMessage(
            type=MessageType.LOG,
            payload={
                "level": level,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
        )

        self.output_queue.put(msg.to_dict())

    def send_pong(self) -> None:
        """发送心跳响应"""
        msg = IPCMessage(
            type=MessageType.PONG,
            payload={"instance_id": self.instance_id},
        )
        self.output_queue.put(msg.to_dict())

    def send_message_result(
        self,
        success: bool,
        result: Any = None,
        error: str = "",
    ) -> None:
        """
        发送消息处理结果

        Args:
            success: 是否成功
            result: 处理结果
            error: 错误信息
        """
        msg = IPCMessage(
            type=MessageType.MESSAGE_RESULT,
            payload={
                "success": success,
                "result": result,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            },
        )

        self.output_queue.put(msg.to_dict())

    def send_kb_request(self, request_id: str, query: str, **kwargs) -> None:
        """
        发送知识库检索请求

        Args:
            request_id: 请求 ID
            query: 查询内容
            **kwargs: 其他参数
        """
        msg = IPCMessage(
            type=MessageType.KB_REQUEST,
            payload={
                "request_id": request_id,
                "query": query,
                "instance_id": self.instance_id,
                **kwargs,
            },
        )

        self.output_queue.put(msg.to_dict())

    # ========== 接收方法 ==========

    def register_message_handler(self, handler: Callable) -> None:
        """
        注册消息处理器

        Args:
            handler: 回调函数，签名: handler(message_data, stream_id)
        """
        self._message_handler = handler

    def register_kb_result_handler(self, handler: Callable) -> None:
        """
        注册知识库结果处理器

        Args:
            handler: 回调函数，签名: handler(request_id, result)
        """
        self._kb_result_handler = handler

    async def poll_input(self, timeout: float = 0.05) -> Optional[IPCMessage]:
        """
        非阻塞轮询输入队列

        Args:
            timeout: 超时时间（秒）

        Returns:
            IPCMessage 或 None
        """
        try:
            if self.input_queue.empty():
                await asyncio.sleep(timeout)
                return None

            data = self.input_queue.get_nowait()
            return IPCMessage.from_dict(data)
        except Exception:
            return None

    async def process_input(self, msg: IPCMessage) -> Optional[str]:
        """
        处理从主进程收到的消息

        Args:
            msg: IPC 消息

        Returns:
            命令类型（用于特殊处理，如 "stop"）
        """
        if msg.type == MessageType.MESSAGE:
            if self._message_handler:
                payload = msg.payload
                result = self._message_handler(
                    payload.get("message_data"),
                    payload.get("stream_id"),
                )
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)

        elif msg.type == MessageType.PING:
            self.send_pong()

        elif msg.type == MessageType.STOP:
            return "stop"

        elif msg.type == MessageType.KB_RESULT:
            if self._kb_result_handler:
                payload = msg.payload
                request_id = payload.get("request_id")
                self._kb_result_handler(request_id, payload)

        return None
