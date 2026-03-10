"""
OpenClaw WebSocket/HTTP 客户端
负责与 OpenClaw 网关通信
采用后台任务模式：持续监听 WebSocket，发送和接收完全分离
"""

import asyncio
import json
import time
import uuid
from typing import Any, Optional

import aiohttp
from astrbot.api import logger


class OpenClawClient:
    """OpenClaw 网关客户端（后台任务模式）"""

    def __init__(
        self,
        gateway_url: str,
        token: str = "",
        timeout: float = 30.0,
        connection_type: str = "websocket",
        idle_timeout: float = 1800.0,  # 空闲超时，默认30分钟
    ):
        self.gateway_url = gateway_url
        self.token = token
        self.timeout = timeout
        self.connection_type = connection_type
        self.idle_timeout = idle_timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._connected = False
        self._authenticated = False

        # 后台任务相关
        self._listen_task: Optional[asyncio.Task] = None
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._last_activity_time: float = time.time()
        self._lock = asyncio.Lock()

        # 流式响应累积（runId -> 累积的文本）
        self._stream_responses: dict[str, str] = {}

    async def connect(self) -> bool:
        """连接到 OpenClaw 网关"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            if self.connection_type == "websocket":
                return await self._connect_websocket()
            else:
                # HTTP 模式不需要持久连接
                return True

        except Exception as e:
            logger.error(f"[OpenClaw] 连接失败: {e}", exc_info=True)
            return False

    async def _connect_websocket(self) -> bool:
        """建立 WebSocket 连接并完成握手"""
        try:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self.ws = await self.session.ws_connect(
                self.gateway_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
            self._connected = True
            logger.info(f"[OpenClaw] WebSocket 连接成功: {self.gateway_url}")

            # 等待 connect.challenge 事件
            try:
                challenge_msg = await asyncio.wait_for(
                    self.ws.receive(),
                    timeout=5.0
                )

                if challenge_msg.type == aiohttp.WSMsgType.TEXT:
                    challenge_data = json.loads(challenge_msg.data)
                    logger.debug(f"[OpenClaw] 收到质询: {challenge_data}")

                    # 发送 connect 请求
                    connect_id = str(uuid.uuid4())
                    connect_request = {
                        "type": "req",
                        "id": connect_id,
                        "method": "connect",
                        "params": {
                            "minProtocol": 3,
                            "maxProtocol": 3,
                            "client": {
                                "id": "cli",
                                "version": "1.0.0",
                                "platform": "python",
                                "mode": "cli"
                            },
                            "role": "operator",
                            "scopes": ["operator.read", "operator.write"],
                            "caps": [],
                            "commands": [],
                            "permissions": {},
                            "auth": {"token": self.token} if self.token else {},
                            "locale": "zh-CN",
                            "userAgent": "astrbot/1.0.0",
                        }
                    }

                    await self.ws.send_json(connect_request)
                    logger.debug(f"[OpenClaw] 发送 connect 请求")

                    # 等待 hello-ok 响应
                    hello_msg = await asyncio.wait_for(
                        self.ws.receive(),
                        timeout=5.0
                    )

                    if hello_msg.type == aiohttp.WSMsgType.TEXT:
                        hello_data = json.loads(hello_msg.data)
                        if hello_data.get("type") == "res" and hello_data.get("ok"):
                            logger.info(f"[OpenClaw] 握手成功")
                            self._authenticated = True
                            return True
                        else:
                            logger.error(f"[OpenClaw] 握手失败: {hello_data}")
                            return False

            except asyncio.TimeoutError:
                logger.error(f"[OpenClaw] 握手超时")
                return False

            return True

        except Exception as e:
            logger.error(f"[OpenClaw] WebSocket 连接失败: {e}", exc_info=True)
            self._connected = False
            self._authenticated = False
            return False

    async def _ensure_listener_running(self) -> bool:
        """确保后台监听任务正在运行"""
        if self._listen_task and not self._listen_task.done():
            return True

        # 确保已连接
        if not self._connected or not self.ws or not self._authenticated:
            connected = await self.connect()
            if not connected:
                logger.error(f"[OpenClaw] 无法建立 WebSocket 连接")
                return False

        # 启动后台监听任务
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info(f"[OpenClaw] 后台监听任务已启动")
        return True

    async def _listen_loop(self) -> None:
        """后台监听循环，持续接收 WebSocket 消息"""
        logger.info(f"[OpenClaw] 开始后台监听循环")
        check_interval = 60  # 每分钟检查一次空闲超时

        while True:
            try:
                # 检查是否需要退出
                if self._should_stop():
                    logger.info(f"[OpenClaw] 空闲超时，停止后台监听")
                    break

                # 等待接收消息，带超时以便定期检查空闲状态
                try:
                    response = await asyncio.wait_for(
                        self.ws.receive(),
                        timeout=check_interval
                    )
                except asyncio.TimeoutError:
                    # 超时，检查是否需要退出
                    continue

                if response.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(response.data)
                    logger.debug(f"[OpenClaw] 后台收到消息: {data.get('type')} - {data.get('event') or data.get('id')}")

                    # 更新最后活动时间
                    self._last_activity_time = time.time()

                    # 处理消息
                    await self._handle_message(data)

                elif response.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"[OpenClaw] WebSocket 错误: {response.data}")
                    break
                elif response.type == aiohttp.WSMsgType.CLOSE:
                    logger.warning(f"[OpenClaw] WebSocket 连接已关闭")
                    break
                elif response.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning(f"[OpenClaw] WebSocket 已关闭")
                    break

            except asyncio.CancelledError:
                logger.info(f"[OpenClaw] 后台监听任务被取消")
                break
            except Exception as e:
                logger.error(f"[OpenClaw] 后台监听循环异常: {e}", exc_info=True)
                break

        # 清理
        self._listen_task = None
        await self._cleanup_pending_requests()

    def _should_stop(self) -> bool:
        """检查是否应该停止后台任务"""
        # 如果没有 pending 请求且空闲超时，则停止
        idle_time = time.time() - self._last_activity_time
        return (
            not self._pending_requests
            and idle_time >= self.idle_timeout
            and self._connected
        )

    async def _handle_message(self, data: dict) -> None:
        """处理接收到的消息，根据 request_id 分发给对应的 future"""
        msg_type = data.get("type")
        request_id = data.get("id")

        # 处理响应消息 (res)
        if msg_type == "res" and request_id:
            async with self._lock:
                if request_id in self._pending_requests:
                    future = self._pending_requests[request_id]
                    if not future.done():
                        # 解析响应
                        result = self._parse_response(data)
                        if result is not None:
                            # 检查是否是 accepted 状态
                            if result.get("status") == "accepted":
                                run_id = result.get("run_id")
                                if run_id:
                                    # 移除旧的 request_id，创建新的 runId future
                                    self._pending_requests.pop(request_id)
                                    # 将旧的 future 转移到新的 runId
                                    self._pending_requests[run_id] = future
                                    logger.debug(f"[OpenClaw] future 已转移: {request_id} -> {run_id}")
                            else:
                                # 有最终结果，设置 future
                                self._pending_requests.pop(request_id)
                                future.set_result(result)
            return

        # 处理事件消息（可能包含流式响应）
        if msg_type == "event":
            event_name = data.get("event")
            payload = data.get("payload", {})

            # 检查是否是 agent 相关事件
            if event_name and "agent" in event_name:
                run_id = payload.get("runId")
                stream_type = payload.get("stream")

                # 累积流式文本（stream: assistant）
                if stream_type == "assistant" and run_id:
                    data_obj = payload.get("data", {})
                    delta_text = data_obj.get("text") or ""
                    if delta_text:
                        async with self._lock:
                            current = self._stream_responses.get(run_id, "")
                            self._stream_responses[run_id] = current + delta_text
                        logger.debug(f"[OpenClaw] 累积流式文本: {delta_text[:30]}...")

                # 检查是否结束（lifecycle: end），此时返回累积的完整响应
                if stream_type == "lifecycle":
                    lifecycle_data = payload.get("data", {})
                    if lifecycle_data.get("phase") == "end" and run_id:
                        async with self._lock:
                            full_reply = self._stream_responses.pop(run_id, "")
                            if run_id in self._pending_requests:
                                future = self._pending_requests[run_id]
                                if not future.done() and full_reply:
                                    logger.info(f"[OpenClaw] 流式响应完成: {full_reply[:50]}...")
                                    future.set_result({"reply": full_reply, "payload": payload})
                                # 移除 pending 请求
                                self._pending_requests.pop(run_id, None)
                        logger.debug(f"[OpenClaw] 收到结束事件")

    def _parse_response(self, data: dict) -> Optional[dict[str, Any]]:
        """解析响应消息"""
        if data.get("type") != "res":
            return None

        if not data.get("ok"):
            error = data.get("error", {})
            logger.error(f"[OpenClaw] 请求失败: {error}")
            return None

        payload = data.get("payload", {})
        status = payload.get("status")

        # 如果是 accepted，需要继续等待（让 _handle_message 处理 future 转换）
        if status == "accepted":
            logger.debug(f"[OpenClaw] 请求已接受，等待响应中...")
            # 返回特殊标记，让 _handle_message 创建新的 future
            return {"status": "accepted", "run_id": payload.get("runId")}

        # 状态为 ok/completed，提取最终回复
        if status in ("ok", "completed"):
            result = payload.get("result", {})
            payloads = result.get("payloads", [])
            if payloads and isinstance(payloads[0], dict):
                reply_text = payloads[0].get("text") or ""
                if reply_text:
                    logger.info(f"[OpenClaw] 收到最终回复: {reply_text[:50]}...")
                    return {"reply": reply_text, "payload": payload}

        # 备用路径提取
        reply_text = payload.get("text") or payload.get("message") or payload.get("content") or ""
        return {"reply": reply_text, "payload": payload}

    def _parse_event_response(self, data: dict) -> Optional[dict[str, Any]]:
        """解析事件消息中的响应"""
        payload = data.get("payload", {})
        event_name = data.get("event")

        # 从 data.text 提取
        reply_text = ""
        data_obj = payload.get("data", {})
        if isinstance(data_obj, dict):
            reply_text = data_obj.get("text") or ""

        # 备用路径
        if not reply_text:
            reply_text = payload.get("text") or ""

        if reply_text:
            return {"reply": reply_text, "payload": payload, "event": event_name}

        return None

    async def _cleanup_pending_requests(self) -> None:
        """清理所有 pending 的请求"""
        async with self._lock:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_result(None)
            self._pending_requests.clear()

    async def send_message(
        self,
        message: str,
        sender_id: str,
        session_id: str,
        platform: str = "unknown",
    ) -> Optional[dict[str, Any]]:
        """
        发送消息到 OpenClaw 网关并等待响应
        后台任务模式：发送不等，异步等待响应

        Args:
            message: 用户消息内容
            sender_id: 发送者 ID
            session_id: 会话 ID
            platform: 消息平台

        Returns:
            OpenClaw 的响应，包含 reply 字段
        """
        if self.connection_type == "websocket":
            return await self._send_message_ws(message, sender_id, session_id, platform)
        else:
            return await self._send_message_http(message, sender_id, session_id, platform)

    async def _send_message_ws(
        self,
        message: str,
        sender_id: str,
        session_id: str,
        platform: str,
    ) -> Optional[dict[str, Any]]:
        """通过 WebSocket 发送消息（后台任务模式）"""
        try:
            # 确保后台监听任务正在运行
            if not await self._ensure_listener_running():
                return None

            # 构建请求
            request_id = str(uuid.uuid4())
            request_data = {
                "type": "req",
                "id": request_id,
                "method": "agent",
                "params": {
                    "message": message,
                    "sessionKey": session_id,
                    "idempotencyKey": request_id,
                },
            }

            # 创建 future 用于接收响应
            future = asyncio.get_running_loop().create_future()

            # 注册到 pending 请求
            async with self._lock:
                self._pending_requests[request_id] = future
                self._last_activity_time = time.time()

            # 发送请求
            await self.ws.send_json(request_data)
            logger.debug(f"[OpenClaw] 发送消息: {request_data}")

            # 等待响应（带超时）
            try:
                result = await asyncio.wait_for(future, timeout=self.timeout)
                return result
            except asyncio.TimeoutError:
                logger.error(f"[OpenClaw] 等待响应超时 ({self.timeout}s)")
                # 清理 pending 请求
                async with self._lock:
                    self._pending_requests.pop(request_id, None)
                return None

        except Exception as e:
            logger.error(f"[OpenClaw] WebSocket 发送消息失败: {e}", exc_info=True)
            return None

    async def _send_message_http(
        self,
        message: str,
        sender_id: str,
        session_id: str,
        platform: str,
    ) -> Optional[dict[str, Any]]:
        """通过 HTTP 发送消息"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            # 构建请求
            request_id = str(uuid.uuid4())
            request_data = {
                "type": "req",
                "id": request_id,
                "method": "agent",
                "params": {
                    "message": message,
                    "sessionKey": session_id,
                    "idempotencyKey": request_id,
                },
            }

            # 发送请求
            async with self.session.post(
                f"{self.gateway_url}/api/agent",
                json=request_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        payload = data.get("payload", {})
                        reply_text = ""
                        if isinstance(payload, dict):
                            reply_text = payload.get("text") or payload.get("message") or payload.get("content") or ""
                        return {"reply": reply_text, "payload": payload}
                    else:
                        logger.error(f"[OpenClaw] HTTP 请求失败: {data.get('error')}")
                        return None
                else:
                    logger.error(f"[OpenClaw] HTTP 响应错误: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"[OpenClaw] HTTP 发送消息失败: {e}", exc_info=True)
            return None

    async def health_check(self) -> bool:
        """检查 OpenClaw 网关健康状态"""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            async with self.session.get(
                f"{self.gateway_url}/health",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"[OpenClaw] 健康检查失败: {e}")
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        try:
            # 取消后台任务
            if self._listen_task:
                self._listen_task.cancel()
                try:
                    await self._listen_task
                except asyncio.CancelledError:
                    pass
                self._listen_task = None

            # 清理 pending 请求
            await self._cleanup_pending_requests()

            # 关闭连接
            if self.ws:
                await self.ws.close()
            if self.session:
                await self.session.close()
        except Exception as e:
            logger.error(f"[OpenClaw] 断开连接时出错: {e}")
        finally:
            self._connected = False
            self.ws = None
            self.session = None

    @property
    def is_connected(self) -> bool:
        """检查是否已连接并认证"""
        return self._connected and self._authenticated
