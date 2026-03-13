import asyncio
import time
from typing import List, Dict, Tuple, Optional, Any
from astrbot.core.maibot.src.plugin_system.apis.tool_api import get_llm_available_tool_definitions, get_tool_instance
from astrbot.core.maibot.src.plugin_system.base.base_tool import BaseTool
from astrbot.core.maibot.src.plugin_system.core.global_announcement_manager import global_announcement_manager
from astrbot.core.maibot.src.llm_models.utils_model import LLMRequest
from astrbot.core.maibot.src.llm_models.payload_content import ToolCall
from astrbot.core.maibot.src.config.config import global_config, model_config
from astrbot.core.maibot.src.chat.utils.prompt_builder import Prompt, global_prompt_manager
from astrbot.core.maibot.src.chat.message_receive.chat_stream import get_chat_manager
from astrbot.core.maibot.src.common.logger import get_logger

logger = get_logger("tool_use")

# ========== AstrBot 工具定义全局存储 ==========
# 存储从主进程通过 config 传递过来的 AstrBot 工具定义
_astrbot_tool_definitions: List[Dict[str, Any]] = []
# 存储 AstrBot 工具名称集合（用于快速判断）
_astrbot_tool_names: set = set()

# ========== IPC 客户端引用（用于调用主进程执行工具） ==========
_ipc_client = None


def set_ipc_client(client) -> None:
    """设置 IPC 客户端，供工具执行时使用

    Args:
        client: IPC 客户端对象
    """
    global _ipc_client
    _ipc_client = client
    logger.info("已设置 IPC 客户端")


def get_ipc_client():
    """获取 IPC 客户端"""
    return _ipc_client


def set_astrbot_tool_definitions(tool_definitions: List[Dict[str, Any]]) -> None:
    """设置 AstrBot 工具定义，供 ToolExecutor 使用

    Args:
        tool_definitions: 工具定义列表，每个元素为 {"name": str, "description": str, "parameters": dict}
    """
    global _astrbot_tool_definitions, _astrbot_tool_names
    _astrbot_tool_definitions = tool_definitions
    _astrbot_tool_names = {t.get("name", "") for t in tool_definitions if t.get("name")}
    logger.info(f"已设置 {len(tool_definitions)} 个 AstrBot 工具定义: {_astrbot_tool_names}")


def get_astrbot_tool_definitions() -> List[Dict[str, Any]]:
    """获取 AstrBot 工具定义

    Returns:
        工具定义列表
    """
    return _astrbot_tool_definitions


def clear_astrbot_tool_definitions() -> None:
    """清除 AstrBot 工具定义"""
    global _astrbot_tool_definitions
    _astrbot_tool_definitions = []
    logger.info("已清除 AstrBot 工具定义")


def init_tool_executor_prompt():
    """初始化工具执行器的提示词"""
    tool_executor_prompt = """
你是一个专门执行工具的助手。你的名字是{bot_name}。现在是{time_now}。
群里正在进行的聊天内容：
{chat_history}

现在，{sender}发送了内容:{target_message},你想要回复ta。
请仔细分析聊天内容，考虑以下几点：
1. 内容中是否包含需要查询信息的问题
2. 是否有明确的工具使用指令
你可以选择多个动作

If you need to use tools, please directly call the corresponding tool function. If you do not need to use any tool, simply output "No tool needed".
"""
    Prompt(tool_executor_prompt, "tool_executor_prompt")


# 初始化提示词
init_tool_executor_prompt()


