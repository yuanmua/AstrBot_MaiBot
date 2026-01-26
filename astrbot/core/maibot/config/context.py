"""
实例上下文管理

通过 instance_id 动态推断路径，统一管理 MaiBot 的各种路径和配置。
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from astrbot.core.maibot.common.logger import get_logger

logger = get_logger("instance_context")


@dataclass
class InstanceContext:
    """
    MaiBot 实例上下文

    通过 instance_id 动态推断路径，避免使用全局变量和环境变量。

    目录结构:
        data_root/
        ├── config/                    # 公共配置目录
        │   ├── bot_config.toml
        │   ├── model_config.toml
        │   └── instances/             # 实例独立配置
        │       └── {instance_id}.toml
        └── instances/                 # 实例数据目录
            └── {instance_id}/
                ├── data/
                │   └── local_store.json
                ├── cache/
                └── logs/
    """

    data_root: str
    """数据根目录，例如 'data/maibot'"""

    instance_id: str
    """实例ID，用于推断实例目录"""

    # ===== 端口配置 =====
    host: str = "127.0.0.1"
    """服务监听地址"""

    port: int = 8000
    """服务端口"""

    web_host: str = "127.0.0.1"
    """WebUI 监听地址"""

    web_port: int = 8001
    """WebUI 端口"""

    enable_webui: bool = False
    """是否启用 WebUI 服务"""

    enable_socket: bool = False
    """是否启用 Socket 服务"""

    # WebUI 静态文件目录
    webui_dist_path: str = "D:\work\Bot\参考\MaiBot\webui\dist"
    """WebUI 静态文件目录路径，为空时自动计算"""

    # 缓存路径
    _project_root: Optional[str] = None
    _config_dir: Optional[str] = None
    _template_dir: Optional[str] = None

    # ===== 属性方法 =====
    @property
    def data_dir(self) -> str:
        """获取数据目录（兼容属性）"""
        return self.get_project_root()

    @property
    def maiabot_project_path(self) -> str:
        """获取 MaiBot 项目路径"""
        return os.path.normpath(
            os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                ),
                "MaiBot",
            )
        )

    # ===== 路径方法 =====
    def get_project_root(self) -> str:
        """获取项目根目录（数据根目录）"""
        if self._project_root is None:
            self._project_root = os.path.abspath(self.data_root)
        return self._project_root

    def get_config_dir(self) -> str:
        """获取公共配置目录（所有实例共享）"""
        if self._config_dir is None:
            self._config_dir = os.path.join(self.get_project_root(), "config")
            os.makedirs(self._config_dir, exist_ok=True)
        return self._config_dir

    def get_instance_config_path(self) -> str:
        """
        获取实例独立配置文件路径

        Returns:
            例如: data/maibot/config/instances/test_lifecycle.toml
        """
        return os.path.join(
            self.get_config_dir(), "instances", f"{self.instance_id}.toml"
        )

    def get_instance_data_dir(self) -> str:
        """
        获取实例数据目录

        Returns:
            例如: data/maibot/instances/test_lifecycle
        """
        return os.path.join(self.get_project_root(), "instances", self.instance_id)

    def get_instance_data_path(self, filename: str) -> str:
        """
        获取实例数据目录下文件的路径

        Args:
            filename: 文件名，例如 'local_store.json'

        Returns:
            例如: data/maibot/instances/test_lifecycle/data/local_store.json
        """
        data_dir = os.path.join(self.get_instance_data_dir(), "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, filename)

    def get_database_path(self) -> str:
        """
        获取数据库文件路径

        Returns:
            例如: data/maibot/instances/test_lifecycle/data/mai.db
        """
        return self.get_instance_data_path("mai.db")

    def get_local_store_path(self) -> str:
        """
        获取 local_store.json 文件路径

        Returns:
            例如: data/maibot/instances/test_lifecycle/data/local_store.json
        """
        return self.get_instance_data_path("local_store.json")

    def get_cache_dir(self) -> str:
        """获取缓存目录"""
        cache_dir = os.path.join(self.get_instance_data_dir(), "cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def get_logs_dir(self) -> str:
        """获取日志目录"""
        logs_dir = os.path.join(self.get_instance_data_dir(), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        return logs_dir

    def get_template_dir(self) -> str:
        """获取模板目录"""
        if self._template_dir is None:
            self._template_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "template")
            )
            os.makedirs(self._template_dir, exist_ok=True)
        return self._template_dir

    def get_model_config_path(self) -> str:
        """
        获取 model_config.toml 路径（公共配置）

        Returns:
            例如: data/maibot/config/model_config.toml
        """
        return os.path.join(self.get_project_root(), "config", "model_config.toml")

    def get_webui_config_path(self) -> str:
        """
        获取 webui.json 配置文件路径

        Returns:
            例如: data/maibot/instances/test_lifecycle/webui.json
        """
        return os.path.join(self.get_project_root(), "webui.json")

    def get_maiabot_path(self) -> str:
        """获取 MaiBot 项目路径"""
        return self.maiabot_project_path

    def get_webui_dist_path(self) -> str:
        """
        获取 WebUI 静态文件目录路径

        优先级:
        1. 显式配置的 webui_dist_path
        2. 自动计算: MaiBot/webui/dist
        """
        if self.webui_dist_path:
            return self.webui_dist_path
        return os.path.join(self.get_maiabot_path(), "webui", "dist")

    def log_info(self):
        """输出路径信息到日志"""
        logger.info(f"实例上下文 (instance_id={self.instance_id}):")
        logger.info(f"  data_root: {self.get_project_root()}")
        logger.info(f"  config_dir: {self.get_config_dir()}")
        logger.info(f"  instance_config: {self.get_instance_config_path()}")
        logger.info(f"  instance_data: {self.get_instance_data_dir()}")
        logger.info(f"  local_store: {self.get_local_store_path()}")
        logger.info(f"  端口配置: host={self.host}, port={self.port}")
        logger.info(
            f"  WebUI配置: host={self.web_host}, port={self.web_port}, enable={self.enable_webui}"
        )
        logger.info(f"  Socket配置: enable={self.enable_socket}")


# 全局上下文管理
_context: Optional[InstanceContext] = None


def get_context() -> InstanceContext:
    """获取全局实例上下文"""
    global _context
    if _context is None:
        raise RuntimeError("InstanceContext 未初始化，请先调用 set_context()")
    return _context


def set_context(context: InstanceContext) -> None:
    """设置全局实例上下文"""
    global _context
    _context = context
    _context.log_info()


def clear_context() -> None:
    """清除全局实例上下文"""
    global _context
    _context = None


__all__ = ["InstanceContext", "get_context", "set_context", "clear_context"]
