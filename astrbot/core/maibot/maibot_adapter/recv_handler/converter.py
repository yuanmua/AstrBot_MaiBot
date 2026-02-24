"""
AstrBot → MaiBot 消息转换器

将 AstrBot 的 AstrMessageEvent 转换为 MaiBot 的 MessageBase 格式。
"""

import json
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from astrbot.core.maibot.maim_message import (
    BaseMessageInfo,
    GroupInfo,
    UserInfo,
    FormatInfo,
    Seg,
)

if TYPE_CHECKING:
    from astrbot.core.platform.astr_message_event import AstrMessageEvent
    from astrbot.core.message.components import BaseMessageComponent


class AstrBotToMaiBot:
    """AstrBot → MaiBot 消息转换器"""

    @staticmethod
    def convert_event(
        event: "AstrMessageEvent",
        unified_msg_origin: str,
        instance_id: str = "default",
    ) -> Dict[str, Any]:
        """
        将 AstrMessageEvent 转换为 MaiBot 的 message_data 字典

        Args:
            event: AstrBot 消息事件
            unified_msg_origin: 统一消息来源标识符（event.unified_msg_origin）
            instance_id: MaiBot 实例 ID

        Returns:
            message_data 字典���可直接传给 chat_bot.message_process）
        """
        # 获取原始平台名称
        real_platform = event.platform_meta.name if hasattr(event, "platform_meta") else "unknown"

        # 构建 message_info（使用原平台名称，传入 astr 扩展字段）
        message_info = AstrBotToMaiBot._build_message_info(
            event, real_platform, instance_id, unified_msg_origin
        )

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
        instance_id: str = "default",
        unified_msg_origin: str = "",
    ) -> BaseMessageInfo:
        """
        构建 BaseMessageInfo

        Args:
            event: AstrBot 消息事件
            platform: 原始平台名称
            instance_id: AstrBot 实例 ID
            unified_msg_origin: 统一消息来源标识符

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
            astr_instance_id=instance_id,
            astr_stream_id=unified_msg_origin,
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
            ComponentType,
        )

        comp_type = component.type

        # 纯文本
        if comp_type == ComponentType.Plain:
            return Seg(type="text", data=getattr(component, "text", ""))

        # 图片
        elif comp_type == ComponentType.Image:
            # 优先使用 URL，其次使用 file，最后使用 base64
            url = getattr(component, "url", None)
            file = getattr(component, "file", None)
            if url:
                return Seg(type="image", data=json.dumps({"url": url}, ensure_ascii=False))
            elif file:
                return Seg(type="image", data=json.dumps({"file": file}, ensure_ascii=False))
            else:
                return Seg(type="image", data="")

        # @提及
        elif comp_type == ComponentType.At:
            qq = getattr(component, "qq", "")
            return Seg(type="at", data=json.dumps({"qq": str(qq)}, ensure_ascii=False))

        # 回复
        elif comp_type == ComponentType.Reply:
            reply_id = getattr(component, "id", "")
            sender_id = getattr(component, "sender_id", "")
            message_str = getattr(component, "message_str", "")
            return Seg(type="reply", data=json.dumps({
                "id": str(reply_id),
                "sender_id": sender_id,
                "message_str": message_str,
            }, ensure_ascii=False))

        # 语音
        elif comp_type == ComponentType.Record:
            url = getattr(component, "url", None)
            file = getattr(component, "file", None)
            if url:
                return Seg(type="voice", data=json.dumps({"url": url}, ensure_ascii=False))
            elif file:
                return Seg(type="voice", data=json.dumps({"file": file}, ensure_ascii=False))
            return None

        # 视频
        elif comp_type == ComponentType.Video:
            file = getattr(component, "file", None)
            if file:
                return Seg(type="video", data=json.dumps({"file": file}, ensure_ascii=False))
            return None

        # QQ 表情
        elif comp_type == ComponentType.Face:
            face_id = getattr(component, "id", 0)
            return Seg(type="face", data=json.dumps({"id": face_id}, ensure_ascii=False))

        # 文件
        elif comp_type == ComponentType.File:
            name = getattr(component, "name", "")
            url = getattr(component, "url", "")
            file = getattr(component, "file_", "") or getattr(component, "file", "")
            return Seg(type="file", data=json.dumps({
                "name": name,
                "url": url,
                "file": file,
            }, ensure_ascii=False))

        # 其他类型暂不支持
        else:
            return None
