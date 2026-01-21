"""
MaiBot 处理子阶段
负责将消息路由到 MaiBot 进行处理

工作流程：
1. 生成 stream_id 并将 AstrMessageEvent 存入适配器（按 stream_id 索引）
2. 调用 MaiBot 的 message_process 触发消息处理
3. MaiBot 生成回复时，monkey patch 根据 stream_id 找到事件并直接发送
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
    """MaiBot 消息处理子阶段"""

    async def initialize(self, ctx: PipelineContext) -> None:
        self.ctx = ctx
        self.config = ctx.astrbot_config

    async def process(self, event: AstrMessageEvent) -> Optional[bool]:
        """
        处理消息事件，如果开启了麦麦处理，则路由到 MaiBot

        Returns:
            如果消息被 MaiBot 处理，返回 True；否则返回 None
        """
        # 动态检查 MaiBot 多实例管理器是否已初始化
        instance_manager = None
        message_router = None

        try:
            # 尝试从 core_lifecycle 中获取实例管理器
            # 注：MaiBot 已由多实例管理器接管，不再使用全局 maibot_core
            from astrbot.core.core_lifecycle import core

            instance_manager = getattr(core, 'instance_manager', None)
            message_router = getattr(core, 'message_router', None)

            # 检查多实例管理器是否已初始化
            if not instance_manager or not message_router:
                logger.debug(f"[MaiBot] 多实例管理器未初始化，跳过")
                return None

            # 检查是否有运行中的实例
            running_instances = instance_manager.get_running_instances()
            if not running_instances:
                logger.debug(f"[MaiBot] 没有运行中的实例，跳过")
                return None

        except Exception as e:
            logger.debug(f"[MaiBot] 无法加载多实例管理器: {e}")
            return None

        # 从当前配置中读取麦麦处理开关
        maibot_settings = self.config.get("maibot_processing", {})
        enable_flag = maibot_settings.get("enable", False)

        if not enable_flag:
            logger.debug(f"[MaiBot] 麦麦处理未启用，继续 AstrBot 流水线")
            return None

        logger.info(f"[MaiBot] 开始处理: {event.message_str[:100]}")

        try:
            # 获取适配器和转换器
            from astrbot.core.maibot_adapter.platform_adapter import get_astrbot_adapter
            from astrbot.core.maibot_adapter import convert_astrbot_to_maibot
            from astrbot.core.maibot.chat.message_receive.bot import chat_bot

            adapter = get_astrbot_adapter()

            # 生成 stream_id（与 MaiBot 算法一致）
            message_obj = event.message_obj
            sender = message_obj.sender
            real_platform = event.platform_meta.name
            user_id = str(sender.user_id)
            group_id = str(message_obj.group.group_id) if message_obj.group else None
            stream_id = _generate_stream_id(real_platform, user_id, group_id)

            # 步骤1：将当前事件存入适配器（按 stream_id 索引）
            adapter.set_event(stream_id, event)
            logger.debug(f"[MaiBot] 已设置事件: stream_id={stream_id[:16]}...")

            # 转换消息格式（使用 stream_id 作为 platform 标识）
            maibot_message_data = convert_astrbot_to_maibot(event)

            # 验证 stream_id 是否正确生成
            message_info = maibot_message_data.get("message_info", {})
            logger.debug(f"[MaiBot] message_info.platform: {message_info.get('platform', 'N/A')}")

            # 步骤2：调用 MaiBot 处理消息
            # 注意：message_process 不会等待回复生成，回复在后台循环中异步生成
            # 当 MaiBot 生成回复并调用 send_message 时，monkey patch 会根据 stream_id 找到事件并直接发送
            await chat_bot.message_process(maibot_message_data)
            logger.debug(f"[MaiBot] message_process 完成")

            # 注意：不要在这里清除事件！
            # MaiBot 生成回复时会在 monkey patch 中自动清除事件

            # 停止事件传播（MaiBot 已经处理）
            event.stop_event()

            logger.debug(f"[MaiBot] 消息处理完成")
            return True

        except Exception as e:
            logger.error(f"[MaiBot] 处理消息失败: {e}", exc_info=True)
            # 清除事件，防止泄漏
            try:
                if 'stream_id' in locals():
                    adapter.remove_event(stream_id)
            except Exception:
                pass
            # 如果 MaiBot 处理失败，继续由 AstrBot 处理
            return None
