"""
MaiBot 处理子阶段
负责将消息路由到 MaiBot 进行处理（IPC 模式）

工作流程：
1. 主进程将消息通过 IPC 发送给子进程
2. 子进程中的 MaiBot 处理消息并生成回复
3. 子进程通过 output_queue 将回复发送给主进程
4. 主进程的 _handle_instance_reply() 负责发送回复
"""

import hashlib
from typing import Optional

from astrbot.api import logger
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.pipeline.context import PipelineContext
from astrbot.core.pipeline.stage import Stage


def _generate_stream_id(platform: str, user_id: str, group_id: Optional[str] = None) -> str:
    """生成聊天流唯一ID，与 MaiBot 的 ChatManager._generate_stream_id 保持一致"""
    if group_id:
        components = [platform, str(group_id)]
    else:
        components = [platform, str(user_id), "private"]
    key = "_".join(components)
    return hashlib.md5(key.encode()).hexdigest()


class MaiBotProcessSubStage(Stage):
    """MaiBot 消息处理子阶段（IPC 模式）"""

    def __init__(self):
        super().__init__()
        self.maibot_manager = None
        self.adapter = None

    async def initialize(self, ctx: PipelineContext) -> None:
        self.ctx = ctx
        self.config = ctx.astrbot_config

    async def process(self, event: AstrMessageEvent) -> Optional[bool]:
        """
        处理消息事件，如果开启了麦麦处理，则路由到 MaiBot（IPC 模式）

        Returns:
            如果消息被 MaiBot 处理，返回 True；否则返回 None
        """
        # 从当前配置中读取麦麦处理开关
        maibot_settings = self.config.get("maibot_processing", {})
        enable_flag = maibot_settings.get("enable", False)

        if not enable_flag:
            logger.debug(f"[MaiBot][IPC] 麦麦处理未启用，继续 AstrBot 流水线")
            return None

        # 动态检查 MaiBot 多实例管理器是否已初始化
        try:
            from astrbot.core.maibot.maibot_adapter.maibot_instance import get_instance_manager
            from astrbot.core.maibot.maibot_adapter import get_astrbot_adapter

            self.maibot_manager = get_instance_manager()
            self.adapter = get_astrbot_adapter()

            if not self.maibot_manager:
                logger.debug(f"[MaiBot][IPC] MaiBot 管理器未初始化，跳过")
                return None

            if not self.adapter:
                logger.debug(f"[MaiBot][IPC] AstrBot 适配器未初始化，跳过")
                return None

            # 检查是否有运行中的实例
            running_instances = self.maibot_manager.get_running_instances()
            if not running_instances:
                logger.debug(f"[MaiBot][IPC] 没有运行中的实例，跳过")
                return None

        except Exception as e:
            logger.debug(f"[MaiBot][IPC] 无法加载 MaiBot 管理器: {e}")
            return None

        logger.info(f"[MaiBot][IPC] 开始处理: {event.message_str[:100]}")

        try:
            # 获取转换器
            from astrbot.core.maibot.maibot_adapter.recv_handler import AstrBotToMaiBot

            message_obj = event.message_obj
            sender = message_obj.sender
            real_platform = event.platform_meta.name
            user_id = str(sender.user_id)
            group_id = str(message_obj.group.group_id) if message_obj.group else None
            stream_id = _generate_stream_id(real_platform, user_id, group_id)

            # 获取实例ID
            maibot_settings = self.config.get("maibot_processing", {})
            instance_id = maibot_settings.get("instance_id", "default")

            # 转换消息格式
            maibot_message_data = AstrBotToMaiBot.convert_event(event, stream_id, instance_id)

            # 从转换后的消息中提取 platform（包含实例ID）
            message_info = maibot_message_data.get("message_info", {})
            platform = message_info.get("platform", "")
            chat_id = message_info.get("chat_id", "")

            logger.debug(f"[MaiBot][IPC] platform={platform}, chat_id={chat_id[:50]}...")

            # 解析实例ID
            from astrbot.core.maibot.maibot_adapter import parse_astrbot_instance_id
            instance_id = parse_astrbot_instance_id(platform) or "default"

            logger.debug(f"[MaiBot][IPC] 路由到实例: {instance_id}")

            # 步骤1：将当前事件存入适配器（按 stream_id 索引）
            self.adapter.set_event(stream_id, event)

            # 步骤2：通过 IPC 队列发送消息给子进程
            result = await self.maibot_manager.send_message(
                instance_id=instance_id,
                message_data=maibot_message_data,
                stream_id=stream_id,
                timeout=30.0,
            )

            if result.get("success"):
                # 消息已提交给子进程处理
                # 回复会通过 output_queue -> _handle_instance_reply() 异步发送
                logger.debug(f"[MaiBot][IPC] 消息已提交处理")

                # 停止事件传播（MaiBot 已经处理）
                event.stop_event()
                return True
            else:
                error = result.get("error", "未知错误")
                logger.error(f"[MaiBot][IPC] 发送消息到实例 {instance_id} 失败: {error}")
                self.adapter.remove_event(stream_id)
                return None

        except Exception as e:
            logger.error(f"[MaiBot][IPC] 处理消息失败: {e}", exc_info=True)
            # 清除事件，防止泄漏
            try:
                if 'stream_id' in locals():
                    self.adapter.remove_event(stream_id)
            except Exception:
                pass
            # 如果 MaiBot 处理失败，继续由 AstrBot 处理
            return None
