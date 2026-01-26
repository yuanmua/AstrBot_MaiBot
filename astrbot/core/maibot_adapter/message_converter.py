"""
AstrBot 消息 → MaiBot 消息格式转换器

支持多实例路由：
- platform 格式：astr:{instance_id}:{stream_id}
- chat_id 格式：{platform}:{user_id}:{type} (type = private/group)
"""

import hashlib
import time
from typing import Any, Dict, Optional

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


def _generate_stream_id(platform: str, user_id: str, group_id: Optional[str] = None) -> str:
    """生成聊天流唯一ID，与 MaiBot 的 ChatManager._generate_stream_id 保持一致"""
    if group_id:
        components = [platform, str(group_id)]
    else:
        components = [platform, str(user_id), "private"]
    key = "_".join(components)
    return hashlib.md5(key.encode()).hexdigest()


def _get_routing_instance_id(chat_id: str) -> str:
    """获取消息应该路由到的实例ID

    Args:
        chat_id: 聊天ID，格式：{platform}:{user_id}:{type}

    Returns:
        实例ID，如果没有配置路由则返回 "default"
    """
    try:
        from astrbot.core.maibot_adapter.platform_adapter import get_astrbot_adapter

        adapter = get_astrbot_adapter()
        if adapter and adapter.message_router:
            return adapter.message_router.route_message(chat_id)
    except Exception:
        pass

    return "default"


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

    # 2. 构建 user_info（使用真实平台）
    sender = message_obj.sender
    real_platform = event.platform_meta.name  # 真实平台名，如 lark
    user_info = {
        "platform": real_platform,  # 用户所在的真实平台
        "user_id": str(sender.user_id),
        "user_nickname": sender.nickname or "",
        "user_cardname": getattr(sender, "card", None) or "",  # 群昵称
    }

    # 3. 生成 stream_id（使用与 MaiBot 相同的算法）
    user_id = str(sender.user_id)
    group_id = str(message_obj.group.group_id) if message_obj.group else None
    stream_id = _generate_stream_id(real_platform, user_id, group_id)

    # 4. 转换消息段（message_segment）
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

    # 添加 chat_id 用于消息路由（格式：platform:user_id:type）
    # chat_id 必须在获取实例ID之前构建
    chat_id = f"{real_platform}:{user_id}"
    if group_id:
        chat_id += f":group"
    else:
        chat_id += ":private"

    # 5. 获取路由实例ID并构建平台标识
    # 使用 _get_routing_instance_id 从消息路由器获取实例ID
    instance_id = _get_routing_instance_id(chat_id)

    # 使用 stream_id 作为平台标识（以 "astr:" 前缀区分，便于识别这是 AstrBot 转发的消息）
    # 格式：astr:{instance_id}:{stream_id}
    astrbot_platform = f"astr:{instance_id}:{stream_id}"

    message_info = {
        "platform": astrbot_platform,  # 使用 {instance_id}:{stream_id} 格式
        "message_id": message_obj.message_id,
        "time": message_obj.timestamp or time.time(),
        "group_info": group_info,
        "user_info": user_info,
        "template_info": None,  # 暂不支持自定义模板
        "chat_id": chat_id,  # 用于消息路由的 chat_id
    }

    # 6. 构建完整的 message_data（字典格式，MaiBot 会自己转换为 Seg）
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
