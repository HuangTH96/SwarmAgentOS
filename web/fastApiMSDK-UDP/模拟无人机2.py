import asyncio
import json
import time
import math
import random
import signal

import websockets

# --- 配置 ---
# C++代码中的服务器地址
# SERVER_URL = "ws://192.168.1.111:8081/ws/psdk-client-M350"
# 为了方便本地测试，可以先用localhost
SERVER_URL = "ws://127.0.0.1:8081/ws/psdk-client-test2"

TELEMETRY_INTERVAL = 0.1  # 10Hz, 与C++代码一致
BATTERY_INTERVAL = 2.0  # 0.5Hz, 与C++代码一致


# --- 模拟状态变量 ---
class DroneState:
    def __init__(self):
        # 初始位置 (例如：旧金山)
        self.lat = 31.939
        self.lon = 118.7897
        self.height = 0.0
        self.is_flying = False

        # 运动模拟参数
        self.start_time = time.time()
        self.radius = 0.0001  # 模拟飞行的半径（纬度/经度单位）
        self.speed_factor = 0.5  # 模拟飞行速度

        # 电池
        self.battery_percent = 100.0
        self.battery_voltage = 22.8


# 创建一个全局的无人机状态实例
drone_state = DroneState()
# 创建一个事件来处理优雅退出
shutdown_event = asyncio.Event()


def handle_shutdown_signal(signum, frame):
    """处理Ctrl+C等信号，触发优雅退出"""
    print("\n[系统] 收到关闭信号，正在停止...")
    shutdown_event.set()


async def receive_messages(websocket):
    """一个持续运行的任务，用于接收和处理来自服务器的消息。"""
    print("[接收器] 启动，等待服务器命令...")
    try:
        async for message in websocket:
            print(f"\n<-- [收到命令] {message}\n")
            # 简单模拟对起飞/降落命令的响应
            if message == "takeoff":
                drone_state.is_flying = True
                drone_state.start_time = time.time()  # 重置飞行模拟时间
            elif message == "land":
                drone_state.is_flying = False
    except asyncio.CancelledError:
        print("[接收器] 任务被取消。")
    except Exception as e:
        print(f"[接收器] 发生错误: {e}")
    finally:
        print("[接收器] 已停止。")


async def send_data(websocket):
    """一个持续运行的任务，用于生成并发送模拟的遥测和电池数据。"""
    print("[发送器] 启动，开始发送数据...")
    last_battery_send_time = 0

    try:
        while not shutdown_event.is_set():
            current_time = time.time()

            # --- 更新模拟状态 ---
            if drone_state.is_flying:
                # 模拟在空中盘旋飞行
                elapsed_time = current_time - drone_state.start_time
                angle = elapsed_time * drone_state.speed_factor

                drone_state.lat += math.cos(angle) * drone_state.radius * 0.01
                drone_state.lon += math.sin(angle) * drone_state.radius * 0.01
                drone_state.height = 50.0 + math.sin(angle / 5) * 5  # 高度略有起伏
            else:
                # 停在地面
                drone_state.height = 0.2

                # 模拟电池消耗
            if drone_state.is_flying:
                drone_state.battery_percent -= 0.005
            drone_state.battery_percent = max(0, drone_state.battery_percent)

            # --- 1. 准备并发送遥测数据 (高频) ---
            telemetry_payload = {
                "data_type": "telemetry",
                "data": {
                    "latitude": drone_state.lat,
                    "longtitude": drone_state.lon,  # 保持C++代码中的拼写错误
                    "altitude": drone_state.height + 120,  # 假设海平面高度为120m
                    "height": drone_state.height,  # 相对起飞点高度
                    "speed": random.uniform(4.5, 5.5) if drone_state.is_flying else 0.0,
                    "head": (math.degrees(math.atan2(math.sin(elapsed_time * drone_state.speed_factor), math.cos(
                        elapsed_time * drone_state.speed_factor))) + 360) % 360 if 'elapsed_time' in locals() else 0,
                    "distance": random.uniform(100, 110) if drone_state.is_flying else 0.0,
                    "homeLocation": {"latitude": 37.7749, "longitude": -122.4194},
                    "quaternion": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},  # 简化四元数
                    "velocity": {
                        "x": random.uniform(-1, 1) if drone_state.is_flying else 0.0,
                        "y": random.uniform(-1, 1) if drone_state.is_flying else 0.0,
                        "z": random.uniform(-0.1, 0.1) if drone_state.is_flying else 0.0
                    },
                    "flystate": 0,
                    "angular_velocity": {"x": 0, "y": 0, "z": 0},
                    "acceleration": {"x": 0, "y": 0, "z": 0},
                    "position_vo": {"x": 0, "y": 0, "z": 0},
                    "position_latlon": {"x": 0, "y": 0, "z": 0},
                    "origin_is_set": True,
                    "origin_location": {"latitude": 37.7749, "longitude": -122.4194},
                    "ros_enabled": False,
                    "ros_xyz": {"x": 0, "y": 0, "z": 0}
                }
            }
            await websocket.send(json.dumps(telemetry_payload))
            # print(".", end="", flush=True) # 取消注释以查看每次发送的指示器

            # --- 2. 准备并发送电池数据 (低频) ---
            if current_time - last_battery_send_time > BATTERY_INTERVAL:
                last_battery_send_time = current_time
                battery_payload = {
                    "data_type": "battery",
                    "data": {
                        "batteries": [
                            {
                                "percent": int(drone_state.battery_percent),
                                "voltage": drone_state.battery_voltage - (100 - drone_state.battery_percent) * 0.05,
                                # 电压随电量下降
                                "connected": True,
                                "full_capacity": 5935.0,  # 模拟值
                                "remaining_capacity": 5935.0 * (drone_state.battery_percent / 100.0)
                            }
                        ]
                    }
                }
                await websocket.send(json.dumps(battery_payload))

            # 等待下一个发送周期
            await asyncio.sleep(TELEMETRY_INTERVAL)

    except asyncio.CancelledError:
        print("[发送器] 任务被取消。")
    except Exception as e:
        print(f"[发送器] 发生错误: {e}")
    finally:
        print("[发送器] 已停止。")


async def main_client():
    """主客户端函数，处理连接和任务管理。"""
    uri = f"{SERVER_URL}"

    while not shutdown_event.is_set():
        try:
            async with websockets.connect(uri) as websocket:
                print(f"[系统] 成功连接到 {uri}")

                # 创建并运行接收和发送任务
                receiver_task = asyncio.create_task(receive_messages(websocket))
                sender_task = asyncio.create_task(send_data(websocket))

                # 等待任一任务结束或收到关闭信号
                done, pending = await asyncio.wait(
                    [receiver_task, sender_task, shutdown_event.wait()],
                    return_when=asyncio.FIRST_COMPLETED
                )

                # 清理挂起的任务
                for task in pending:
                    task.cancel()
                    await task

        except websockets.exceptions.ConnectionClosed as e:
            print(f"[系统] 连接已关闭: {e}")
        except ConnectionRefusedError:
            print("[系统] 连接被拒绝。服务器是否正在运行？")
        except asyncio.CancelledError:
            print("[系统] 主任务被取消。")
            break
        except Exception as e:
            print(f"[系统] 发生未知错误: {e}")

        if not shutdown_event.is_set():
            print("[系统] 5秒后尝试重新连接...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    # 注册信号处理器
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        asyncio.run(main_client())
    except KeyboardInterrupt:
        # 这个是为了防止在 asyncio.run 之外按下 Ctrl+C 导致异常
        print("[系统] 程序被强制中断。")
    finally:
        print("[系统] 程序已退出。")