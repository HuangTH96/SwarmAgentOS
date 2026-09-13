import asyncio
import json
import time
import math
import random
import signal

# --- 配置 ---
# C++代码中的服务器地址和端口
SERVER_HOST = "127.0.0.1"  # 为了方便本地测试, 改为localhost
# SERVER_HOST = "192.168.1.106" # 你的C++服务器IP
SERVER_PORT = 8081

# 客户端ID，必须与C++代码中的某个预期ID匹配或为新ID
CLIENT_ID = "psdk-client-SIMULATOR"

TELEMETRY_INTERVAL = 0.1  # 10Hz, 与C++代码一致
BATTERY_INTERVAL = 2.0  # 0.5Hz, 与C++代码一致


# --- 模拟状态变量 (与原版一致) ---
class DroneState:
    def __init__(self):
        # 初始位置 (南京)
        self.lat = 31.939
        self.lon = 118.7896
        self.height = 0.0
        self.is_flying = False

        # 运动模拟参数
        self.start_time = time.time()
        self.radius = 0.0001  # 模拟飞行的半径（纬度/经度单位）
        self.speed_factor = 0.5  # 模拟飞行速度
        self.heading = 0.0

        # 电池
        self.battery_percent = 100.0
        self.battery_voltage = 22.8

        # Swarm Type
        self.swarm_type = 0


# 创建一个全局的无人机状态实例
drone_state = DroneState()
# 创建一个事件来处理优雅退出
shutdown_event = asyncio.Event()


def handle_shutdown_signal(signum, frame):
    """处理Ctrl+C等信号，触发优雅退出"""
    print("\n[系统] 收到关闭信号，正在停止...")
    shutdown_event.set()


# =======================================================
# UDP通信的核心：Asyncio Protocol
# =======================================================
class DroneProtocol(asyncio.DatagramProtocol):
    def __init__(self, state, on_con_lost):
        self.transport = None
        self.state = state
        self.on_con_lost = on_con_lost

    def connection_made(self, transport):
        """当UDP端点准备好时调用"""
        self.transport = transport
        print(f"[系统] UDP套接字已创建，准备向 {SERVER_HOST}:{SERVER_PORT} 发送数据")

    def datagram_received(self, data, addr):
        """当收到UDP数据报时调用"""
        message = data.decode()
        print(f"\n<-- [收到命令] {message} from {addr}\n")

        # 尝试解析JSON命令 (例如服务器的ACK)
        try:
            cmd_json = json.loads(message)
            if cmd_json.get("type") == "ack":
                print(f"[ACK] 服务器已确认指令 ID: {cmd_json.get('command_id')}")
            return  # JSON消息通常不是需要无人机状态机响应的简单命令
        except json.JSONDecodeError:
            pass  # 不是JSON，继续作为简单文本命令处理

        # 简单模拟对起飞/降落命令的响应
        if message == "takeoff":
            self.state.is_flying = True
            self.state.start_time = time.time()  # 重置飞行模拟时间
        elif message == "land":
            self.state.is_flying = False
        # 模拟执行航线规划
        elif message.startswith('{"command":"execute_path"'):
            print("[模拟器] 收到航迹规划命令，开始模拟飞行...")
            self.state.is_flying = True
            self.state.swarm_type = 2  # 假设执行路径时类型变为2
            self.state.start_time = time.time()  # 重新开始盘旋

    def error_received(self, exc):
        """当发生OS级别的套接字错误时调用"""
        print(f"[错误] 套接字错误: {exc}")

    def connection_lost(self, exc):
        """当连接“丢失”（套接字关闭）时调用"""
        print("[系统] 套接字已关闭，正在停止...")
        self.on_con_lost.set_result(True)


# =======================================================


