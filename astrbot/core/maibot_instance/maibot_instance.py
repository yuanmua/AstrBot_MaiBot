"""
MaiBot 多实例启动管理器

通过实例ID启动和管理多个 MaiBot 实例
支持进程隔离，每个实例在独立子进程中运行
配置从 data/maibot/config/instances_meta.json 读取
数据存储到 data/maibot/instances/{instance_id}
"""

import asyncio
import json
import os
import shutil
import sys
import time
from datetime import datetime
from enum import Enum
from multiprocessing import Process, Queue
from typing import Optional, Dict, Any, List

# 确保项目根目录在路径中（Windows multiprocessing 需要）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from astrbot.core.maibot_instance.subprocess_entry import subprocess_main
from astrbot.core.maibot.common.logger import get_logger

logger = get_logger("maibot_instance")

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT = 30


class InstanceStatus(str, Enum):
    """实例状态枚举"""
    STOPPED = "stopped"           # 已停止
    STARTING = "starting"         # 启动中
    RUNNING = "running"           # 运行中
    STOPPING = "stopping"         # 停止中
    ERROR = "error"               # 错误状态
    RESTARTING = "restarting"     # 重启中


class MaibotInstance:
    """单个 MaiBot 实例（进程隔离模式）"""

    def __init__(
        self,
        instance_id: str,
        name: str,
        description: str = "",
        is_default: bool = False,
        lifecycle: Optional[Dict[str, Any]] = None,    # 生命周期配置
        host: str = "127.0.0.1",
        port: int = 8000,
        web_host: str = "127.0.0.1",
        web_port: int = 8001,
        enable_webui: bool = False,
        enable_socket: bool = False,
    ):
        self.instance_id = instance_id
        self.name = name
        self.description = description
        self.is_default = is_default
        # 生命周期配置
        self.lifecycle = lifecycle or {
            "start_order": 0,           # 启动顺序（数字小的先启动）
            "restart_on_crash": True,   # 崩溃后自动重启
            "max_restarts": 3,          # 最大重启次数
            "restart_delay": 5000,      # 重启延迟（毫秒）
        }
        self.host = host
        self.port = port
        self.web_host = web_host
        self.web_port = web_port
        self.enable_webui = enable_webui
        self.enable_socket = enable_socket

        self.status = InstanceStatus.STOPPED
        self.error_message = ""
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None

        # ===== 进程隔离相关字段 =====
        self.process: Optional[Process] = None
        """子进程对象"""
        self.input_queue: Optional[Queue] = None
        """命令输入队列（主进程 -> 子进程）"""
        self.output_queue: Optional[Queue] = None
        """状态输出队列（子进程 -> 主进程）"""
        self.last_heartbeat: Optional[datetime] = None
        """上次心跳时间"""
        self._status_monitor_task: Optional[asyncio.Task] = None
        """状态监控任务"""

    def get_data_dir(self, base_path: str) -> str:
        return os.path.join(base_path, "instances", self.instance_id)

    def get_config_path(self, base_path: str) -> str:
        return os.path.join(
            base_path, "config", "instances", f"{self.instance_id}.toml"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.instance_id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "lifecycle": self.lifecycle,
            "host": self.host,
            "port": self.port,
            "web_host": self.web_host,
            "web_port": self.web_port,
            "enable_webui": self.enable_webui,
            "enable_socket": self.enable_socket,
            "status": self.status.value
            if hasattr(self.status, "value")
            else str(self.status),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


class MaibotInstanceManager:
    """MaiBot 多实例管理器"""

    def __init__(self, data_root: str = "data/maibot"):
        self.data_root = data_root
        self.instances: Dict[str, MaibotInstance] = {}
        self.metadata_path = os.path.join(data_root, "config", "instances_meta.json")

    async def initialize(self) -> None:
        """初始化实例管理器"""
        os.makedirs(os.path.join(self.data_root, "config", "instances"), exist_ok=True)
        os.makedirs(os.path.join(self.data_root, "instances"), exist_ok=True)

        await self._load_instances_metadata()

        if "default" not in self.instances:
            logger.info("默认实例不存在，正在创建...")
            await self.create_instance("default", "默认麦麦", is_default=True)

        logger.info(f"实例管理器初始化完成，共 {len(self.instances)} 个实例")

    async def _load_instances_metadata(self) -> None:
        """加载实例元数据"""
        if not os.path.exists(self.metadata_path):
            logger.info("未找到实例元数据文件")
            return

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        for instance_data in metadata.get("instances", []):
            instance = MaibotInstance(
                instance_id=instance_data["id"],
                name=instance_data["name"],
                description=instance_data.get("description", ""),
                is_default=instance_data.get("is_default", False),
                lifecycle=instance_data.get("lifecycle"),
                host=instance_data.get("host", "127.0.0.1"),
                port=instance_data.get("port", 8000),
                web_host=instance_data.get("web_host", "127.0.0.1"),
                web_port=instance_data.get("web_port", 8001),
                enable_webui=instance_data.get("enable_webui", False),
                enable_socket=instance_data.get("enable_socket", False),
            )
            if instance_data.get("created_at"):
                instance.created_at = datetime.fromisoformat(
                    instance_data["created_at"]
                )
            if instance_data.get("updated_at"):
                instance.updated_at = datetime.fromisoformat(
                    instance_data["updated_at"]
                )
            self.instances[instance.instance_id] = instance

        logger.info(f"已加载 {len(self.instances)} 个实例")

    async def _save_instances_metadata(self) -> None:
        """保存实例元数据"""
        instances_data = [
            {
                "id": inst.instance_id,
                "name": inst.name,
                "description": inst.description,
                "is_default": inst.is_default,
                "lifecycle": inst.lifecycle,
                "host": inst.host,
                "port": inst.port,
                "web_host": inst.web_host,
                "web_port": inst.web_port,
                "enable_webui": inst.enable_webui,
                "enable_socket": inst.enable_socket,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
                "updated_at": inst.updated_at.isoformat() if inst.updated_at else None,
            }
            for inst in self.instances.values()
        ]

        metadata = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "instances": instances_data,
        }

        os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    async def create_instance(
        self,
        instance_id: str,
        name: str,
        description: str = "",
        is_default: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
        web_host: str = "127.0.0.1",
        web_port: int = 8001,
        enable_webui: bool = False,
        enable_socket: bool = False,
    ) -> MaibotInstance:
        """创建新实例"""
        if instance_id in self.instances:
            raise ValueError(f"实例ID已存在: {instance_id}")

        instance = MaibotInstance(
            instance_id=instance_id,
            name=name,
            description=description,
            is_default=is_default,
            host=host,
            port=port,
            web_host=web_host,
            web_port=web_port,
            enable_webui=enable_webui,
            enable_socket=enable_socket,
        )

        instance_dir = instance.get_data_dir(self.data_root)
        os.makedirs(os.path.join(instance_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(instance_dir, "cache"), exist_ok=True)

        instance.created_at = datetime.now()

        template_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "maibot",
            "template",
            "bot_config_template.toml",
        )
        config_path = instance.get_config_path(self.data_root)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        if os.path.exists(template_path):
            shutil.copy2(template_path, config_path)
            logger.info(f"已从模板创建实例 {instance_id} 配置文件")
        else:
            logger.warning(f"未找到配置模板: {template_path}")

        self.instances[instance_id] = instance
        await self._save_instances_metadata()

        logger.info(f"实例 {instance_id} 创建成功")
        return instance

    async def start_instance(self, instance_id: str) -> bool:
        """启动指定实例（进程隔离模式）

        通过创建子进程运行 MaiBotCore，实现进程隔离
        """
        if instance_id not in self.instances:
            logger.error(f"实例不存在: {instance_id}")
            return False

        instance = self.instances[instance_id]

        if instance.status == InstanceStatus.RUNNING:
            logger.warning(f"实例 {instance_id} 已在运行")
            return True

        try:
            instance.status = InstanceStatus.STARTING
            instance.error_message = ""

            # 1. 检查配置文件是否存在
            config_path = instance.get_config_path(self.data_root)
            if not os.path.exists(config_path):
                instance.status = InstanceStatus.STOPPED
                instance.error_message = "配置文件不存在，请先配置实例"
                logger.warning(f"实例 {instance_id} 配置文件不存在: {config_path}")
                return False

            # 2. 创建进程间通信队列
            instance.input_queue = Queue()
            instance.output_queue = Queue()

            # 3. 构建配置字典
            data_root = self.data_root
            config = {
                "data_root": data_root,
                "host": instance.host,
                "port": instance.port,
                "web_host": instance.web_host,
                "web_port": instance.web_port,
                "enable_webui": instance.enable_webui,
                "enable_socket": instance.enable_socket,
            }

            # 4. 创建并启动子进程
            logger.info(f"正在启动实例 {instance_id} 的子进程...")
            instance.process = Process(
                target=subprocess_main,
                args=(
                    instance_id,
                    data_root,
                    config,
                    instance.input_queue,
                    instance.output_queue,
                ),
                name=f"MaiBot-{instance_id}",
            )
            instance.process.start()
            logger.info(f"子进程已启动，PID: {instance.process.pid}")

            # 5. 等待子进程初始化并接收初始状态
            init_timeout = 30  # 初始化超时时间（秒）
            start_time = time.time()

            while time.time() - start_time < init_timeout:
                if instance.output_queue.empty():
                    await asyncio.sleep(0.1)
                    continue

                try:
                    msg = instance.output_queue.get(timeout=1.0)
                    msg_type = msg.get("type", "")
                    payload = msg.get("payload", {})

                    if msg_type == "status":
                        status = payload.get("status", "")
                        message = payload.get("message", "")
                        error = payload.get("error", "")

                        if status == "running":
                            # 初始化成功
                            instance.status = InstanceStatus.RUNNING
                            instance.started_at = datetime.now()
                            instance.last_heartbeat = datetime.now()
                            logger.info(f"实例 {instance_id} 启动成功，状态: {message}")
                            # 启动状态监控任务
                            instance._status_monitor_task = asyncio.create_task(
                                self._monitor_instance_status(instance)
                            )
                            return True
                        elif status == "error":
                            instance.status = InstanceStatus.ERROR
                            instance.error_message = error or message
                            logger.error(f"实例 {instance_id} 启动失败: {error or message}")
                            self._cleanup_instance(instance)
                            return False
                        elif status == "config_needed":
                            instance.status = InstanceStatus.STOPPED
                            instance.error_message = "配置已创建，请填写后重新启动"
                            logger.info(f"实例 {instance_id} 配置已创建，请填写后重新启动")
                            self._cleanup_instance(instance)
                            return True
                        else:
                            logger.info(f"实例 {instance_id} 状态: {status} - {message}")
                            if status == "initializing":
                                # 正在初始化，继续等待
                                instance.status = InstanceStatus.STARTING
                                continue
                    elif msg_type == "log":
                        # 转发日志
                        level = payload.get("level", "info")
                        msg_text = payload.get("message", "")
                        if level == "error":
                            logger.error(f"[{instance_id}] {msg_text}")
                        elif level == "warning":
                            logger.warning(f"[{instance_id}] {msg_text}")
                        else:
                            logger.info(f"[{instance_id}] {msg_text}")

                except Exception as e:
                    logger.warning(f"解析子进程消息时出错: {e}")
                    continue

            # 超时
            instance.status = InstanceStatus.ERROR
            instance.error_message = "启动超时"
            logger.error(f"实例 {instance_id} 启动超时")
            self._cleanup_instance(instance)
            return False

        except Exception as e:
            instance.status = InstanceStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"实例 {instance_id} 启动失败: {e}", exc_info=True)
            self._cleanup_instance(instance)
            return False

    def _cleanup_instance(self, instance: MaibotInstance) -> None:
        """清理实例资源（进程、队列等）"""
        if instance.process and instance.process.is_alive():
            instance.process.terminate()
            instance.process.join(timeout=5)
            if instance.process.is_alive():
                instance.process.kill()
            logger.info(f"已终止实例 {instance.instance_id} 的子进程")

        if instance.input_queue:
            try:
                while not instance.input_queue.empty():
                    instance.input_queue.get_nowait()
            except Exception:
                pass

        if instance.output_queue:
            try:
                while not instance.output_queue.empty():
                    instance.output_queue.get_nowait()
            except Exception:
                pass

        if instance._status_monitor_task:
            instance._status_monitor_task.cancel()
            try:
                # 不需要 await，因为任务可能在另一个事件循环中运行
                pass
            except Exception:
                pass

        instance.process = None
        instance.input_queue = None
        instance.output_queue = None
        instance._status_monitor_task = None

    async def _monitor_instance_status(self, instance: MaibotInstance) -> None:
        """监控实例状态（后台任务）

        定期检查子进程状态，接收心跳和日志，支持崩溃自动重启
        """
        instance_id = instance.instance_id
        restart_count = 0  # 重启计数
        max_restarts = instance.lifecycle.get("max_restarts", 3)

        while instance.status == InstanceStatus.RUNNING:
            try:
                # 发送心跳检测
                if instance.input_queue:
                    try:
                        instance.input_queue.put_nowait({"type": "ping"})
                    except Exception:
                        pass

                # 检查子进程是否还在运行
                if instance.process and not instance.process.is_alive():
                    exit_code = instance.process.exitcode
                    logger.warning(
                        f"实例 {instance_id} 子进程已退出，退出码: {exit_code}"
                    )

                    # 检查是否需要自动重启
                    if instance.lifecycle.get("restart_on_crash", True):
                        if restart_count < max_restarts:
                            restart_count += 1
                            delay = instance.lifecycle.get("restart_delay", 5000) / 1000
                            logger.info(
                                f"实例 {instance_id} 等待 {delay}s 后自动重启 ({restart_count}/{max_restarts})"
                            )
                            await asyncio.sleep(delay)

                            # 清理资源
                            self._cleanup_instance(instance)

                            # 重启
                            instance.status = InstanceStatus.RESTARTING
                            await self.start_instance(instance_id)
                            # 重置重启计数，让监控继续
                            restart_count = 0
                            continue
                        else:
                            # 超过最大重启次数
                            logger.error(
                                f"实例 {instance_id} 崩溃重启次数超限 ({restart_count}/{max_restarts})"
                            )

                    instance.status = InstanceStatus.ERROR
                    instance.error_message = f"子进程异常退出，退出码: {exit_code}"
                    instance.started_at = None
                    self._cleanup_instance(instance)
                    break

                # 读取输出队列中的消息
                if instance.output_queue:
                    while not instance.output_queue.empty():
                        try:
                            msg = instance.output_queue.get_nowait()
                            msg_type = msg.get("type", "")
                            payload = msg.get("payload", {})

                            if msg_type == "pong":
                                # 心跳响应
                                instance.last_heartbeat = datetime.now()
                            elif msg_type == "status":
                                status = payload.get("status", "")
                                if status == "stopped":
                                    logger.info(f"实例 {instance_id} 已停止")
                                    instance.status = InstanceStatus.STOPPED
                                    instance.started_at = None
                                    self._cleanup_instance(instance)
                                    break
                            elif msg_type == "log":
                                level = payload.get("level", "info")
                                msg_text = payload.get("message", "")
                                if level == "error":
                                    logger.error(f"[{instance_id}] {msg_text}")
                                elif level == "warning":
                                    logger.warning(f"[{instance_id}] {msg_text}")
                                else:
                                    logger.info(f"[{instance_id}] {msg_text}")
                            elif msg_type == "signal":
                                signum = payload.get("signal", "")
                                logger.info(f"实例 {instance_id} 收到信号: {signum}")
                            elif msg_type == "message_reply":
                                # 处理子进程返回的回复消息
                                stream_id = payload.get("stream_id", "")
                                reply = payload.get("reply", {})
                                logger.info(f"[{instance_id}] 收到回复: stream_id={stream_id[:16] if stream_id else 'unknown'}...")
                                # 将回复传递给 AstrBot 适配器发送
                                await self._handle_instance_reply(instance_id, stream_id, reply)
                        except Exception:
                            break

                # 检查心跳超时
                if instance.last_heartbeat:
                    elapsed = (datetime.now() - instance.last_heartbeat).total_seconds()
                    if elapsed > HEARTBEAT_TIMEOUT:
                        logger.warning(
                            f"实例 {instance_id} 心跳超时 ({elapsed:.1f}s)，尝试重启..."
                        )
                        instance.status = InstanceStatus.RESTARTING
                        await self.restart_instance(instance_id)
                        break

                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                logger.info(f"实例 {instance_id} 状态监控任务已取消")
                break
            except Exception as e:
                logger.error(f"监控实例 {instance_id} 状态时出错: {e}")
                await asyncio.sleep(5.0)

    async def _handle_instance_reply(
        self, instance_id: str, stream_id: str, reply: Dict[str, Any]
    ) -> None:
        """处理子进程返回的回复消息

        通过 AstrBot 适配器将回复发送给原始平台

        Args:
            instance_id: 实例ID
            stream_id: 流ID
            reply: 回复数据 {
                "message_info": {...},
                "message_chain": dict,  # 字典格式的 MessageChain
                "processed_plain_text": str
            }
        """
        try:
            from astrbot.core.maibot_adapter.platform_adapter import get_astrbot_adapter
            from astrbot.core.message.message_event_result import MessageChain
            from astrbot.core.message.components import (
                Plain,
                Image,
                Record,
                Video,
                Face,
                File,
            )

            adapter = get_astrbot_adapter()

            # 获取原始事件
            event = adapter.get_event(stream_id)
            if not event:
                logger.warning(
                    f"[{instance_id}] 未找到 stream_id={stream_id[:16] if stream_id else 'unknown'} 对应的事件"
                )
                return

            # 从字典重建 MessageChain
            message_chain_data = reply.get("message_chain", {})
            if message_chain_data:
                chain_data = message_chain_data.get("chain", [])

                # 从字典列表重建组件
                components = []
                for comp_dict in chain_data:
                    comp_type = comp_dict.get("type", "").lower()
                    comp_data = comp_dict.get("data", {})

                    if comp_type == "text" or comp_type == "plain":
                        components.append(Plain(comp_data.get("text", "")))
                    elif comp_type == "image":
                        # Image 可能有多种来源：url, base64, file
                        if "base64" in comp_data:
                            components.append(Image(base64=comp_data["base64"]))
                        elif "url" in comp_data:
                            components.append(Image(url=comp_data["url"]))
                        elif "file" in comp_data:
                            components.append(Image(file=comp_data["file"]))
                    elif comp_type == "voice" or comp_type == "record":
                        if "url" in comp_data:
                            components.append(Record(url=comp_data["url"]))
                        elif "file" in comp_data:
                            components.append(Record(file=comp_data["file"]))
                    elif comp_type == "video":
                        if "url" in comp_data:
                            components.append(Video(url=comp_data["url"]))
                        elif "file" in comp_data:
                            components.append(Video(file=comp_data["file"]))
                    elif comp_type == "face":
                        face_id = comp_data.get("id", 0)
                        components.append(Face(id=face_id))
                    elif comp_type == "file":
                        if "url" in comp_data:
                            components.append(File(url=comp_data["url"]))
                        elif "file" in comp_data:
                            components.append(File(file=comp_data["file"]))
                    else:
                        # 未知类型，尝试创建 Plain
                        components.append(Plain(f"[未知类型: {comp_type}]"))

                # 创建 MessageChain
                message_chain = MessageChain(
                    chain=components,
                    use_t2i_=message_chain_data.get("use_t2i_"),
                )

                # 发送消息
                await event.send(message_chain)
                logger.info(
                    f"[{instance_id}] 回复已发送: stream_id={stream_id[:16] if stream_id else 'unknown'}, 内容: {reply.get('processed_plain_text', '')[:50]}"
                )
            else:
                logger.warning(
                    f"[{instance_id}] 回复中没有 message_chain: stream_id={stream_id[:16] if stream_id else 'unknown'}"
                )

            # 清理事件
            adapter.remove_event(stream_id)

        except Exception as e:
            logger.error(f"[{instance_id}] 处理子进程回复失败: {e}", exc_info=True)

    async def restart_instance(self, instance_id: str) -> bool:
        """重启指定实例"""
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]

        logger.info(f"正在重启实例 {instance_id}...")

        # 停止实例
        stopped = await self.stop_instance(instance_id)
        if not stopped:
            logger.error(f"停止实例 {instance_id} 失败，无法重启")
            return False

        # 等待一段时间
        await asyncio.sleep(1.0)

        # 启动实例
        return await self.start_instance(instance_id)

    async def stop_instance(self, instance_id: str) -> bool:
        """停止指定实例（进程隔离模式）

        通过发送停止命令给子进程来停止实例
        """
        if instance_id not in self.instances:
            return False

        instance = self.instances[instance_id]

        if instance.status == InstanceStatus.STOPPED:
            return True

        try:
            instance.status = InstanceStatus.STOPPING

            # 取消状态监控任务
            if instance._status_monitor_task:
                instance._status_monitor_task.cancel()
                instance._status_monitor_task = None

            # 发送停止命令给子进程
            if instance.input_queue:
                try:
                    instance.input_queue.put_nowait({"type": "stop"})
                    logger.info(f"已向实例 {instance_id} 发送停止命令")
                except Exception as e:
                    logger.warning(f"发送停止命令失败: {e}")

            # 等待子进程退出
            if instance.process and instance.process.is_alive():
                instance.process.join(timeout=10)
                if instance.process.is_alive():
                    logger.warning(f"子进程未响应终止信号，强制终止...")
                    instance.process.terminate()
                    instance.process.join(timeout=5)
                    if instance.process.is_alive():
                        instance.process.kill()

            # 清理资源
            self._cleanup_instance(instance)

            instance.status = InstanceStatus.STOPPED
            instance.started_at = None

            logger.info(f"实例 {instance_id} 已停止")
            return True

        except Exception as e:
            instance.status = InstanceStatus.ERROR
            instance.error_message = str(e)
            logger.error(f"停止实例 {instance_id} 失败: {e}")
            return False

    def get_instance(self, instance_id: str) -> Optional[MaibotInstance]:
        return self.instances.get(instance_id)

    def get_all_instances(self) -> List[MaibotInstance]:
        return list(self.instances.values())

    def get_running_instances(self) -> List[MaibotInstance]:
        return [
            inst
            for inst in self.instances.values()
            if inst.status == InstanceStatus.RUNNING
        ]

    def is_configured(self, instance_id: str) -> bool:
        """检查实例配置是否已就绪"""
        if instance_id not in self.instances:
            return False
        instance = self.instances[instance_id]
        config_path = instance.get_config_path(self.data_root)
        return os.path.exists(config_path)

    async def send_message(
        self,
        instance_id: str,
        message_data: Dict[str, Any],
        stream_id: str,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """发送消息给指定实例（IPC 模式）

        通过进程间队列直接发送消息给子进程，避免 TCP 通信

        Args:
            instance_id: 实例ID
            message_data: MaiBot 格式的消息数据
            stream_id: 流ID，用于追踪
            timeout: 超时时间（秒）

        Returns:
            Dict[str, Any]: 处理结果 {
                "success": bool,
                "result": {
                    "status": "replied" | "processed",
                    "reply": {...}  # 如果有回复
                },
                "error": str
            }

        Raises:
            ValueError: 实例不存在或未运行
        """
        if instance_id not in self.instances:
            raise ValueError(f"实例不存在: {instance_id}")

        instance = self.instances[instance_id]

        if instance.status != InstanceStatus.RUNNING:
            raise ValueError(f"实例 {instance_id} 未运行，当前状态: {instance.status.value}")

        if not instance.input_queue:
            raise ValueError(f"实例 {instance_id} 未初始化消息队列")

        # 发送消息到子进程
        cmd = {
            "type": "message",
            "payload": {
                "message_data": message_data,
                "stream_id": stream_id,
            }
        }

        try:
            instance.input_queue.put_nowait(cmd)
            logger.debug(f"消息已发送到实例 {instance_id}: stream_id={stream_id[:16]}...")
        except Exception as e:
            logger.error(f"发送消息到实例 {instance_id} 失败: {e}")
            return {"success": False, "error": str(e)}

        # 等待处理结果（包括回复）
        start_time = time.time()
        reply_result = None
        last_status_time = start_time

        while time.time() - start_time < timeout:
            try:
                # 检查 output_queue 是否有结果
                if instance.output_queue.empty():
                    await asyncio.sleep(0.05)
                    continue

                msg = instance.output_queue.get(timeout=1.0)
                msg_type = msg.get("type", "")

                if msg_type == "message_result":
                    payload = msg.get("payload", {})
                    success = payload.get("success", False)
                    result = payload.get("result")
                    error = payload.get("error", "")
                    logger.debug(f"实例 {instance_id} 消息处理结果: success={success}")
                    return {"success": success, "result": result, "error": error}
                else:
                    # 不是消息结果，继续处理其他类型的消息
                    continue

            except multiprocessing.queues.Empty:
                continue
            except Exception as e:
                logger.error(f"获取消息处理结果时出错: {e}")
                return {"success": False, "error": str(e)}

        logger.warning(f"等待实例 {instance_id} 消息处理结果超时")
        return {"success": False, "error": "处理超时"}


_instance_manager: Optional[MaibotInstanceManager] = None


async def initialize_instance_manager(
    data_root: str = "data/maibot",
) -> MaibotInstanceManager:
    """初始化全局实例管理器"""
    global _instance_manager
    _instance_manager = MaibotInstanceManager(data_root)
    await _instance_manager.initialize()
    return _instance_manager


def get_instance_manager() -> Optional[MaibotInstanceManager]:
    """获取全局实例管理器"""
    return _instance_manager


async def start_maibot(instance_id: str) -> bool:
    """通过实例ID启动 MaiBot 实例"""
    manager = get_instance_manager()
    if manager is None:
        manager = await initialize_instance_manager()
    return await manager.start_instance(instance_id)


async def stop_maibot(instance_id: str) -> bool:
    """停止指定的 MaiBot 实例"""
    manager = get_instance_manager()
    if manager is None:
        return False
    return await manager.stop_instance(instance_id)


def list_instances() -> List[Dict[str, Any]]:
    """列出所有实例"""
    manager = get_instance_manager()
    if manager is None:
        return []
    return [inst.to_dict() for inst in manager.get_all_instances()]


def get_instance_status(instance_id: str) -> Optional[Dict[str, Any]]:
    """获取实例状态"""
    manager = get_instance_manager()
    if manager is None:
        return None
    instance = manager.get_instance(instance_id)
    if instance:
        return instance.to_dict()
    return None


async def send_message_to_instance(
    instance_id: str,
    message_data: Dict[str, Any],
    stream_id: str,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    """便捷函数：发送消息给指定实例（IPC 模式）"""
    manager = get_instance_manager()
    if manager is None:
        return {"success": False, "error": "实例管理器未初始化"}
    return await manager.send_message(instance_id, message_data, stream_id, timeout)


__all__ = [
    "MaibotInstanceManager",
    "MaibotInstance",
    "initialize_instance_manager",
    "get_instance_manager",
    "start_maibot",
    "stop_maibot",
    "list_instances",
    "get_instance_status",
    "send_message_to_instance",
]
