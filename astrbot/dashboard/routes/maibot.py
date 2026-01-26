"""麦麦管理 API 路由

提供麦麦实例的创建、删除、启动、停止等管理功能。
"""

from typing import Optional

from quart import request

from astrbot.api import logger
from astrbot.core.core_lifecycle import AstrBotCoreLifecycle

from .route import Response, Route, RouteContext


class MaiBotManagerRoute(Route):
    """麦麦管理 API 路由"""

    def __init__(self, context: RouteContext, core_lifecycle: AstrBotCoreLifecycle):
        super().__init__(context)
        self.core_lifecycle = core_lifecycle
        self.routes = {
            # ============ 实例管理 ============
            "/maibot/instances": [
                ("GET", self.get_instances),
                ("POST", self.create_instance),
            ],
            "/maibot/instances/<instance_id>":  [
                ("GET", self.get_instance),
                ("PUT", self.update_instance),
                ("DELETE", self.delete_instance),
            ],
            # ============ 生命周期管理 ============
            "/maibot/instances/<instance_id>/start": ("POST", self.start_instance),
            "/maibot/instances/<instance_id>/stop": ("POST", self.stop_instance),
            "/maibot/instances/<instance_id>/restart": ("POST", self.restart_instance),
            # ============ 运行状态 ============
            "/maibot/running": ("GET", self.get_running_instances),
            "/maibot/default": [
                ("GET", self.get_default_instance),
                ("PUT", self.set_default_instance),
            ],
            # ============ 路由规则管理 ============
            "/maibot/routing/rules":[
                ("GET", self.get_routing_rules),
                ("PUT", self.save_routing_rules),
                ("DELETE", self.clear_routing_rules),
        ],
        }
        self.register_routes()

    @property
    def maibot_manager(self):
        """获取 MaiBot 实例管理器"""
        return getattr(self.core_lifecycle, "maibot_manager", None)

    def _check_maibot_manager(self) -> bool:
        """检查 maibot_manager 是否可用"""
        if not self.maibot_manager:
            logger.warning("MaiBot 管理器未初始化")
            return False
        return True

    # ============ 实例管理 ============

    async def get_instances(self):
        """获取所有实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            instances = self.maibot_manager.get_all_instances()
            return Response().ok({
                "instances": [inst.to_dict() for inst in instances],
                "total": len(instances),
            }).__dict__
        except Exception as e:
            logger.error(f"获取实例列表失败: {e}", exc_info=True)
            return Response().error(f"获取实例列表失败: {e}").__dict__, 500

    async def get_instance(self, instance_id: str):
        """获取单个实例详情"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            instance = self.maibot_manager.get_instance(instance_id)
            if not instance:
                return Response().error(f"实例 {instance_id} 不存在").__dict__, 404

            return Response().ok(instance.to_dict()).__dict__
        except Exception as e:
            logger.error(f"获取实例详情失败: {e}", exc_info=True)
            return Response().error(f"获取实例详情失败: {e}").__dict__, 500

    async def create_instance(self):
        """创建新实例

        Request Body:
            - instance_id: 实例 ID (必填)
            - name: 实例名称 (必填)
            - description: 描述
            - port: 服务端口
            - web_port: WebUI 端口
            - enable_webui: 是否启用 WebUI
            - enable_socket: 是否启用 Socket
        """
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            data = await request.get_json()

            instance_id = data.get("instance_id")
            name = data.get("name")
            if not instance_id or not name:
                return Response().error("实例 ID 和名称不能为空").__dict__, 400

            instance = await self.maibot_manager.create_instance(
                instance_id=instance_id,
                name=name,
                description=data.get("description", ""),
                host=data.get("host", "127.0.0.1"),
                port=data.get("port", 8000),
                web_host=data.get("web_host", "127.0.0.1"),
                web_port=data.get("web_port", 8001),
                enable_webui=data.get("enable_webui", False),
                enable_socket=data.get("enable_socket", False),
            )

            return Response().ok({
                "id": instance.instance_id,
                "name": instance.name,
                "message": "实例创建成功",
            }).__dict__

        except ValueError as e:
            return Response().error(str(e)).__dict__, 409
        except Exception as e:
            logger.error(f"创建实例失败: {e}", exc_info=True)
            return Response().error(f"创建实例失败: {e}").__dict__, 500

    async def update_instance(self, instance_id: str):
        """更新实例配置

        Request Body:
            - name: 实例名称
            - description: 描述
            - lifecycle: 生命周期配置
        """
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            instance = self.maibot_manager.get_instance(instance_id)
            if not instance:
                return Response().error(f"实例 {instance_id} 不存在").__dict__, 404

            data = await request.get_json()

            # 更新字段
            if "name" in data:
                instance.name = data["name"]
            if "description" in data:
                instance.description = data["description"]
            if "lifecycle" in data:
                instance.lifecycle.update(data["lifecycle"])

            # 更新配置
            instance.updated_at = None  # 会在保存时自动设置

            await self.maibot_manager._save_instances_metadata()

            return Response().ok({
                "id": instance_id,
                "message": "配置已更新",
            }).__dict__

        except Exception as e:
            logger.error(f"更新实例配置失败: {e}", exc_info=True)
            return Response().error(f"更新实例配置失败: {e}").__dict__, 500

    async def delete_instance(self, instance_id: str):
        """删除实例

        Query Parameters:
            - delete_data: 是否删除数据目录 (默认 false)
        """
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            # 检查实例是否存在
            instance = self.maibot_manager.get_instance(instance_id)
            if not instance:
                return Response().error(f"实例 {instance_id} 不存在").__dict__, 404

            # 如果实例正在运行，先停止
            if instance.status.value == "running":
                await self.maibot_manager.stop_instance(instance_id)

            # 从管理器中移除
            del self.maibot_manager.instances[instance_id]
            await self.maibot_manager._save_instances_metadata()

            return Response().ok({
                "deleted": True,
                "instance_id": instance_id,
            }).__dict__

        except Exception as e:
            logger.error(f"删除实例失败: {e}", exc_info=True)
            return Response().error(f"删除实例失败: {e}").__dict__, 500

    # ============ 生命周期管理 ============

    async def start_instance(self, instance_id: str):
        """启动实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            success = await self.maibot_manager.start_instance(instance_id)
            if not success:
                instance = self.maibot_manager.get_instance(instance_id)
                error_msg = instance.error_message if instance else "启动失败"
                return Response().error(error_msg).__dict__, 400

            return Response().ok({
                "id": instance_id,
                "status": "starting",
                "message": "实例启动中...",
            }).__dict__

        except Exception as e:
            logger.error(f"启动实例失败: {e}", exc_info=True)
            return Response().error(f"启动实例失败: {e}").__dict__, 500

    async def stop_instance(self, instance_id: str):
        """停止实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            success = await self.maibot_manager.stop_instance(instance_id)
            if not success:
                return Response().error("停止失败").__dict__, 400

            return Response().ok({
                "id": instance_id,
                "status": "stopping",
                "message": "实例停止中...",
            }).__dict__

        except Exception as e:
            logger.error(f"停止实例失败: {e}", exc_info=True)
            return Response().error(f"停止实例失败: {e}").__dict__, 500

    async def restart_instance(self, instance_id: str):
        """重启实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            success = await self.maibot_manager.restart_instance(instance_id)
            if not success:
                return Response().error("重启失败").__dict__, 400

            return Response().ok({
                "id": instance_id,
                "status": "restarting",
                "message": "实例重启中...",
            }).__dict__

        except Exception as e:
            logger.error(f"重启实例失败: {e}", exc_info=True)
            return Response().error(f"重启实例失败: {e}").__dict__, 500

    # ============ 运行状态 ============

    async def get_running_instances(self):
        """获取运行中的实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            running = self.maibot_manager.get_running_instances()
            return Response().ok({
                "instances": [inst.to_dict() for inst in running],
                "total": len(running),
            }).__dict__
        except Exception as e:
            logger.error(f"获取运行中实例失败: {e}", exc_info=True)
            return Response().error(f"获取运行中实例失败: {e}").__dict__, 500

    async def get_default_instance(self):
        """获取默认实例"""
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            default = None
            for instance in self.maibot_manager.instances.values():
                if instance.is_default:
                    default = instance
                    break
            if not default:
                # 如果没有标记为默认的，返回第一个
                instances = list(self.maibot_manager.instances.values())
                if instances:
                    default = instances[0]

            if default:
                return Response().ok(default.to_dict()).__dict__
            return Response().error("未设置默认实例").__dict__, 404
        except Exception as e:
            logger.error(f"获取默认实例失败: {e}", exc_info=True)
            return Response().error(f"获取默认实例失败: {e}").__dict__, 500

    async def set_default_instance(self):
        """设置默认实例

        Request Body:
            - instance_id: 实例 ID
        """
        if not self._check_maibot_manager():
            return Response().error("麦麦管理器未初始化").__dict__, 500

        try:
            data = await request.get_json()
            instance_id = data.get("instance_id")
            if not instance_id:
                return Response().error("实例 ID 不能为空").__dict__, 400

            instance = self.maibot_manager.get_instance(instance_id)
            if not instance:
                return Response().error(f"实例 {instance_id} 不存在").__dict__, 404

            # 取消之前的默认实例
            for inst in self.maibot_manager.instances.values():
                inst.is_default = False

            # 设置新的默认实例
            instance.is_default = True
            await self.maibot_manager._save_instances_metadata()

            return Response().ok({
                "instance_id": instance_id,
                "message": "默认实例已更新",
            }).__dict__
        except Exception as e:
            logger.error(f"设置默认实例失败: {e}", exc_info=True)
            return Response().error(f"设置默认实例失败: {e}").__dict__, 500

    # ============ 路由规则管理 ============

    async def get_routing_rules(self):
        """获取路由规则"""
        try:
            adapter = self.maibot_adapter
            if not adapter:
                return Response().error("适配器未初始化").__dict__, 500

            return Response().ok({
                "default_instance": adapter.message_router.default_instance,
                "rules": adapter.message_router.get_rules(),
            }).__dict__
        except Exception as e:
            logger.error(f"获取路由规则失败: {e}", exc_info=True)
            return Response().error(f"获取路由规则失败: {e}").__dict__, 500

    async def save_routing_rules(self):
        """保存路由规则

        Request Body:
            - default_instance: 默认实例 ID
            - rules: 路由规则列表 [{"chat_id": "...", "instance_id": "..."}]
        """
        try:
            adapter = self.maibot_adapter
            if not adapter:
                return Response().error("适配器未初始化").__dict__, 500

            data = await request.get_json()

            if "default_instance" in data:
                adapter.message_router.set_default_instance(data["default_instance"])

            if "rules" in data:
                # 清空现有规则并添加新规则
                adapter.message_router.clear_rules()
                for rule in data["rules"]:
                    chat_id = rule.get("chat_id")
                    instance_id = rule.get("instance_id")
                    if chat_id and instance_id:
                        adapter.message_router.add_rule(chat_id, instance_id)

            await adapter.message_router.save_config()

            return Response().ok({"message": "路由规则已保存"}).__dict__
        except Exception as e:
            logger.error(f"保存路由规则失败: {e}", exc_info=True)
            return Response().error(f"保存路由规则失败: {e}").__dict__, 500

    async def clear_routing_rules(self):
        """清空路由规则"""
        try:
            adapter = self.maibot_adapter
            if not adapter:
                return Response().error("适配器未初始化").__dict__, 500

            adapter.message_router.clear_rules()
            await adapter.message_router.save_config()

            return Response().ok({"message": "路由规则已清空"}).__dict__
        except Exception as e:
            logger.error(f"清空路由规则失败: {e}", exc_info=True)
            return Response().error(f"清空路由规则失败: {e}").__dict__, 500

    @property
    def maibot_adapter(self):
        """获取 MaiBot 适配器"""
        from astrbot.core.maibot_adapter import get_astrbot_adapter
        return get_astrbot_adapter()
