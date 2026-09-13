# app/manager.py
import asyncio
import json
import socket
import time
from fastapi import WebSocket
from typing import Dict, List, Any, Optional, Set, Tuple


class ConnectionManager:
    """管理所有活动的客户端状态和通信。"""

    def __init__(self, stream_pool_size: int = 10, client_timeout: int = 15, command_ack_timeout: float = 1.0,
                 command_retries: int = 3):
        """初始化连接管理器。"""
        self.active_clients: Dict[str, Dict[str, Any]] = {}
        self.control_websocket: Optional[WebSocket] = None
        self.local_ip: Optional[str] = self._fetch_local_ip()

        # RTMP推流池配置
        self.stream_pool_size = stream_pool_size
        self.available_stream_keys: Set[str] = {f"drone_rtmp_feed_{i}" for i in range(1, self.stream_pool_size + 1)}
        self.client_stream_assignments: Dict[str, str] = {}

        # 配置项
        self.CLIENT_TIMEOUT_SECONDS = client_timeout
        self.COMMAND_ACK_TIMEOUT_SECONDS = command_ack_timeout
        self.COMMAND_RETRIES = command_retries

        # 用于指令可靠性传输
        self.pending_acks: Dict[int, asyncio.Event] = {}
        self.command_counter = 0
        self.command_lock = asyncio.Lock()

        # <--- 关键修复: 添加一个属性来存储 transport 对象
        self.transport: Optional[asyncio.DatagramTransport] = None

        # 网络指标追踪
        self.network_metrics: Dict[str, Dict[str, Any]] = {}
        # 数据包统计
        self.packet_stats: Dict[str, Dict[str, Any]] = {}
        # 命令响应时间追踪
        self.command_latencies: Dict[str, List[float]] = {}

        print(f"ConnectionManager initialized. Local IP: {self.local_ip or '获取失败'}")

    def _fetch_local_ip(self) -> Optional[str]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception as e:
            print(f"Failed to fetch local IP: {e}")
            return "127.0.0.1"

    # <--- 关键修复: 新增方法用于保存 transport 对象
    def set_transport(self, transport: asyncio.DatagramTransport):
        """
        从主应用设置UDP transport对象。
        """
        self.transport = transport

    # --- UDP 数据处理 ---
    # <--- 修改: 移除了 transport 参数，因为它现在是类属性
    async def handle_udp_datagram(self, data: bytes, addr: Tuple[str, int]):
        """处理从UDP服务器收到的每一个数据报。"""
        try:
            message = data.decode('utf-8')
            payload = json.loads(message)
            client_id = payload.get("client_id")

            if not client_id:
                return

            # 检查是否有伪装IP
            fake_ip = payload.get("fake_ip")
            client_ip = fake_ip if fake_ip else addr[0]

            if client_id not in self.active_clients:
                self._register_client(client_id, addr, client_ip)
                await self.notify_control_panel_update()

            self.active_clients[client_id]["addr"] = addr
            self.active_clients[client_id]["ip"] = client_ip  # 更新IP（可能是伪装的）
            self.active_clients[client_id]["last_seen"] = time.time()

            # 更新数据包统计
            self.update_packet_stats(client_id, len(data))

            data_type = payload.get("data_type")
            if data_type == "telemetry":
                telemetry_dict = payload.get("data", {})
                self.update_telemetry(client_id, telemetry_dict)
                # 收到遥测数据也算作心跳响应
                if client_id in self.packet_stats:
                    self.packet_stats[client_id]["heartbeats_acked"] += 1
                await self.send_control_message({
                    "type": "telemetry_update", "client_id": client_id, "telemetry": telemetry_dict
                })
            elif data_type == "battery":
                # 收到电池数据也算作心跳响应
                if client_id in self.packet_stats:
                    self.packet_stats[client_id]["heartbeats_acked"] += 1
                await self.send_control_message({
                    "type": "battery_update", "client_id": client_id, "battery_info": payload.get("data", {})
                })
            elif payload.get("type") == "ack":
                command_id = payload.get("command_id")
                if command_id in self.pending_acks:
                    self.pending_acks[command_id].set()
                    # 记录ACK，用于丢包率计算
                    if client_id in self.packet_stats:
                        self.packet_stats[client_id]["heartbeats_acked"] += 1

        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print(f"无法解析来自 {addr} 的UDP数据: {e}")
        except Exception as e:
            print(f"处理UDP数据时发生未知错误: {e}")

    def update_packet_stats(self, client_id: str, packet_size: int):
        """更新数据包统计信息"""
        if client_id not in self.packet_stats:
            self.packet_stats[client_id] = {
                "total_received": 0,
                "total_sent": 0,
                "last_update": time.time(),
                "heartbeats_sent": 0,
                "heartbeats_acked": 0
            }
        
        stats = self.packet_stats[client_id]
        stats["total_received"] += packet_size
        stats["last_update"] = time.time()

    def _register_client(self, client_id: str, addr: Tuple[str, int], client_ip: str = None):
        """注册一个新的客户端。"""
        if client_ip is None:
            client_ip = addr[0]
        
        self.active_clients[client_id] = {
            "addr": addr, "ip": client_ip, "last_seen": time.time(),
            "telemetry": None, "stream_url": None, "origin_is_set": False,
            "origin_location": {"latitude": 0.0, "longitude": 0.0},
            "first_seen": time.time()  # 记录首次连接时间
        }
        
        # 初始化数据包统计
        self.packet_stats[client_id] = {
            "total_received": 0,
            "total_sent": 0,
            "last_update": time.time(),
            "heartbeats_sent": 0,
            "heartbeats_acked": 0
        }
        
        # 初始化命令时延列表
        self.command_latencies[client_id] = []
        
        print(f"发现新客户端 {client_id} (真实地址: {addr[0]}:{addr[1]}, 显示IP: {client_ip})")

    # --- 后台任务 ---
    async def run_background_tasks(self):
        await asyncio.gather(self._heartbeat_task(), self._cleanup_task())

    async def _heartbeat_task(self):
        """每秒向所有客户端发送心跳包。"""
        while True:
            await asyncio.sleep(1)  # 先 sleep，确保 transport 已经被设置
            heartbeat_message = json.dumps({"type": "heartbeat"}).encode('utf-8')

            # <--- 关键修复: 直接使用 self.transport
            if self.transport:
                for client_id, client_data in self.active_clients.items():
                    try:
                        self.transport.sendto(heartbeat_message, client_data["addr"])
                        # 统计发送的心跳包
                        if client_id in self.packet_stats:
                            self.packet_stats[client_id]["heartbeats_sent"] += 1
                            self.packet_stats[client_id]["total_sent"] += len(heartbeat_message)
                    except Exception as e:
                        print(f"发送心跳到 {client_data['addr']} 失败: {e}")

    async def _cleanup_task(self):
        """定期清理超时的客户端。"""
        while True:
            await asyncio.sleep(self.CLIENT_TIMEOUT_SECONDS / 2)
            now = time.time()
            disconnected_clients = [
                cid for cid, cdata in self.active_clients.items()
                if now - cdata.get("last_seen", 0) > self.CLIENT_TIMEOUT_SECONDS
            ]
            if disconnected_clients:
                for client_id in disconnected_clients:
                    self._disconnect_client(client_id)
                await self.notify_control_panel_update()

    def _disconnect_client(self, client_id: str):
        if client_id in self.active_clients:
            assigned_key = self.client_stream_assignments.pop(client_id, None)
            if assigned_key:
                self.available_stream_keys.add(assigned_key)
                print(f"Stream key '{assigned_key}' released by client {client_id}.")
            del self.active_clients[client_id]
            print(f"客户端 {client_id} 超时断开。")

    # --- 指令发送 ---
    async def send_personal_message(self, message_str: str, client_id: str) -> bool:
        client = self.active_clients.get(client_id)
        if not client:
            return False

        if not self.transport:
            print("错误: UDP transport 对象未设置，无法发送消息。")
            return False

        command_to_send = message_str
        is_rtmp_command = "start_rtmp_live" in message_str.strip().lower()

        # 特殊处理 RTMP 指令
        if message_str.strip().lower() == "start_rtmp_live":
            is_rtmp_command = True
            if not self.local_ip:
                print("错误: 无法启动RTMP直播，因为获取不到本机IP。")
                return False

            assigned_key = self.client_stream_assignments.get(client_id)
            if not assigned_key:
                if self.available_stream_keys:
                    assigned_key = self.available_stream_keys.pop()
                    self.client_stream_assignments[client_id] = assigned_key
                else:
                    print(f"错误: 没有可用的RTMP推流地址给客户端 {client_id}。")
                    return False

            rtmp_url = f"rtmp://{self.local_ip}:1935/{assigned_key}"
            self.active_clients[client_id]["stream_url"] = rtmp_url
            print(f"分配推流地址 '{rtmp_url}' 给客户端 {client_id}.")
            await self.notify_control_panel_update()
            command_to_send = f"start_rtmp_live {rtmp_url}"

        # 封装指令为JSON，并添加 command_id 以便跟踪ACK
        async with self.command_lock:
            self.command_counter += 1
            command_id = self.command_counter

        # 对于RTMP等简单文本指令，也将其包装成JSON以支持ACK
        if is_rtmp_command or not message_str.startswith('{'):
            final_payload = {"command": "text", "data": command_to_send, "command_id": command_id}
        else:  # 如果已经是JSON，则解析并注入command_id
            try:
                final_payload = json.loads(message_str)
                final_payload["command_id"] = command_id
            except json.JSONDecodeError:
                # 以防万一，如果解析失败，按文本处理
                final_payload = {"command": "text", "data": command_to_send, "command_id": command_id}

        message_bytes = json.dumps(final_payload).encode('utf-8')

        addr = client["addr"]
        ack_event = asyncio.Event()
        self.pending_acks[command_id] = ack_event
        
        # 记录命令发送时间
        command_send_time = time.time()

        print(f"发送指令 (ID: {command_id}) 到 {client_id}: {command_to_send}")

        try:
            for i in range(self.COMMAND_RETRIES):
                self.transport.sendto(message_bytes, addr)
                # 统计发送的字节数
                if client_id in self.packet_stats:
                    self.packet_stats[client_id]["total_sent"] += len(message_bytes)
                
                try:
                    await asyncio.wait_for(ack_event.wait(), timeout=self.COMMAND_ACK_TIMEOUT_SECONDS)
                    # 计算并记录时延
                    latency = (time.time() - command_send_time) * 1000  # 转换为毫秒
                    self.record_command_latency(client_id, latency)
                    print(f"收到指令 (ID: {command_id}) 的ACK，时延: {latency:.2f}ms")
                    return True
                except asyncio.TimeoutError:
                    print(f"指令 (ID: {command_id}) ACK超时，重试第 {i + 1}/{self.COMMAND_RETRIES} 次...")

            print(f"指令 (ID: {command_id}) 发送失败，所有重试均未收到ACK。")
            return False
        finally:
            del self.pending_acks[command_id]

    def record_command_latency(self, client_id: str, latency: float):
        """记录命令响应时延"""
        if client_id not in self.command_latencies:
            self.command_latencies[client_id] = []
        
        # 只保留最近50个时延值
        latencies = self.command_latencies[client_id]
        latencies.append(latency)
        if len(latencies) > 50:
            latencies.pop(0)

    # ... (其余所有方法，如 broadcast_to_clients, connect_control, 等等，都保持不变)
    async def broadcast_to_clients(self, message: str):
        tasks = [self.send_personal_message(message, client_id) for client_id in self.active_clients]
        await asyncio.gather(*tasks)

    async def connect_control(self, websocket: WebSocket):
        await websocket.accept()
        self.control_websocket = websocket
        print("控制面板已连接。")
        await self.send_control_message({"type": "client_list", "clients": self.get_active_clients_info()})

    def disconnect_control(self, websocket: WebSocket):
        if self.control_websocket is websocket:
            self.control_websocket = None
            print("控制面板已断开。")

    async def send_control_message(self, message: dict):
        if self.control_websocket:
            try:
                await self.control_websocket.send_json(message)
            except Exception:
                self.control_websocket = None

    async def notify_control_panel_update(self):
        await self.send_control_message({"type": "client_list_update", "clients": self.get_active_clients_info()})

    def get_active_clients_info(self) -> List[Dict[str, Any]]:
        return [{
            "id": client_id, "ip": client_data["ip"], "telemetry": client_data["telemetry"],
            "stream_url": client_data["stream_url"], "origin_is_set": client_data.get("origin_is_set", False),
            "origin_location": client_data.get("origin_location", {})
        } for client_id, client_data in self.active_clients.items()]

    def update_telemetry(self, client_id: str, telemetry_data: dict):
        if client_id in self.active_clients:
            self.active_clients[client_id]["telemetry"] = telemetry_data

    def get_telemetry(self, client_id: str) -> Optional[dict]:
        client = self.active_clients.get(client_id)
        return client.get("telemetry") if client else None

    def get_stream_key_for_client(self, client_id: str) -> Optional[str]:
        return self.client_stream_assignments.get(client_id)

    def calculate_network_metrics(self, client_id: str) -> Dict[str, Any]:
        """计算单个无人机的网络性能指标"""
        client = self.active_clients.get(client_id)
        if not client:
            return {}
        
        stats = self.packet_stats.get(client_id, {})
        latencies = self.command_latencies.get(client_id, [])
        
        current_time = time.time()
        first_seen = client.get("first_seen", current_time)
        last_update = stats.get("last_update", current_time)
        
        # 计算时间窗口（最近10秒）
        time_window = min(10.0, current_time - first_seen)
        if time_window <= 0:
            time_window = 1.0
        
        # 计算带宽 (Mbps)
        total_received = stats.get("total_received", 0)
        bandwidth = (total_received * 8) / (time_window * 1_000_000) if time_window > 0 else 0.0
        
        # 计算下行速率 (KB/s) - 从无人机接收的数据
        download_speed = (total_received / time_window / 1024) if time_window > 0 else 0.0
        
        # 计算上行速率 (KB/s) - 向无人机发送的数据
        total_sent = stats.get("total_sent", 0)
        upload_speed = (total_sent / time_window / 1024) if time_window > 0 else 0.0
        
        # 计算丢包率 (%)
        heartbeats_sent = stats.get("heartbeats_sent", 0)
        heartbeats_acked = stats.get("heartbeats_acked", 0)
        packet_loss = 0.0
        if heartbeats_sent > 0:
            packet_loss = ((heartbeats_sent - heartbeats_acked) / heartbeats_sent) * 100
            packet_loss = max(0.0, min(100.0, packet_loss))  # 限制在0-100%
        
        # 计算平均时延 (ms)
        latency = 0.0
        if latencies:
            latency = sum(latencies) / len(latencies)
        
        # 计算连接时间 (seconds)
        connection_time = int(current_time - first_seen)
        
        return {
            "client_id": client_id,
            "ip": client.get("ip", ""),
            "bandwidth": round(bandwidth, 2),
            "download_speed": round(download_speed, 2),
            "upload_speed": round(upload_speed, 2),
            "packet_loss": round(packet_loss, 2),
            "latency": round(latency, 2),
            "connection_time": connection_time
        }
    
    def get_all_network_metrics(self) -> List[Dict[str, Any]]:
        """获取所有活跃无人机的网络指标"""
        metrics = []
        for client_id in self.active_clients.keys():
            metric = self.calculate_network_metrics(client_id)
            if metric:
                metrics.append(metric)
        return metrics


# 创建一个全局的 ConnectionManager 实例
manager = ConnectionManager()
