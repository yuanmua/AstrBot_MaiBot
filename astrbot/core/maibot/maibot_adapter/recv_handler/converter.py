"""
AstrBot → MaiBot 消息转换器

将 AstrBot 的 AstrMessageEvent 转换为 MaiBot 的 MessageBase 格式。
"""

import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from astrbot.core.maibot.maim_message import (
    MessageBase,
    BaseMessageInfo,
    GroupInfo,
    UserInfo,
    FormatInfo,
    Seg,
)

if TYPE_CHECKING:
    from astrbot.core.platform.astr_message_event import AstrMessageEvent
    from astrbot.core.message.components import BaseMessageComponent


def convert_astrbot_to_maibot(
    event: "AstrMessageEvent",
    config: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    将 AstrMessageEvent 转换为 MaiBot 的 message_data 字典（兼容旧接口）

    Args:
        event: AstrBot 消息事件
        config: AstrBot 配置（用于获取实例ID等）

    Returns:
        message_data 字典
    """
    import hashlib

    # 获取实例ID
    instance_id = "default"
    if config:
        maibot_settings = config.get("maibot_processing", {})
        instance_id = maibot_settings.get("instance_id", "default")

    # 生成 stream_id
    message_obj = event.message_obj
    sender = message_obj.sender
    real_platform = event.platform_meta.name if hasattr(event, "platform_meta") else "unknown"
    user_id = str(sender.user_id) if sender else "unknown"
    group_id = str(message_obj.group.group_id) if message_obj.group else None

    if group_id:
        components = [real_platform, str(group_id)]
    else:
        components = [real_platform, str(user_id), "private"]
    key = "_".join(components)
    stream_id = hashlib.md5(key.encode()).hexdigest()

    return AstrBotToMaiBot.convert_event(event, stream_id, instance_id)


class AstrBotToMaiBot:
    """AstrBot → MaiBot 消息转换器"""

    @staticmethod
    def convert_event(
        event: "AstrMessageEvent",
        stream_id: str,
        instance_id: str = "default",
    ) -> Dict[str, Any]:
        """
        将 AstrMessageEvent 转换为 MaiBot 的 message_data 字典

        Args:
            event: AstrBot 消息事件
            stream_id: 流 ID（用于关联回复）
            instance_id: MaiBot 实例 ID

        Returns:
            message_data 字典（可直接传给 chat_bot.message_process）
        """
        # 构建 platform 标识：astr:{instance_id}:{stream_id}
        platform = f"astr:{instance_id}:{stream_id}"

        # 构建 message_info
        message_info = AstrBotToMaiBot._build_message_info(event, platform)

        # 构建 message_segment
        message_segment = AstrBotToMaiBot._build_message_segment(event)

        # 构建完整的 message_data
        message_data = {
            "message_info": message_info.to_dict(),
            "message_segment": message_segment.to_dict(),
        }

        return message_data

    @staticmethod
    def _build_message_info(
        event: "AstrMessageEvent",
        platform: str,
    ) -> BaseMessageInfo:
        """
        构建 BaseMessageInfo

        Args:
            event: AstrBot 消息事件
            platform: 平台标识

        Returns:
            BaseMessageInfo 对象
        """
        # 获取群组信息
        group_info = None
        if hasattr(event, "message_obj") and event.message_obj:
            group_id = getattr(event.message_obj, "group_id", None)
            if group_id:
                group_info = GroupInfo(
                    platform=platform,
                    group_id=str(group_id),
                    group_name=getattr(event.message_obj, "group_name", None),
                )

        # 获取用户信息
        user_info = None
        sender_id = event.get_sender_id() if hasattr(event, "get_sender_id") else None
        sender_name = event.get_sender_name() if hasattr(event, "get_sender_name") else None

        if sender_id:
            user_info = UserInfo(
                platform=platform,
                user_id=str(sender_id),
                user_nickname=sender_name,
            )

        # 获取消息 ID
        message_id = None
        if hasattr(event, "message_obj") and event.message_obj:
            message_id = getattr(event.message_obj, "message_id", None)

        # 构建格式信息
        format_info = FormatInfo(
            content_format=["text", "image", "emoji"],
            accept_format=["text", "emoji", "reply", "image"],
        )

        return BaseMessageInfo(
            platform=platform,
            message_id=str(message_id) if message_id else None,
            time=time.time(),
            group_info=group_info,
            user_info=user_info,
            format_info=format_info,
        )

    @staticmethod
    def _build_message_segment(event: "AstrMessageEvent") -> Seg:
        """
        构建 Seg 消息段

        Args:
            event: AstrBot 消息事件

        Returns:
            Seg 对象
        """
        # 获取消息链
        message_chain = None
        if hasattr(event, "message_obj") and event.message_obj:
            message_chain = getattr(event.message_obj, "message", None)

        if not message_chain:
            # 如果没有消息链，尝试获取纯文本
            plain_text = event.message_str if hasattr(event, "message_str") else ""
            return Seg(type="text", data=plain_text)

        # 转换消息链为 Seg 列表
        seg_list = AstrBotToMaiBot._convert_message_chain(message_chain)

        if len(seg_list) == 1:
            return seg_list[0]
        else:
            return Seg(type="seglist", data=seg_list)

    @staticmethod
    def _convert_message_chain(message_chain: List["BaseMessageComponent"]) -> List[Seg]:
        """
        将 AstrBot 消息链转换为 Seg 列表

        Args:
            message_chain: AstrBot 消息组件列表

        Returns:
            Seg 列表
        """
        from astrbot.core.message.components import (
            Plain,
            Image,
            At,
            Reply,
            Record,
            Video,
            Face,
            File,
        )

        seg_list = []

        for component in message_chain:
            seg = AstrBotToMaiBot._convert_component(component)
            if seg:
                seg_list.append(seg)

        return seg_list if seg_list else [Seg(type="text", data="")]

    @staticmethod
    def _convert_component(component: "BaseMessageComponent") -> Optional[Seg]:
        """
        将单个 AstrBot 消息组件转换为 Seg

        Args:
            component: AstrBot 消息组件

        Returns:
            Seg 对象或 None
        """
        from astrbot.core.message.components import (
            Plain,
            Image,
            At,
            Reply,
            Record,
            Video,
            Face,
            File,
            ComponentType,
        )

        comp_type = component.type

        # 纯文本
        if comp_type == ComponentType.Plain:
            return Seg(type="text", data=component.text)

        # 图片
        elif comp_type == ComponentType.Image:
            # 优先使用 URL，其次使用 file，最后使用 base64
            if component.url:
                return Seg(type="image", data={"url": component.url})
            elif component.file:
                return Seg(type="image", data={"file": component.file})
            else:
                return Seg(type="image", data="")

        # @提及
        elif comp_type == ComponentType.At:
            return Seg(type="at", data={"qq": str(component.qq)})

        # 回复
        elif comp_type == ComponentType.Reply:
            return Seg(type="reply", data={
                "id": str(component.id),
                "sender_id": component.sender_id,
                "message_str": component.message_str,
            })

        # 语音
        elif comp_type == ComponentType.Record:
            if component.url:
                return Seg(type="voice", data={"url": component.url})
            elif component.file:
                return Seg(type="voice", data={"file": component.file})
            return None

        # 视频
        elif comp_type == ComponentType.Video:
            if hasattr(component, "file") and component.file:
                return Seg(type="video", data={"file": component.file})
            return None

        # QQ 表情
        elif comp_type == ComponentType.Face:
            return Seg(type="face", data={"id": component.id})

        # 文件
        elif comp_type == ComponentType.File:
            return Seg(type="file", data={
                "name": component.name,
                "url": component.url,
                "file": component.file_ if hasattr(component, "file_") else "",
            })

        # 其他类型暂不支持
        else:
            return None
