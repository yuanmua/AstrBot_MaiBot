"""
MaiBot 多实例管理器测试

测试内容包括：
1. 实例的创建和元数据管理
2. 配置文件的自动创建和复制
3. 生命周期管理（启动、停止）
4. 多实例管理
"""

import os
import shutil
import pytest


class TestMaibotInstanceManager:
    """MaiBot 实例管理器测试类"""

    @pytest.fixture
    def temp_data_root(self):
        # """创建临时数据目录"""
        # temp_dir = tempfile.mkdtemp(prefix="maibot_test_")
        """创建临时数据目录（在项目内）"""
        # 使用项目内的临时目录
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")
        temp_dir = os.path.join(base_dir, f"maibot_test_{os.getpid()}")
        os.makedirs(temp_dir, exist_ok=True)
        yield temp_dir
        # 清理
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def instance_manager(self, temp_data_root):
        """创建实例管理器"""
        from astrbot.core.maibot.maibot_adapter import (
            MaibotInstanceManager,
        )
        manager = MaibotInstanceManager(data_root=temp_data_root)
        return manager

    def test_maibot_instance_creation(self):
        """测试 MaibotInstance 实例创建"""
        from astrbot.core.maibot.maibot_adapter import MaibotInstance
        from astrbot.core.maibot.maibot_adapter import InstanceStatus

        instance = MaibotInstance(
            instance_id="test_instance",
            name="测试实例",
            description="这是一个测试实例",
            is_default=False,
            host="0.0.0.0",
            port=9000,
            web_host="0.0.0.0",
            web_port=9001,
            enable_webui=True,
            enable_socket=True,
        )

        assert instance.instance_id == "test_instance"
        assert instance.name == "测试实例"
        assert instance.description == "这是一个测试实例"
        assert instance.is_default is False
        assert instance.host == "0.0.0.0"
        assert instance.port == 9000
        assert instance.web_host == "0.0.0.0"
        assert instance.web_port == 9001
        assert instance.enable_webui is True
        assert instance.enable_socket is True
        assert instance.status == InstanceStatus.STOPPED