class ToolExecutor:
    """独立的工具执行器组件

    可以直接输入聊天消息内容，自动判断并执行相应的工具，返回结构化的工具执行结果。
    """

    def __init__(self, chat_id: str, enable_cache: bool = True, cache_ttl: int = 3):
        """初始化工具执行器

        Args:
            executor_id: 执行器标识符，用于日志记录
            enable_cache: 是否启用缓存机制
            cache_ttl: 缓存生存时间（周期数）
        """
        self.chat_id = chat_id
        self.chat_stream = get_chat_manager().get_stream(self.chat_id)
        self.log_prefix = f"[{get_chat_manager().get_stream_name(self.chat_id) or self.chat_id}]"

        self.llm_model = LLMRequest(model_set=model_config.model_task_config.tool_use, request_type="tool_executor")

        # 缓存配置
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.tool_cache = {}  # 格式: {cache_key: {"result": result, "ttl": ttl, "timestamp": timestamp}}

        logger.info(f"{self.log_prefix}工具执行器初始化完成，缓存{'启用' if enable_cache else '禁用'}，TTL={cache_ttl}")

    async def execute_from_chat_message(
        self, target_message: str, chat_history: str, sender: str, return_details: bool = False
    ) -> Tuple[List[Dict[str, Any]], List[str], str]:
        """从聊天消息执行工具

        Args:
            target_message: 目标消息内容
            chat_history: 聊天历史
            sender: 发送者
            return_details: 是否返回详细信息(使用的工具列表和提示词)

        Returns:
            如果return_details为False: Tuple[List[Dict], List[str], str] - (工具执行结果列表, 空, 空)
            如果return_details为True: Tuple[List[Dict], List[str], str] - (结果列表, 使用的工具, 提示词)
        """

        # 首先检查缓存
        cache_key = self._generate_cache_key(target_message, chat_history, sender)
        if cached_result := self._get_from_cache(cache_key):
            logger.info(f"{self.log_prefix}使用缓存结果，跳过工具执行")
            if not return_details:
                return cached_result, [], ""

            # 从缓存结果中提取工具名称
            used_tools = [result.get("tool_name", "unknown") for result in cached_result]
            return cached_result, used_tools, ""

        # 缓存未命中，执行工具调用
        # 获取可用工具
        tools = self._get_tool_definitions()

        # 如果没有可用工具，直接返回空内容
        if not tools:
            logger.debug(f"{self.log_prefix}没有可用工具，直接返回空内容")
            if return_details:
                return [], [], ""
            else:
                return [], [], ""

        # print(f"tools: {tools}")

        # 获取当前时间
        time_now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        bot_name = global_config.bot.nickname

        # 构建工具调用提示词
        prompt = await global_prompt_manager.format_prompt(
            "tool_executor_prompt",
            target_message=target_message,
            chat_history=chat_history,
            sender=sender,
            bot_name=bot_name,
            time_now=time_now,
        )

        logger.debug(f"{self.log_prefix}开始LLM工具调用分析")

        # 调用LLM进行工具决策
        response, (reasoning_content, model_name, tool_calls) = await self.llm_model.generate_response_async(
            prompt=prompt, tools=tools, raise_when_empty=False
        )

        # 执行工具调用
        tool_results, used_tools = await self.execute_tool_calls(tool_calls)

        # 缓存结果
        if tool_results:
            self._set_cache(cache_key, tool_results)

        if used_tools:
            logger.info(f"{self.log_prefix}工具执行完成，共执行{len(used_tools)}个工具: {used_tools}")

        if return_details:
            return tool_results, used_tools, prompt
        else:
            return tool_results, [], ""

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """获取可用的工具定义

        优先级：
        1. 如果配置了 AstrBot 工具定义，优先使用（通过 config 传递）
        2. 否则使用 MaiBot 自己的工具定义
        """
        # 优先使用 AstrBot 工具定义
        if _astrbot_tool_definitions:
            logger.debug(f"{self.log_prefix}使用 AstrBot 工具定义 ({len(_astrbot_tool_definitions)} 个)")
            return _astrbot_tool_definitions

        # 回退到 MaiBot 自己的工具
        all_tools = get_llm_available_tool_definitions()
        user_disabled_tools = global_announcement_manager.get_disabled_chat_tools(self.chat_id)
        return [definition for name, definition in all_tools if name not in user_disabled_tools]

    async def execute_tool_calls(self, tool_calls: Optional[List[ToolCall]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """执行工具调用

        Args:
            tool_calls: LLM返回的工具调用列表

        Returns:
            Tuple[List[Dict], List[str]]: (工具执行结果列表, 使用的工具名称列表)
        """
        tool_results: List[Dict[str, Any]] = []
        used_tools = []

        if not tool_calls:
            logger.debug(f"{self.log_prefix}无需执行工具")
            return [], []

        # 提取tool_calls中的函数名称
        func_names = [call.func_name for call in tool_calls if call.func_name]

        logger.info(f"{self.log_prefix}开始执行工具调用: {func_names}")

        # 执行每个工具调用
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.func_name
                logger.debug(f"{self.log_prefix}执行工具: {tool_name}")

                # 执行工具
                result = await self.execute_tool_call(tool_call)

                if result:
                    tool_info = {
                        "type": result.get("type", "unknown_type"),
                        "id": result.get("id", f"tool_exec_{time.time()}"),
                        "content": result.get("content", ""),
                        "tool_name": tool_name,
                        "timestamp": time.time(),
                    }
                    content = tool_info["content"]
                    if not isinstance(content, (str, list, tuple)):
                        tool_info["content"] = str(content)
                    # 空内容直接跳过（空字符串、全空白字符串、空列表/空元组）
                    content_check = tool_info["content"]
                    if (isinstance(content_check, str) and not content_check.strip()) or (
                        isinstance(content_check, (list, tuple)) and len(content_check) == 0
                    ):
                        logger.debug(f"{self.log_prefix}工具{tool_name}无有效内容，跳过展示")
                        continue

                    tool_results.append(tool_info)
                    used_tools.append(tool_name)
                    preview = content[:200]
                    logger.debug(f"{self.log_prefix}工具{tool_name}结果内容: {preview}...")
            except Exception as e:
                logger.error(f"{self.log_prefix}工具{tool_name}执行失败: {e}")
                # 添加错误信息到结果中
                error_info = {
                    "type": "tool_error",
                    "id": f"tool_error_{time.time()}",
                    "content": f"工具{tool_name}执行失败: {str(e)}",
                    "tool_name": tool_name,
                    "timestamp": time.time(),
                }
                tool_results.append(error_info)

        return tool_results, used_tools

    async def execute_tool_call(
        self, tool_call: ToolCall, tool_instance: Optional[BaseTool] = None
    ) -> Optional[Dict[str, Any]]:
        # sourcery skip: use-assigned-variable
        """执行单个工具调用

        Args:
            tool_call: 工具调用对象

        Returns:
            Optional[Dict]: 工具调用结果，如果失败则返回None
        """
        try:
            function_name = tool_call.func_name
            function_args = tool_call.args or {}
            function_args["llm_called"] = True  # 标记为LLM调用

            # 判断是否为 AstrBot 工具（通过工具名称判断）
            if function_name in _astrbot_tool_names:
                # 通过 IPC 调用主进程执行 AstrBot 工具
                result = await self._execute_astrbot_tool_via_ipc(function_name, function_args)
                if result:
                    return {
                        "tool_call_id": tool_call.call_id,
                        "role": "tool",
                        "name": function_name,
                        "type": "function",
                        "content": result,
                    }
                return None

            # 获取对应工具实例（MaiBot 自己的工具）
            tool_instance = tool_instance or get_tool_instance(function_name, self.chat_stream)
            if not tool_instance:
                logger.warning(f"未知工具名称: {function_name}")
                return None

            # 执行工具
            result = await tool_instance.execute(function_args)
            if result:
                return {
                    "tool_call_id": tool_call.call_id,
                    "role": "tool",
                    "name": function_name,
                    "type": "function",
                    "content": result["content"],
                }
            return None
        except Exception as e:
            logger.error(f"执行工具调用时发生错误: {str(e)}")
            raise e

    async def _execute_astrbot_tool_via_ipc(self, tool_name: str, tool_args: dict) -> Optional[str]:
        """通过 IPC 调用主进程执行 AstrBot 工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果，如果失败则返回 None
        """
        import uuid
        from multiprocessing import Queue

        # 检查是否有 IPC 客户端
        client = get_ipc_client()
        if not client:
            logger.warning(f"IPC 客户端未设置，无法执行 AstrBot 工具: {tool_name}")
            return None

        request_id = str(uuid.uuid4())

        # 发送工具执行请求到主进程
        # 注意：这里我们需要使用同步的方式发送，然后等待结果
        try:
            # 直接使用 Queue 发送（LocalClient 内部也是用 Queue）
            # 构造消息
            msg = {
                "type": "tool_execute",
                "payload": {
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                }
            }

            # 发送到主进程
            client.input_queue.put_nowait(msg)

            # 等待结果（从 output_queue）
            start_time = time.time()
            timeout = 30.0  # 30 秒超时

            while time.time() - start_time < timeout:
                await asyncio.sleep(0.1)

                if client.output_queue.empty():
                    continue

                try:
                    result_msg = client.output_queue.get_nowait()
                    msg_type = result_msg.get("type", "")
                    if msg_type == "tool_execute_result":
                        payload = result_msg.get("payload", {})
                        req_id = payload.get("request_id", "")
                        if req_id == request_id:
                            if payload.get("success"):
                                result = payload.get("result", {})
                                return result.get("content", "")
                            else:
                                error = payload.get("error", "未知错误")
                                logger.error(f"AstrBot 工具执行失败: {error}")
                                return f"工具执行失败: {error}"
                except Exception:
                    continue

            logger.warning(f"AstrBot 工具执行超时: {tool_name}")
            return None

        except Exception as e:
            logger.error(f"通过 IPC 执行 AstrBot 工具失败: {e}")
            return None

    def _generate_cache_key(self, target_message: str, chat_history: str, sender: str) -> str:
        """生成缓存键

        Args:
            target_message: 目标消息内容
            chat_history: 聊天历史
            sender: 发送者

        Returns:
            str: 缓存键
        """
        import hashlib

        # 使用消息内容和群聊状态生成唯一缓存键
        content = f"{target_message}_{chat_history}_{sender}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """从缓存获取结果

        Args:
            cache_key: 缓存键

        Returns:
            Optional[List[Dict]]: 缓存的结果，如果不存在或过期则返回None
        """
        if not self.enable_cache or cache_key not in self.tool_cache:
            return None

        cache_item = self.tool_cache[cache_key]
        if cache_item["ttl"] <= 0:
            # 缓存过期，删除
            del self.tool_cache[cache_key]
            logger.debug(f"{self.log_prefix}缓存过期，删除缓存键: {cache_key}")
            return None

        # 减少TTL
        cache_item["ttl"] -= 1
        logger.debug(f"{self.log_prefix}使用缓存结果，剩余TTL: {cache_item['ttl']}")
        return cache_item["result"]

    def _set_cache(self, cache_key: str, result: List[Dict]):
        """设置缓存

        Args:
            cache_key: 缓存键
            result: 要缓存的结果
        """
        if not self.enable_cache:
            return

        self.tool_cache[cache_key] = {"result": result, "ttl": self.cache_ttl, "timestamp": time.time()}
        logger.debug(f"{self.log_prefix}设置缓存，TTL: {self.cache_ttl}")

    def _cleanup_expired_cache(self):
        """清理过期的缓存"""
        if not self.enable_cache:
            return

        expired_keys = []
        expired_keys.extend(cache_key for cache_key, cache_item in self.tool_cache.items() if cache_item["ttl"] <= 0)
        for key in expired_keys:
            del self.tool_cache[key]

        if expired_keys:
            logger.debug(f"{self.log_prefix}清理了{len(expired_keys)}个过期缓存")

    async def execute_specific_tool_simple(self, tool_name: str, tool_args: Dict) -> Optional[Dict]:
        """直接执行指定工具

        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            validate_args: 是否验证参数

        Returns:
            Optional[Dict]: 工具执行结果，失败时返回None
        """
        try:
            tool_call = ToolCall(
                call_id=f"direct_tool_{time.time()}",
                func_name=tool_name,
                args=tool_args,
            )

            logger.info(f"{self.log_prefix}直接执行工具: {tool_name}")

            result = await self.execute_tool_call(tool_call)

            if result:
                tool_info = {
                    "type": result.get("type", "unknown_type"),
                    "id": result.get("id", f"direct_tool_{time.time()}"),
                    "content": result.get("content", ""),
                    "tool_name": tool_name,
                    "timestamp": time.time(),
                }
                logger.info(f"{self.log_prefix}直接工具执行成功: {tool_name}")
                return tool_info

        except Exception as e:
            logger.error(f"{self.log_prefix}直接工具执行失败 {tool_name}: {e}")

        return None

    def clear_cache(self):
        """清空所有缓存"""
        if self.enable_cache:
            cache_count = len(self.tool_cache)
            self.tool_cache.clear()
            logger.info(f"{self.log_prefix}清空了{cache_count}个缓存项")

    def get_cache_status(self) -> Dict:
        """获取缓存状态信息

        Returns:
            Dict: 包含缓存统计信息的字典
        """
        if not self.enable_cache:
            return {"enabled": False, "cache_count": 0}

        # 清理过期缓存
        self._cleanup_expired_cache()

        total_count = len(self.tool_cache)
        ttl_distribution = {}

        for cache_item in self.tool_cache.values():
            ttl = cache_item["ttl"]
            ttl_distribution[ttl] = ttl_distribution.get(ttl, 0) + 1

        return {
            "enabled": True,
            "cache_count": total_count,
            "cache_ttl": self.cache_ttl,
            "ttl_distribution": ttl_distribution,
        }

    def set_cache_config(self, enable_cache: Optional[bool] = None, cache_ttl: int = -1):
        """动态修改缓存配置

        Args:
            enable_cache: 是否启用缓存
            cache_ttl: 缓存TTL
        """
        if enable_cache is not None:
            self.enable_cache = enable_cache
            logger.info(f"{self.log_prefix}缓存状态修改为: {'启用' if enable_cache else '禁用'}")

        if cache_ttl > 0:
            self.cache_ttl = cache_ttl
            logger.info(f"{self.log_prefix}缓存TTL修改为: {cache_ttl}")


"""
ToolExecutor使用示例：

# 1. 基础使用 - 从聊天消息执行工具（启用缓存，默认TTL=3）
executor = ToolExecutor(executor_id="my_executor")
results, _, _ = await executor.execute_from_chat_message(
    talking_message_str="今天天气怎么样？现在几点了？",
    is_group_chat=False
)

# 2. 禁用缓存的执行器
no_cache_executor = ToolExecutor(executor_id="no_cache", enable_cache=False)

# 3. 自定义缓存TTL
long_cache_executor = ToolExecutor(executor_id="long_cache", cache_ttl=10)

# 4. 获取详细信息
results, used_tools, prompt = await executor.execute_from_chat_message(
    talking_message_str="帮我查询Python相关知识",
    is_group_chat=False,
    return_details=True
)

# 5. 直接执行特定工具
result = await executor.execute_specific_tool_simple(
    tool_name="get_knowledge",
    tool_args={"query": "机器学习"}
)

# 6. 缓存管理
cache_status = executor.get_cache_status()  # 查看缓存状态
executor.clear_cache()  # 清空缓存
executor.set_cache_config(cache_ttl=5)  # 动态修改缓存配置
"""
