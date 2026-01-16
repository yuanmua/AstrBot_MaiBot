"""
AstrBot 消息 → MaiBot 消息格式转换器
"""

import time
from typing import Any, Dict

from astrbot.core.platform.astr_message_event import AstrMessageEvent
from astrbot.core.message.components import (
    Plain,
    Image,
    Record,
    Video,
    Face,
    At,
    AtAll,
    Reply,
    File,
    WechatEmoji,
    ComponentType,
)


def convert_astrbot_to_maibot(event: AstrMessageEvent) -> Dict[str, Any]:
    """
    将 AstrBot 的 AstrMessageEvent 转换为 MaiBot 的 message_data 格式

    Args:
        event: AstrBot 消息事件对象

    Returns:
        Dict: MaiBot 期望的 message_data 字典
    """
    message_obj = event.message_obj

    # 1. 构建 group_info（如果是群聊）
    group_info = None
    if message_obj.group:
        group_info = {
            "group_id": str(message_obj.group.group_id),
            "group_name": message_obj.group.group_name or "",
        }

    # 2. 构建 user_info（平台统一为 AstrBot）
    sender = message_obj.sender
    user_info = {
        "platform": "AstrBot",  # 统一平台名称
        "user_id": str(sender.user_id),
        "user_nickname": sender.nickname or "",
        "user_cardname": getattr(sender, "card", None) or "",  # 群昵称
    }

    # 3. 转换消息段（message_segment）
    message_segments = []
    for component in message_obj.message:
        seg = _convert_component_to_seg(component)
        if seg:
            message_segments.append(seg)

    # 如果没有消息段，至少添加一个纯文本段
    if not message_segments and message_obj.message_str:
        message_segments.append({"type": "text", "data": message_obj.message_str})

    # 创建消息段字典（注意：不要创建 Seg 对象，MaiBot 会自己转换）
    message_segment = {
        "type": "seglist",
        "data": message_segments
    }

    # 4. 构建 message_info（平台统一设为 AstrBot，由 AstrBot 负责路由到实际平台）
    message_info = {
        "platform": "AstrBot",  # 统一平台名称，由 AstrBot 适配器处理
        "message_id": message_obj.message_id,
        "time": message_obj.timestamp or time.time(),
        "group_info": group_info,
        "user_info": user_info,
        "template_info": None,  # 暂不支持自定义模板
    }

    # 5. 构建完整的 message_data（字典格式，MaiBot 会自己转换为 Seg）
    message_data = {
        "message_info": message_info,
        "message_segment": message_segment,  # 字典格式，不是 Seg 对象
        "raw_message": message_obj.message_str or "",
    }

    return message_data


def _convert_component_to_seg(component) -> Dict[str, Any] | None:
    """
    将 AstrBot 的消息组件转换为 MaiBot 的消息段（Seg）

    Args:
        component: AstrBot 消息组件对象

    Returns:
        Dict | None: MaiBot 消息段字典，如果无法转换则返回 None
    """
    comp_type = component.type

    # 纯文本
    if comp_type == ComponentType.Plain:
        return {"type": "text", "data": component.text}

    # 图片
    elif comp_type == ComponentType.Image:
        # MaiBot 期望图片 URL 或 base64
        image_data = {}
        if hasattr(component, "url") and component.url:
            image_data["url"] = component.url
        elif hasattr(component, "file") and component.file:
            image_data["file"] = component.file
        elif hasattr(component, "base64") and component.base64:
            image_data["base64"] = component.base64

        return {"type": "image", "data": image_data}

    # 语音
    elif comp_type == ComponentType.Record:
        voice_data = {}
        if hasattr(component, "url") and component.url:
            voice_data["url"] = component.url
        elif hasattr(component, "file") and component.file:
            voice_data["file"] = component.file

        return {"type": "voice", "data": voice_data}

    # 视频
    elif comp_type == ComponentType.Video:
        video_data = {}
        if hasattr(component, "url") and component.url:
            video_data["url"] = component.url
        elif hasattr(component, "file") and component.file:
            video_data["file"] = component.file

        return {"type": "video", "data": video_data}

    # QQ 表情
    elif comp_type == ComponentType.Face:
        return {"type": "face", "data": {"id": component.id}}

    # 微信表情
    elif comp_type == ComponentType.WechatEmoji:
        # 将微信表情转换为 emoji 类型
        return {"type": "emoji", "data": {"md5": component.md5}}

    # @某人
    elif comp_type == ComponentType.At:
        # MaiBot 中 @ 表示为 mention
        return {"type": "mention", "data": {"user_id": component.qq}}

    # @全体成员
    elif comp_type == ComponentType.AtAll:
        return {"type": "mention_all", "data": {}}

    # 引用回复
    elif comp_type == ComponentType.Reply:
        return {
            "type": "reply",
            "data": {
                "message_id": component.id,
                "sender_id": getattr(component, "sender_id", ""),
            },
        }

    # 文件
    elif comp_type == ComponentType.File:
        file_data = {}
        if hasattr(component, "url") and component.url:
            file_data["url"] = component.url
        elif hasattr(component, "file") and component.file:
            file_data["file"] = component.file

        return {"type": "file", "data": file_data}

    # 其他未识别的类型，转为纯文本
    else:
        return {"type": "text", "data": f"[不支持的消息类型: {comp_type.name}]"}
