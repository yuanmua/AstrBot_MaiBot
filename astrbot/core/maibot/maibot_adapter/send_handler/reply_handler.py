"""
回复处理器

负责：
1. 注册到 maim_message API 的发送消息处理器
2. 拦截 AstrBot 平台的回复消息
3. 通过 IPC 发送到主进程

使用 maim_message 的 register_send_message_handler 机制。
"""

from typing import Callable, Optional, TYPE_CHECKING

from astrbot.core.maibot.maim_message import MessageBase, Seg

from .converter import seg_to_dict_list

if TYPE_CHECKING:
    from ..ipc import LocalServer


class ReplyHandler:
    """
    回复处理器

    注册到 maim_message API 的发送消息处理器，拦截 AstrBot 平台的回复消息。
    """

    def __init__(self, ipc_server: "LocalServer"):
        """
        初始化回复处理器

        Args:
            ipc_server: IPC 服务端（子进程侧）
        """
        self.ipc_server = ipc_server
        self._log_func: Optional[Callable] = None

    def set_logger(self, log_func: Callable) -> None:
        """
        设置日志函数

        Args:
            log_func: 日志函数，签名: log_func(level, message)
        """
        self._log_func = log_func

    def _log(self, level: str, message: str) -> None:
        """内部日志方法"""
        if self._log_func:
            self._log_func(level, message)

    async def handle_outgoing_message(self, message: MessageBase) -> bool:
        """
        处理 MaiBot 发出的消息

        此方法注册到 maim_message API 的发送消息处理器。
        当 MaiBot 调用 send_message 时，会触发此方法。

        Args:
            message: MessageBase 对象

        Returns:
            True 表示消息已处理（AstrBot 平台），False 表示需要继续处理
        """
        try:
            # 获取平台信息
            platform = message.message_info.platform

            # 检查是否是 AstrBot 平台的消息
            stream_id = self._parse_astrbot_platform(platform)
            if not stream_id:
                # 不是 AstrBot 平台，返回 False 让 WebSocket 处理
                return False

            self._log("info", f"[ReplyHandler] 拦截到 AstrBot 回复: stream_id={stream_id[:16]}")

            # 获取消息段
            message_segment = message.message_segment

            # 转换为字典列表
            if message_segment:
                segments = seg_to_dict_list(message_segment)
            else:
                segments = []

            # 获取处理后的纯文本
            processed_plain_text = getattr(message, "processed_plain_text", "")

            # 通过 IPC 发送到主进程
            self.ipc_server.send_reply(
                stream_id=stream_id,
                segments=segments,
                processed_plain_text=processed_plain_text,
            )

            self._log("info", f"[ReplyHandler] 回复已发送到主进程: segments={len(segments)}")

            return True

        except Exception as e:
            self._log("error", f"[ReplyHandler] 处理回复失败: {e}")
            import traceback
            self._log("error", traceback.format_exc())
            return False

    @staticmethod
    def _parse_astrbot_platform(platform: str) -> Optional[str]:
        """
        解析 AstrBot 平台标识，返回 stream_id

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
        # 1. astr:{stream_id} - 旧格式
        # 2. astr:{instance_id}:{stream_id} - 新格式
        if len(parts) == 1:
            return parts[0]
        elif len(parts) == 2:
            return parts[1]

        return None


def create_reply_handler(ipc_server: "LocalServer") -> ReplyHandler:
    """
    创建回复处理器

    Args:
        ipc_server: IPC 服务端

    Returns:
        ReplyHandler 实例
    """
    return ReplyHandler(ipc_server)
