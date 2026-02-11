"""
消息接收处理器

负责：
1. 接收 AstrBot 的消息事件
2. 调用转换器转换为 MaiBot 格式
3. 通过 IPC 发送到子进程
"""

from typing import TYPE_CHECKING, Optional

from astrbot.api import logger

from .converter import AstrBotToMaiBot
from ..ipc import LocalClient

if TYPE_CHECKING:
    from astrbot.core.platform.astr_message_event import AstrMessageEvent


class RecvMessageHandler:
    """消息接收处理器"""

    def __init__(
        self,
        ipc_client: LocalClient,
        instance_id: str = "default",
    ):
        """
        初始化消息接收处理器

        Args:
            ipc_client: IPC 客户端
            instance_id: MaiBot 实例 ID
        """
        self.ipc_client = ipc_client
        self.instance_id = instance_id
        self.converter = AstrBotToMaiBot()

    def handle_event(
        self,
        event: "AstrMessageEvent",
        stream_id: str,
    ) -> None:
        """
        处理 AstrBot 消息事件

        Args:
            event: AstrBot 消息事件
            stream_id: 流 ID（用于关联回复）
        """
        try:
            # 转换消息格式
            message_data = self.converter.convert_event(
                event=event,
                stream_id=stream_id,
                instance_id=self.instance_id,
            )

            # 通过 IPC 发送到子进程
            self.ipc_client.send_message(
                message_data=message_data,
                stream_id=stream_id,
            )

            logger.debug(
                f"[RecvHandler] 消息已发送到子进程: "
                f"stream_id={stream_id[:16] if stream_id else 'None'}"
            )

        except Exception as e:
            logger.error(f"[RecvHandler] 处理消息失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