async def send_data(protocol, client_id):
    """一个持续运行的任务，用于生成并发送模拟的遥测和电池数据。"""
    print("[发送器] 启动，开始发送数据...")
    last_battery_send_time = 0

    # 等待protocol建立transport
    while protocol.transport is None:
        await asyncio.sleep(0.1)

    try:
        while not shutdown_event.is_set():
            current_time = time.time()

            # --- 更新模拟状态 (与原版一致) ---
            if drone_state.is_flying:
                elapsed_time = current_time - drone_state.start_time
                angle = elapsed_time * drone_state.speed_factor
                drone_state.lat += math.cos(angle) * drone_state.radius * 0.01
                drone_state.lon += math.sin(angle) * drone_state.radius * 0.01
                drone_state.height = 50.0 + math.sin(angle / 5) * 5
                drone_state.heading = (math.degrees(math.atan2(math.cos(angle), math.sin(angle))) + 360) % 360
            else:
                drone_state.height = 0.2
                drone_state.swarm_type = 0  # 降落后重置swarm_type

            if drone_state.is_flying:
                drone_state.battery_percent -= 0.005
            drone_state.battery_percent = max(0, drone_state.battery_percent)

            # --- 1. 准备并发送遥测数据 (高频) ---
            telemetry_payload = {
                "client_id": client_id,  # <-- 关键：添加客户端ID
                "data_type": "telemetry",
                "data": {
                    "latitude": drone_state.lat,
                    "longtitude": drone_state.lon,  # 保持C++代码中的拼写错误
                    "altitude": drone_state.height + 120,
                    "height": drone_state.height,
                    "speed": random.uniform(4.5, 5.5) if drone_state.is_flying else 0.0,
                    "head": drone_state.heading,
                    "distance": random.uniform(100, 110) if drone_state.is_flying else 0.0,
                    "homeLocation": {"latitude": 31.939, "longitude": 118.7896},
                    "quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
                    "velocity": {
                        "x": random.uniform(-1, 1) if drone_state.is_flying else 0.0,
                        "y": random.uniform(-1, 1) if drone_state.is_flying else 0.0,
                        "z": random.uniform(-0.1, 0.1) if drone_state.is_flying else 0.0
                    },
                    "flystate": 2 if drone_state.is_flying else 1,  # 模拟飞行/站立状态
                    "angular_velocity": {"x": 0, "y": 0, "z": 0},
                    "acceleration": {"x": 0, "y": 0, "z": 0},
                    "position_vo": {"x": 0, "y": 0, "z": 0},
                    "position_latlon": {"x": 10.5, "y": 20.2, "z": 50.1},  # 模拟的ENU坐标
                    "origin_is_set": True,
                    "origin_location": {"latitude": 31.939, "longitude": 118.7896},
                    "ros_enabled": True,  # 假设ROS总是启用
                    "ros_xyz": {"x": 10.0, "y": 20.0, "z": 50.0},
                    "swarm_type": drone_state.swarm_type
                }
            }
            payload_str = json.dumps(telemetry_payload)
            protocol.transport.sendto(payload_str.encode())

            # --- 2. 准备并发送电池数据 (低频) ---
            if current_time - last_battery_send_time > BATTERY_INTERVAL:
                last_battery_send_time = current_time
                battery_payload = {
                    "client_id": client_id,  # <-- 关键：添加客户端ID
                    "data_type": "battery",
                    "data": {"batteries": [{
                        "percent": int(drone_state.battery_percent),
                        "voltage": drone_state.battery_voltage - (100 - drone_state.battery_percent) * 0.05,
                        "connected": True,
                        "full_capacity": 5935.0,
                        "remaining_capacity": 5935.0 * (drone_state.battery_percent / 100.0)
                    }]}
                }
                payload_str = json.dumps(battery_payload)
                protocol.transport.sendto(payload_str.encode())
                # print("B", end="", flush=True) # 电池发送指示

            await asyncio.sleep(TELEMETRY_INTERVAL)

    except asyncio.CancelledError:
        print("[发送器] 任务被取消。")
    except Exception as e:
        print(f"[发送器] 发生错误: {e}")
    finally:
        print("[发送器] 已停止。")


async def main():
    """主函数，处理UDP端点创建和任务管理。"""
    print(f"[系统] 正在启动UDP模拟无人机 ({CLIENT_ID})...")
    loop = asyncio.get_running_loop()

    # 这个future用于在连接丢失时通知主循环退出
    on_con_lost = loop.create_future()

    # 创建UDP端点。它会立即开始监听，并准备好发送。
    # remote_addr指定了默认的发送目标地址。
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: DroneProtocol(drone_state, on_con_lost),
            remote_addr=(SERVER_HOST, SERVER_PORT)
        )
    except OSError as e:
        print(f"[错误] 创建UDP套接字失败: {e}")
        print("请检查网络配置或目标地址是否正确。")
        return

    # 创建并运行发送数据的任务
    sender_task = asyncio.create_task(send_data(protocol, CLIENT_ID))

    try:
        # 等待关闭信号或连接丢失
        await asyncio.wait(
            [shutdown_event.wait(), on_con_lost],
            return_when=asyncio.FIRST_COMPLETED
        )
    finally:
        print("[系统] 开始清理...")
        sender_task.cancel()
        # 等待任务完成取消
        await asyncio.gather(sender_task, return_exceptions=True)
        transport.close()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[系统] 程序已退出。")