"""
配置模块

提供 MaiBot 的配置管理功能。
"""

from .context import InstanceContext, get_context, set_context, clear_context
from .config import (
    Config,
    APIAdapterConfig,
    load_config,
    api_ada_load_config,
    load_configs,
    initialize_with_context,
    MMC_VERSION,
)

__all__ = [
    "InstanceContext",
    "get_context",
    "set_context",
    "clear_context",
    "Config",
    "APIAdapterConfig",
    "load_config",
    "api_ada_load_config",
    "load_configs",
    "initialize_with_context",
    "MMC_VERSION",
]
