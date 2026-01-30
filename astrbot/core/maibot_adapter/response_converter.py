"""
MaiBot 响应 → AstrBot 消息链转换器
"""

from typing import List

from maim_message import Seg

from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.message.components import (
    Plain,
    Image,
    Record,
    Video,
    Face,
    File,
    Reply,
)


def convert_maibot_to_astrbot(message_segment: Seg) -> MessageChain:
    """
    将 MaiBot 的消息段（Seg）转换为 AstrBot 的 MessageChain

    Args:
        message_segment: MaiBot 的消息段对象（Seg）

    Returns:
        MessageChain: AstrBot 消息链对象
    """
    components = []

    # 解析 MaiBot 的消息段
    segments = _parse_seg(message_segment)

    for seg in segments:
        component = _convert_seg_to_component(seg)
        if component:
            components.append(component)

    # 如果没有任何组件，添加一个空文本
    if not components:
        components.append(Plain(""))

    return MessageChain(components)


def _parse_seg(segment: Seg) -> List[dict]:
    """
    递归解析 Seg 对象，提取所有消息段

    Args:
        segment: Seg 对象

    Returns:
        List[dict]: 消息段列表，每个元素为 {"type": "...", "data": ...}
    """
    result = []

    if segment is None:
        return result

    # 如果是消息段列表
    if segment.type == "seglist":
        if segment.data:
            for seg in segment.data:
                result.extend(_parse_seg(seg))

    # 如果是转发消息
    elif segment.type == "forward":
        # 转发消息暂时转换为纯文本提示
        result.append({"type": "text", "data": "[合并转发消息]"})

    # 其他单个消息段
    else:
        result.append({"type": segment.type, "data": segment.data})

    return result


def _convert_seg_to_component(seg: dict):
    """
    将单个消息段字典转换为 AstrBot 消息组件

    Args:
        seg: 消息段字典 {"type": "...", "data": ...}

    Returns:
        消息组件对象或 None
    """
    print("正在消化消息到AstrBot:",seg)
    seg_type = seg.get("type")
    seg_data = seg.get("data")

    # 纯文本
    if seg_type == "text":
        return Plain(seg_data) if seg_data else None

    # 图片
    elif seg_type == "image":
        if isinstance(seg_data, str):
            # base64 或 URL
            if seg_data.startswith("data:image"):
                # base64 格式
                base64_data = seg_data.split(",", 1)[1] if "," in seg_data else seg_data
                return Image(base64=base64_data)
            else:
                # URL 格式
                return Image(url=seg_data)
        elif isinstance(seg_data, dict):
            # 字典格式
            if "base64" in seg_data:
                return Image(base64=seg_data["base64"])
            elif "url" in seg_data:
                return Image(url=seg_data["url"])
            elif "file" in seg_data:
                return Image(file=seg_data["file"])

    # 图片 URL（imageurl）
    elif seg_type == "imageurl":
        return Image(url=seg_data) if seg_data else None

    # 表情包（emoji）
    elif seg_type == "emoji":
        if isinstance(seg_data, str):
            # base64 格式
            if seg_data.startswith("data:image"):
                base64_data = seg_data.split(",", 1)[1] if "," in seg_data else seg_data
                return Image(base64=base64_data)
            else:
                return Image(url=seg_data)

    # 语音
    elif seg_type == "voice":
        if isinstance(seg_data, str):
            # base64 或 URL
            if seg_data.startswith("data:audio"):
                # base64 格式（暂不支持，转为文本提示）
                return Plain("[语音消息]")
            else:
                # URL 格式
                return Record(url=seg_data)
        elif isinstance(seg_data, dict):
            if "url" in seg_data:
                return Record(url=seg_data["url"])
            elif "file" in seg_data:
                return Record(file=seg_data["file"])

    # 语音 URL（voiceurl）
    elif seg_type == "voiceurl":
        return Record(url=seg_data) if seg_data else None

    # 视频
    elif seg_type == "video":
        if isinstance(seg_data, str):
            if seg_data.startswith("data:video"):
                return Plain("[视频消息]")
            else:
                return Video(url=seg_data)
        elif isinstance(seg_data, dict):
            if "url" in seg_data:
                return Video(url=seg_data["url"])
            elif "file" in seg_data:
                return Video(file=seg_data["file"])

    # 视频 URL（videourl）
    elif seg_type == "videourl":
        return Video(url=seg_data) if seg_data else None

    # QQ 表情
    elif seg_type == "face":
        if isinstance(seg_data, dict) and "id" in seg_data:
            return Face(id=seg_data["id"])
        elif isinstance(seg_data, int):
            return Face(id=seg_data)

    # 文件
    elif seg_type == "file":
        if isinstance(seg_data, dict):
            if "url" in seg_data:
                return File(url=seg_data["url"])
            elif "file" in seg_data:
                return File(file=seg_data["file"])

    # 回复消息 (reply)
    elif seg_type == "reply":
        if isinstance(seg_data, dict):
            # 提取 reply 消息段的各项数据
            reply_id = seg_data.get("id")
            # 被引用的消息内容可能直接提供，也可能在 content 字段
            reply_content = seg_data.get("content")
            # 发送者信息
            sender = seg_data.get("sender", {})
            sender_id = sender.get("user_id") if isinstance(sender, dict) else None
            sender_nickname = sender.get("nickname") if isinstance(sender, dict) else None
            # 消息字符串（用于显示）
            message_str = ""
            if reply_content:
                # 如果有内容，解析为纯文本
                if isinstance(reply_content, list):
                    for item in reply_content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            message_str += item.get("data", "")
                elif isinstance(reply_content, str):
                    message_str = reply_content

            return Reply(
                id=reply_id,
                sender_id=sender_id,
                sender_nickname=sender_nickname,
                message_str=message_str,
            )
        elif isinstance(seg_data, (int, str)):
            # 简单格式：只有消息 ID
            return Reply(id=seg_data)

    # 其他未识别的类型
    else:
        return Plain(f"[消息链转换器-不支持的消息类型: {seg_type}]")

    return None
