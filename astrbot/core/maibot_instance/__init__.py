"""
麦麦多实例管理模块

支持配置和运行多个独立的麦麦实例，每个实例拥有独立的人格、配置、数据存储和日志系统。

目录结构:
    data/maibot/
    ├── config/                    # 公共配置目录
    │   ├── instances_meta.json    # 实例元数据
    │   ├── instances/             # 实例独立配置
    │   │   └── {instance_id}.toml
    │   ├── bot_config.toml        # 机器人配置
    │   └── model_config.toml      # 模型配置
    └── instances/                 # 实例数据目录
        └── {instance_id}/
            ├── data/
            ├── cache/
            └── logs/
"""

from astrbot.core.maibot_instance.maibot_instance import (
    InstanceStatus,
    MaibotInstance,
    MaibotInstanceManager,
    initialize_instance_manager,
    get_instance_manager,
    start_maibot,
    stop_maibot,
    list_instances,
    get_instance_status,
)

__all__ = [
    "InstanceStatus",
    "MaibotInstance",
    "MaibotInstanceManager",
    "initialize_instance_manager",
    "get_instance_manager",
    "start_maibot",
    "stop_maibot",
    "list_instances",
    "get_instance_status",
]
