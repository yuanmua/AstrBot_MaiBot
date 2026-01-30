"""
MaiBot 处理子阶段
负责将消息路由到 MaiBot 进行处理（IPC 模式）

工作流程：
1. 主进程将消息通过 IPC 发送给子进程
2. 子进程中的 MaiBot 处理消息并生成回复
3. 子进程将回复返回给主进程
4. 主进程通过适配器发送回复
"""

import asyncio
import hashlib
import time
from typing import Dict, Optional

from astrbot.api import logger
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.pipeline.context import PipelineContext
from astrbot.core.pipeline.stage import Stage
from astrbot.core.maibot_adapter.response_converter import convert_maibot_to_astrbot


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
            from astrbot.core.maibot_instance.maibot_instance import get_instance_manager
            from astrbot.core.maibot_adapter.platform_adapter import get_astrbot_adapter

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
            from astrbot.core.maibot_adapter import convert_astrbot_to_maibot

            # 生成 stream_id（与 MaiBot 算法一致）
            message_obj = event.message_obj
            sender = message_obj.sender
            real_platform = event.platform_meta.name
            user_id = str(sender.user_id)
            group_id = str(message_obj.group.group_id) if message_obj.group else None
            stream_id = _generate_stream_id(real_platform, user_id, group_id)

            # 转换消息格式（会添加实例ID到 platform）
            maibot_message_data = convert_astrbot_to_maibot(event, self.config)

            # 从转换后的消息中提取 platform（包含实例ID）
            message_info = maibot_message_data.get("message_info", {})
            platform = message_info.get("platform", "")
            chat_id = message_info.get("chat_id", "")

            logger.debug(f"[MaiBot][IPC] platform={platform}, chat_id={chat_id[:50]}...")

            # 解析实例ID
            from astrbot.core.maibot_adapter.platform_adapter import parse_astrbot_instance_id
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
                reply_result = result.get("result", {})
                reply_status = reply_result.get("status", "")

                if reply_status == "replied" and reply_result.get("reply"):
                    # 收到子进程的回复，发送回复
                    reply_data = reply_result["reply"]
                    await self._send_reply(reply_data, stream_id)
                    # 注意：不要在这里删除事件！MaiBot 可能在同一个对话中发送多条消息
                    # 事件会在 _send_reply 中删除（但仅当找到事件时）
                elif reply_status == "processed":
                    # 处理完成但没有回复（MaiBot 可能正在异步生成回复）
                    logger.debug(f"[MaiBot][IPC] 消息已处理，无同步回复")
                    # 不要删除事件，等待 MaiBot 可能的异步回复
                else:
                    logger.debug(f"[MaiBot][IPC] 消息处理完成: {reply_status}")

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

    async def _send_reply(self, reply_data: Dict, stream_id: str) -> None:
        """发送回复消息

        Args:
            reply_data: 子进程返回的回复数据
            stream_id: 流ID
        """
        try:
            message_segment = reply_data.get("message_segment")
            processed_plain_text = reply_data.get("processed_plain_text", "")

            if not message_segment:
                logger.warning(f"[MaiBot][IPC] 回复没有消息段: stream_id={stream_id[:16]}...")
                return

            # 转换 MaiBot 消息为 AstrBot MessageChain
            message_chain = convert_maibot_to_astrbot(message_segment)

            # 获取事件并发送
            current_event = self.adapter.get_event(stream_id)
            if current_event:
                await current_event.send(message_chain)
                logger.info(
                    f"[MaiBot][IPC] 发送回复: {processed_plain_text[:50]} -> stream_id={stream_id[:16]}..."
                )
                # 注意：不要清除事件！MaiBot 可能在同一个对话中发送多条消息
                # 事件会在对话超时时由适配器自动清理
            else:
                logger.warning(
                    f"[MaiBot][IPC] 没有找到事件: stream_id={stream_id[:16]}..."
                )

        except Exception as e:
            logger.error(f"[MaiBot][IPC] 发送回复失败: {e}", exc_info=True)
            # 即使出错也不要删除事件，让后续异步回复有机会找到事件
