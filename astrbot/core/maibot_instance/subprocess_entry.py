"""
子进程入口模块

作为子进程的主入口点，负责：
1. 从 input_queue 读取控制命令和消息
2. 执行 MaiBotCore 的初始化和启动
3. 通过 output_queue 发送状态更新、日志和回复
"""

import asyncio
import multiprocessing
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 计算 MaiBot 项目路径并设置为环境变量（必须在导入 MaiBot 之前设置）
MAIBOT_PATH = os.path.join(PROJECT_ROOT, "MaiBot")
os.environ["MAIBOT_PATH"] = MAIBOT_PATH

# 默认日志配置
DEFAULT_LOG_CONFIG = {
    "enable_console": True,
    "log_level": "INFO",
}


def _run_subprocess_main(
    instance_id: str,
    data_root: str,
    config: Dict[str, Any],
    input_queue: multiprocessing.Queue,
    output_queue: multiprocessing.Queue,
):
    """同步包装函数，用于 multiprocessing.Process

    创建一个新的事件循环并运行异步的 subprocess_main_async
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            subprocess_main_async(
                instance_id=instance_id,
                data_root=data_root,
                config=config,
                input_queue=input_queue,
                output_queue=output_queue,
            )
        )
    finally:
        loop.close()


async def subprocess_main_async(
    instance_id: str,
    data_root: str,
    config: Dict[str, Any],
    input_queue: multiprocessing.Queue,
    output_queue: multiprocessing.Queue,
):
    """
    子进程主入口函数（异步版本）

    Args:
        instance_id: 实例ID
        data_root: 数据根目录
        config: 实例配置字典
        input_queue: 命令输入队列（主进程 -> 子进程）
        output_queue: 状态输出队列（子进程 -> 主进程）
    """
    import signal

    # 1. 先初始化实例日志系统（在导入任何 MaiBot 模块之前）
    # 关键：立即标记子进程模式，确保后续导入的模块知道使用 maibot_logger
    from astrbot.core.maibot_adapter.maibot_logger import (
        _mark_subprocess_mode,
        initialize_maibot_logger,
        get_logger,
        set_log_publisher,
        get_maibot_logger,
    )

    # 立即标记子进程模式，防止后续模块导入时重复配置日志
    _mark_subprocess_mode()

    log_config = config.get("logging", DEFAULT_LOG_CONFIG)
    enable_console = log_config.get("enable_console", True)

    # 设置日志发布回调，用于发送到主进程（仅在 enable_console=True 时设置）
    def send_log_to_main(level: str, msg: str):
        output_queue.put({
            "type": "log",
            "payload": {
                "level": level,
                "message": msg,
                "timestamp": datetime.now().isoformat(),
            }
        })

    if enable_console:
        set_log_publisher(send_log_to_main)

    initialize_maibot_logger(
        instance_id=instance_id,
        log_level=log_config.get("log_level", "INFO"),
        enable_console=enable_console,
    )
    maibot_logger = get_logger("subprocess")

    # 2. 然后导入 MaiBot（会使用已初始化的 maibot_logger）
    from astrbot.core.maibot import MaiBotCore

    # 获取实例日志目录路径
    base_log_dir = Path(config.get("data_root", data_root)).parent / "logs" / "mailog"

    # 设置子进程信号处理
    def signal_handler(signum, frame):
        output_queue.put({
            "type": "signal",
            "payload": {"signal": signum}
        })

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    maibot_core: Optional[MaiBotCore] = None
    running = True
    shutdown_requested = False
    reply_monitor_task = None  # 初始化为 None，避免未定义引用

    # 辅助函数：发送状态到主进程
    def send_status(status: str, message: str = "", error: str = ""):
        output_queue.put({
            "type": "status",
            "payload": {
                "instance_id": instance_id,
                "status": status,
                "message": message,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        })

    # 辅助函数：发送日志到主进程
    def send_log(level: str, msg: str, exc_info: bool = False):
        output_queue.put({
            "type": "log",
            "payload": {
                "level": level,
                "message": msg,
                "timestamp": datetime.now().isoformat(),
            }
        })

    # 辅助函数：发送消息处理结果
    def send_message_result(success: bool, result: Any = None, error: str = ""):
        output_queue.put({
            "type": "message_result",
            "payload": {
                "success": success,
                "result": result,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        })

    # 辅助函数：发送回复到主进程（当 monkey patch 拦截到回复时调用）
    def send_reply_to_mainprocess(message, stream_id: str):
        """将拦截到的回复发送给主进程

        只做序列化，不做消息转换。转换在主进程中进行。
        """
        try:
            # 获取消息信息
            message_info = getattr(message, "message_info", None)
            message_segment = getattr(message, "message_segment", None)
            processed_plain_text = getattr(message, "processed_plain_text", "")

            # 获取 platform 包含的实例 ID
            platform = getattr(message_info, "platform", "") if message_info else ""
            from astrbot.core.maibot_adapter.platform_adapter import parse_astrbot_instance_id
            instance_id = parse_astrbot_instance_id(platform) or "default"

            send_log("info", f"[回调] 🔔 拦截到回复: stream_id={stream_id[:16] if stream_id else 'None'}, instance_id={instance_id}")
            send_log("info", f"[回调] 消息内容预览: {processed_plain_text[:100] if processed_plain_text else '空'}")

            # 将 Seg 对象转换为可序列化的字典列表
            from astrbot.core.maibot_adapter.response_converter import seg_to_dict_list
            segments = seg_to_dict_list(message_segment)
            send_log("info", f"[回调] segments 数量: {len(segments) if segments else 0}")

            # 发送到主进程
            output_queue.put({
                "type": "message_reply",
                "payload": {
                    "stream_id": stream_id,
                    "instance_id": instance_id,
                    "segments": segments,  # 字典列表，主进程中转换为 MessageChain
                    "processed_plain_text": processed_plain_text,
                    "timestamp": datetime.now().isoformat(),
                }
            })
            send_log("info", f"[回调] ✅ 已放入 output_queue: stream_id={stream_id[:16] if stream_id else 'None'}")
        except Exception as e:
            send_log("error", f"[回调] ❌ 发送回复到主进程失败: {e}", exc_info=True)

    send_status("starting", "子进程启动中...")

    # 打印路径信息用于调试
    maibot_logger.info(f"PROJECT_ROOT: {PROJECT_ROOT}")
    maibot_logger.info(f"MAIBOT_PATH: {MAIBOT_PATH}")
    maibot_logger.info(f"MAIBOT_PATH exists: {os.path.exists(MAIBOT_PATH)}")
    maibot_logger.info(f"WebUI dist exists: {os.path.exists(os.path.join(MAIBOT_PATH, 'webui', 'dist'))}")

    try:
        send_log("info", f"子进程启动: instance_id={instance_id}, data_root={data_root}")
        send_log("info", f"MAIBOT_PATH: {MAIBOT_PATH}")

        # 清除缓存的 API 实例（确保每次都是新实例）
        from astrbot.core.maibot.common.message.api import clear_cached_api
        clear_cached_api()

        # 创建 MaiBotCore 实例
        maibot_core = MaiBotCore(instance_id=instance_id, config=config)

        # 初始化 MaiBot
        send_status("initializing", "正在初始化 MaiBot...")
        send_log("info", "开始初始化 MaiBotCore")

        try:
            await maibot_core.initialize()
            send_log("info", "MaiBotCore 初始化完成")
            send_status("initialized", "初始化完成，启动中...")

            # 启动 MaiBot
            await maibot_core.start()
            send_log("info", "MaiBotCore 启动完成")
            send_status("running", "运行中")

        except SystemExit as e:
            if e.code == 0:
                # 配置文件不存在，已创建模板
                send_status("config_needed", "配置已创建，请填写后重新启动")
                send_log("warning", "配置文件不存在，已创建模板")
                return
            else:
                send_status("error", f"初始化退出: {e.code}")
                send_log("error", f"初始化退出，退出码: {e.code}")
                return
        except Exception as e:
            send_status("error", f"初始化失败: {e}")
            send_log("error", f"初始化失败: {e}")
            import traceback
            send_log("error", traceback.format_exc())
            return

        # 设置 monkey patch 的回调函数（用于发送回复到主进程）
        from astrbot.core.maibot_adapter.platform_adapter import (
            get_astrbot_adapter,
            set_reply_callback,
            AstrBotPlatformAdapter,
        )
        send_log("info", f"[子进程] 🔧 准备设置回复回调...")
        send_log("info", f"[子进程] send_reply_to_mainprocess 函数地址: {send_reply_to_mainprocess}")
        set_reply_callback(send_reply_to_mainprocess)
        send_log("info", f"[子进程] ✅ 回复回调已设置: {AstrBotPlatformAdapter._reply_callback}")

        # 设置知识库适配器的 IPC 队列并根据配置创建适配器
        from astrbot.core.maibot.chat.knowledge.knowledge_base_adapter import (
            KnowledgeBaseAdapter,
            create_kb_adapter,
        )
        KnowledgeBaseAdapter.set_ipc_queues(output_queue, instance_id)

        # 从配置中读取知识库设置
        kb_config = config.get("knowledge_base", {})
        if kb_config.get("enabled", False):
            kb_names = kb_config.get("kb_names", [])
            fusion_top_k = kb_config.get("fusion_top_k", 5)
            return_top_k = kb_config.get("return_top_k", 20)
            if kb_names:
                adapter = create_kb_adapter(
                    kb_names=kb_names,
                    fusion_top_k=fusion_top_k,
                    return_top_k=return_top_k,
                )
                send_log("info", f"知识库适配器已创建: kb_names={kb_names}, fusion_top_k={fusion_top_k}, return_top_k={return_top_k}")
            else:
                send_log("info", "知识库适配器已启用但未指定知识库名称，跳过创建")
        else:
            send_log("info", "知识库适配器未启用")

        # 启动回复监听任务

        # 消息处理函数（在 MaiBot 启动后定义，以便访问 chat_bot）
        async def _handle_message(payload: Dict[str, Any]) -> None:
            """处理来自主进程的消息（IPC 模式）

            Args:
                payload: 消息载荷，包含 message_data 等
            """
            try:
                message_data = payload.get("message_data")
                if not message_data:
                    send_message_result(False, error="消息数据为空")
                    return

                stream_id = payload.get("stream_id", "unknown")
                send_log("info", f"收到消息: stream_id={stream_id[:16] if stream_id != 'unknown' else stream_id}...")
                send_log("info", f"message_data keys: {list(message_data.keys()) if message_data else 'empty'}")

                # 获取 MaiBot 的 ChatBot 实例处理消息
                from astrbot.core.maibot.chat.message_receive.bot import chat_bot

                # 调用 MaiBot 的消息处理
                send_log("info", f"调用 chat_bot.message_process...")
                await chat_bot.message_process(message_data)
                send_log("info", f"chat_bot.message_process 完成")

                # 注意：回复会在 monkey patch 中被拦截，并通过 _monitor_pending_replies 发送给主进程
                # 这里只需要返回成功，回复由后台任务处理
                send_log("info", f"消息已提交处理，回复将由后台任务发送给主进程")
                send_message_result(True, result={"status": "processed", "reply": None})

            except Exception as e:
                send_log("error", f"处理消息失败: {e}", exc_info=True)
                send_message_result(False, error=str(e))

        # 主循环：处理来自主进程的命令
        send_log("info", "开始处理命令...")
        while running:
            try:
                # 非阻塞读取命令，设置超时以便定期检查shutdown标志
                if input_queue.empty():
                    await asyncio.sleep(0.05)
                    continue

                cmd = input_queue.get(timeout=1.0)
                cmd_type = cmd.get("type", "unknown")

                if cmd_type == "stop":
                    send_log("info", "收到停止命令")
                    running = False
                    shutdown_requested = True
                    break
                elif cmd_type == "ping":
                    output_queue.put({
                        "type": "pong",
                        "payload": {"instance_id": instance_id}
                    })
                elif cmd_type == "status":
                    output_queue.put({
                        "type": "status",
                        "payload": {
                            "instance_id": instance_id,
                            "status": "running",
                            "message": "正常运行",
                        }
                    })
                elif cmd_type == "message":
                    # 处理消息（IPC 模式）- 在后台运行，不阻塞命令循环
                    # 这样可以让命令循环继续处理 kb_retrieve_result 等响应
                    asyncio.create_task(_handle_message(cmd.get("payload", {})))
                elif cmd_type == "kb_retrieve_result":
                    # 知识库检索结果，缓存到适配器
                    from astrbot.core.maibot.chat.knowledge.knowledge_base_adapter import cache_kb_response
                    payload = cmd.get("payload", {})
                    request_id = payload.get("request_id", "")
                    if request_id:
                        cache_kb_response(request_id, payload)
                        send_log("debug", f"收到知识库检索结果: request_id={request_id}")
                else:
                    send_log("warning", f"未知命令: {cmd_type}")

            except multiprocessing.queues.Empty:
                # 超时继续循环
                continue
            except Exception as e:
                send_log("error", f"处理命令时出错: {e}")
                continue

    except Exception as e:
        send_status("error", f"子进程异常: {e}")
        send_log("error", f"子进程异常: {e}")
        import traceback
        send_log("error", traceback.format_exc())
        running = False

    finally:

        # 关闭 MaiBot
        if maibot_core and shutdown_requested:
            try:
                await maibot_core.shutdown()
                send_log("info", "MaiBot 已关闭")
            except Exception as e:
                send_log("error", f"关闭 MaiBot 时出错: {e}")

        send_status("stopped", "子进程已停止")
        send_log("info", "子进程退出")


# 保持向后兼容，subprocess_main 现在是一个同步包装函数
def subprocess_main(
    instance_id: str,
    data_root: str,
    config: Dict[str, Any],
    input_queue: multiprocessing.Queue,
    output_queue: multiprocessing.Queue,
):
    """子进程主入口函数（保持同步以兼容 multiprocessing）"""
    _run_subprocess_main(instance_id, data_root, config, input_queue, output_queue)


if __name__ == "__main__":
    """
    Windows 下 multiprocessing 需要 __main__ 保护
    直接运行时可接收参数进行测试
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(description="MaiBot 子进程入口")
    parser.add_argument("--instance-id", required=True, help="实例ID")
    parser.add_argument("--data-root", required=True, help="数据根目录")
    parser.add_argument("--config", required=True, help="配置JSON字符串")

    args = parser.parse_args()

    # 创建测试用的队列
    input_queue = multiprocessing.Queue()
    output_queue = multiprocessing.Queue()

    config = json.loads(args.config)

    print(f"启动子进程: instance_id={args.instance_id}")
    print(f"数据目录: {args.data_root}")
    print(f"配置: {config}")

    # 启动子进程
    p = multiprocessing.Process(
        target=subprocess_main,
        args=(args.instance_id, args.data_root, config, input_queue, output_queue),
    )
    p.start()

    # 等待子进程完成
    p.join()

    print(f"子进程已退出，退出码: {p.exitcode}")
