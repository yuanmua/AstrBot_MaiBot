"""
MaiBot集成模块
提供MaiBot的初始化和生命周期管理
"""

import asyncio
import os
from typing import Optional, Dict, Any

from astrbot.core.maibot.src.config.context import InstanceContext, set_context, get_context
from astrbot.core.maibot.src.common.logger import get_logger

logger = get_logger("maibot_init")


class MaiBotCore:
    """MaiBot核心管理类

    支持外部传入配置参数，实现独立启动
    """

    def __init__(
        self,
        instance_id: str = "default",
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化MaiBot核心

        Args:
            instance_id: 实例ID
            config: 可选的配置字典，包含以下字段:
                - data_root: 数据根目录
                - host: 服务监听地址
                - port: 服务端口
                - web_host: WebUI监听地址
                - web_port: WebUI端口
                - enable_webui: 是否启用WebUI
                - enable_socket: 是否启用Socket
        """
        self.instance_id = instance_id
        self.config = config or {}
        self.main_system = None
        self.initialized = False
        self._schedule_task = None

    def _get_config_value(self, key: str, default: Any = None) -> Any:
        """从配置字典获取值，优先使用传入的配置"""
        return self.config.get(key, default)

    async def initialize(self, data_root: Optional[str] = None):
        """
        初始化MaiBot

        Args:
            data_root: 数据根目录，例如 'data/maibot'
                       如果在构造函数中传入 config，则此参数可省略

        Raises:
            SystemExit: 当配置文件不存在时，MaiBot 内部会调用 sys.exit(0)，
                        此异常会传播到调用方处理
        """
        if self.initialized:
            logger.warning("MaiBot已经初始化过了")
            return

        logger.info(f"正在初始化 MaiBot (实例: {self.instance_id})...")

        # 1. 确定数据目录

        # 优先使用传入的 config.data_root，其次使用参数，最后使用默认值
        data_root = self._get_config_value("data_root", data_root) or os.path.join(
            "data", "maibot"
        )
        os.makedirs(data_root, exist_ok=True)

        # 设置实例日志系统
        # set_instance_id(self.instance_id)

        # 2. 从配置中获取端口等参数
        host = self._get_config_value("host", "127.0.0.1")
        port = self._get_config_value("port", 8000)
        web_host = self._get_config_value("web_host", "127.0.0.1")
        web_port = self._get_config_value("web_port", 8001)
        enable_webui = self._get_config_value("enable_webui", False)
        enable_socket = self._get_config_value("enable_socket", False)

        # 3. 创建并设置实例上下文（所有配置通过 context 管理）
        context = InstanceContext(
            data_root=data_root,
            instance_id=self.instance_id,
            host=host,
            port=port,
            web_host=web_host,
            web_port=web_port,
            enable_webui=enable_webui,
            enable_socket=enable_socket,
        )
        set_context(context)

        # 4. 设置 MaiBot 路径环境变量（用于 WebUI 静态文件）
        os.environ.setdefault("MAIBOT_PATH", context.get_maiabot_path())
        logger.info(f"MAIBOT_PATH: {context.get_maiabot_path()}")

        # 5. 初始化配置
        from astrbot.core.maibot.src.config.config import initialize_with_context

        initialize_with_context(context)

        # 6. 初始化数据库
        from astrbot.core.maibot.src.common.database.database import initialize_database

        initialize_database(context.get_database_path())
        logger.info(f"数据库已初始化: {context.get_database_path()}")

        # 7. 加载配置文件（可能抛出 SystemExit）
        from astrbot.core.maibot.src.config.config import load_configs

        load_configs(context)

        # 8. 创建 MainSystem 实例
        from astrbot.core.maibot.src.main import MainSystem

        logger.info("正在创建 MainSystem...")
        self.main_system = MainSystem()

        logger.info("正在初始化 MainSystem...")
        await self.main_system.initialize()
        logger.info("MainSystem 初始化完成")

        self.initialized = True
        logger.info("MaiBot 初始化完成")

    async def start(self):
        """启动MaiBot定时任务"""
        if not self.initialized:
            raise RuntimeError("必须先调用initialize()初始化MaiBot")

        logger.info("正在启动 MaiBot 定时任务...")

        # 启动定时任务（不等待，后台运行）
        self._schedule_task = asyncio.create_task(self.main_system.schedule_tasks())

        logger.info("MaiBot 定时任务启动完成")

    async def shutdown(self):
        """关闭MaiBot"""
        if not self.initialized:
            return

        logger.info(f"正在关闭 MaiBot (实例: {self.instance_id})...")

        # 取消定时任务
        if self._schedule_task:
            self._schedule_task.cancel()
            try:
                await self._schedule_task
            except asyncio.CancelledError:
                pass

        logger.info("MaiBot 已关闭")


# 全局单例
_maibot_core: Optional[MaiBotCore] = None


def get_maibot_core() -> MaiBotCore:
    """获取MaiBot核心实例"""
    global _maibot_core
    if _maibot_core is None:
        _maibot_core = MaiBotCore()
    return _maibot_core


async def create_maibot(
    instance_id: str = "default",
    data_root: str = "data/maibot",
    host: str = "127.0.0.1",
    port: int = 8000,
    web_host: str = "127.0.0.1",
    web_port: int = 8001,
    enable_webui: bool = False,
    enable_socket: bool = False,
) -> MaiBotCore:
    """
    创建并初始化独立的 MaiBot 实例

    这是一个便捷函数，可以直接启动一个独立的 MaiBot 实例

    Args:
        instance_id: 实例ID
        data_root: 数据根目录
        host: 服务监听地址
        port: 服务端口
        web_host: WebUI监听地址
        web_port: WebUI端口
        enable_webui: 是否启用WebUI
        enable_socket: 是否启用Socket

    Returns:
        初始化完成的 MaiBotCore 实例

    Example:
        ```python
        maibot = await create_maibot(
            instance_id="test",
            data_root="data/maibot",
            port=8002,
        )
        await maibot.start()
        ```
    """
    config = {
        "data_root": data_root,
        "host": host,
        "port": port,
        "web_host": web_host,
        "web_port": web_port,
        "enable_webui": enable_webui,
        "enable_socket": enable_socket,
    }

    maibot = MaiBotCore(instance_id=instance_id, config=config)
    await maibot.initialize()
    return maibot


__all__ = ["MaiBotCore", "get_maibot_core", "create_maibot"]
