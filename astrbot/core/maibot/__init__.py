"""
MaiBot集成模块
提供MaiBot的初始化和生命周期管理
"""

import asyncio
from typing import Optional

from astrbot.core.maibot.common.logger import get_logger

logger = get_logger("maibot_init")


class MaiBotCore:
    """MaiBot核心管理类"""

    def __init__(self):
        self.main_system = None
        self.initialized = False
        self._schedule_task = None

    async def initialize(self, data_root: str):
        """
        初始化MaiBot
        Args:
            data_root: 数据根目录，例如 'data/maibot'
        """
        if self.initialized:
            logger.warning("MaiBot已经初始化过了")
            return

        logger.info("正在初始化 MaiBot...")

        # 1. 加载环境变量
        import os
        import shutil
        from pathlib import Path
        from dotenv import load_dotenv

        # 确保data_root目录存在
        os.makedirs(data_root, exist_ok=True)

        # 查找.env文件
        env_path = Path(data_root) / ".env"
        template_env_path = Path(__file__).parent / "template" / "template.env"

        if not env_path.exists():
            if template_env_path.exists():
                shutil.copyfile(template_env_path, env_path)
                logger.info(f"已从模板创建 .env 文件: {env_path}")
            else:
                logger.warning(f"未找到 .env 模板文件: {template_env_path}")
                # 创建默认的.env文件
                env_path.write_text(
                    "# MaiBot主程序配置\n"
                    "HOST=127.0.0.1\n"
                    "PORT=8000\n"
                    "\n"
                    "# WebUI 服务器配置\n"
                    "WEBUI_HOST=127.0.0.1\n"
                    "WEBUI_PORT=8001\n",
                    encoding="utf-8",
                )
                logger.info(f"已创建默认 .env 文件: {env_path}")

        # 加载.env文件到环境变量
        load_dotenv(str(env_path), override=True)
        logger.info(
            f"已加载环境变量: HOST={os.getenv('HOST')}, PORT={os.getenv('PORT')}"
        )

        # 设置 MaiBot 路径（用于 WebUI 静态文件）
        maiabot_project_path = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        maiabot_project_path = os.path.join(maiabot_project_path, "MaiBot")
        maiabot_project_path = os.path.normpath(maiabot_project_path)
        os.environ.setdefault("MAIBOT_PATH", maiabot_project_path)
        logger.info(f"MAIBOT_PATH: {maiabot_project_path}")

        # 2. 初始化路径配置
        from astrbot.core.maibot.config.config import initialize_paths, load_configs

        # 设置 depends-data 目录环境变量
        depends_data_dir = os.path.join(data_root, "depends-data")
        os.environ.setdefault("MAIBOT_DEPENDS_DATA_DIR", depends_data_dir)
        logger.info(f"MAIBOT_DEPENDS_DATA_DIR: {depends_data_dir}")

        initialize_paths(data_root)

        # 3. 初始化数据库
        from astrbot.core.maibot.common.database.database import initialize_database

        initialize_database(data_root)
        logger.info(f"数据库已初始化")

        # 4. 加载配置文件
        load_configs()

        # 5. 创建MainSystem实例
        from astrbot.core.maibot.main import MainSystem

        logger.info("正在创建 MainSystem...")
        self.main_system = MainSystem()

        logger.info("正在初始化 MainSystem...")
        await self.main_system.initialize()
        logger.info("MainSystem 初始化完成")

        # 6. 注册 AstrBot 平台适配器
        logger.info("正在注册 AstrBot 适配器...")
        await self._register_astrbot_adapter()

        self.initialized = True
        logger.info("MaiBot 初始化完成")

    async def _register_astrbot_adapter(self):
        """注册 AstrBot 平台适配器，拦截消息发送"""
        try:
            from astrbot.core.maibot.common.message.api import get_global_api
            from astrbot.core.maibot_adapter.platform_adapter import get_astrbot_adapter, parse_astrbot_platform

            # 获取 MaiBot 的消息服务器
            message_server = get_global_api()

            # 获取 AstrBot 适配器
            astrbot_adapter = get_astrbot_adapter()

            # 保存原始的 send_message 方法
            original_send_message = message_server.send_message

            # 创建包装函数
            async def wrapped_send_message(message):
                """包装 send_message，拦截 AstrBot 平台的消息"""
                try:
                    # 获取消息的 platform 属性
                    platform = getattr(message.message_info, 'platform', None)

                    # 解析是否为 AstrBot 平台（astr:{stream_id} 格式）
                    stream_id = parse_astrbot_platform(platform)

                    if stream_id:
                        # 使用 AstrBot 适配器处理
                        logger.debug(f"[AstrBot 适配器] 拦截消息 -> stream_id: {stream_id[:16]}..., 内容: {getattr(message, 'processed_plain_text', '')[:50]}")
                        return await astrbot_adapter.send_message(message)
                    elif platform and platform.startswith('AstrBot'):
                        # 旧格式兼容
                        logger.debug(f"[AstrBot 适配器] 拦截消息(旧格式): {platform}, 内容: {getattr(message, 'processed_plain_text', '')[:50]}")
                        return await astrbot_adapter.send_message(message)
                    else:
                        # 其他平台使用原始方法
                        return await original_send_message(message)

                except Exception as e:
                    logger.error(f"包装的 send_message 失败: {e}", exc_info=True)
                    # Fallback 到原始方法
                    return await original_send_message(message)

            # 替换 send_message 方法
            message_server.send_message = wrapped_send_message

            logger.info("✅ 已注册 AstrBot 平台适配器（通过 monkey patching）")

        except Exception as e:
            logger.error(f"注册 AstrBot 平台适配器失败: {e}", exc_info=True)

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

        logger.info("正在关闭 MaiBot...")

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


__all__ = ["MaiBotCore", "get_maibot_core"]
