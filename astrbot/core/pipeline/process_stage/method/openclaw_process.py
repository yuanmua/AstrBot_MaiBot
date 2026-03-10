"""
OpenClaw 处理子阶段
负责将消息路由到 OpenClaw 进行处理（外部网关模式）

工作流程：
1. 检查 openclaw_processing.enable 配置
2. 如果启用，将消息通过 WebSocket/HTTP 发送到 OpenClaw 网关
3. 等待响应并返回给用户
"""

from typing import Optional

from astrbot.api import logger
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.pipeline.context import PipelineContext
from astrbot.core.pipeline.stage import Stage


class OpenClawProcessSubStage(Stage):
    """OpenClaw 消息处理子阶段（外部网关模式）"""

    def __init__(self):
        super().__init__()
        self.client = None

    async def initialize(self, ctx: PipelineContext) -> None:
        self.ctx = ctx
        self.config = ctx.astrbot_config

    async def process(self, event: AstrMessageEvent) -> Optional[bool]:
        """
        处理消息事件，如果开启了 OpenClaw 处理，则路由到 OpenClaw

        Returns:
            如果消息被 OpenClaw 处理，返回 True；否则返回 None
        """
        # 从当前配置中读取 OpenClaw 处理开关
        openclaw_settings = self.config.get("openclaw_processing", {})

        # 确保 openclaw_settings 是字典类型
        if not isinstance(openclaw_settings, dict):
            logger.warning(f"[OpenClaw] openclaw_processing 配置格式错误: {type(openclaw_settings)}")
            return None

        enable_flag = openclaw_settings.get("enable", False)

        if not enable_flag:
            logger.debug(f"[OpenClaw] OpenClaw 处理未启用，继续 AstrBot 流水线")
            return None

        logger.info(f"[OpenClaw] 开始处理: {event.message_str[:100]}")

        try:
            # 获取 OpenClaw 客户端
            if not self.client:
                from astrbot.core.pipeline.process_stage.method.openclaw_client import (
                    OpenClawClient,
                )

                # 安全地获取配置值，提供默认值
                gateway_url = openclaw_settings.get("gateway_url") or "ws://localhost:18789"
                token = openclaw_settings.get("token") or ""

                # 处理 timeout，确保是数字
                timeout_raw = openclaw_settings.get("timeout", 30)
                try:
                    timeout = float(timeout_raw) if timeout_raw else 30.0
                except (ValueError, TypeError):
                    logger.warning(f"[OpenClaw] timeout 配置无效 ({timeout_raw})，使用默认值 30")
                    timeout = 30.0

                connection_type = openclaw_settings.get("connection_type") or "websocket"

                self.client = OpenClawClient(
                    gateway_url=gateway_url,
                    token=token,
                    timeout=timeout,
                    connection_type=connection_type,
                )

                # 建立连接
                connected = await self.client.connect()
                if not connected:
                    logger.error(f"[OpenClaw] 连接 OpenClaw 网关失败")
                    return None

            # 获取消息信息
            message = event.message_str
            sender_id = event.get_sender_id()
            session_id = event.session_id
            platform = event.platform_meta.id

            # 发送消息到 OpenClaw
            result = await self.client.send_message(
                message=message,
                sender_id=sender_id,
                session_id=session_id,
                platform=platform,
            )

            if result:
                # 获取回复内容
                reply_text = result.get("reply", "")
                if reply_text:
                    # 构建消息链并发送回复
                    message_chain = MessageChain()
                    message_chain.chain.append(Plain(reply_text))
                    await event.send(message_chain)
                    logger.info(f"[OpenClaw] 收到回复: {reply_text[:100]}")

                # 停止事件传播（OpenClaw 已经处理）
                event.stop_event()
                return True
            else:
                logger.error(f"[OpenClaw] 未收到有效响应")
                return None

        except Exception as e:
            logger.error(f"[OpenClaw] 处理消息失败: {e}", exc_info=True)
            # 如果 OpenClaw 处理失败，继续由 AstrBot 处理
            return None

    async def disconnect(self) -> None:
        """断开 OpenClaw 连接"""
        if self.client:
            await self.client.disconnect()
            self.client = None
