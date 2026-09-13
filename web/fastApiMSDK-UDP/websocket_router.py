# app/websocket_router.py
"""
处理 Web 控制面板的 WebSocket 连接路由。
所有无人机通信现在通过UDP处理。
"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auth import get_user_from_token
from db import SessionLocal

# 注意: manager现在是从manager.py中直接导入的全局实例
from manager import manager

router = APIRouter()


@router.websocket("/ws/control")
async def websocket_control_endpoint(websocket: WebSocket):
    """
    此端点现在只服务于Web控制面板。
    """

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    async with SessionLocal() as db:
        user = await get_user_from_token(db, token)
    if not user:
        await websocket.close(code=1008)
        return

    await manager.connect_control(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                command_data = json.loads(data)
                client_id = command_data.get("client_id")
                payload = command_data.get("payload")

                if not (client_id and payload):
                    print(f"来自控制面板的无效指令: {data}")
                    continue

                # 将 payload 转换为字符串，因为 send_personal_message 期望的是字符串
                message_to_send = json.dumps(payload)

                if client_id == "all":
                    await manager.broadcast_to_clients(message_to_send)
                else:
                    await manager.send_personal_message(message_to_send, client_id)

            except json.JSONDecodeError:
                print(f"来自控制面板的非JSON消息: {data}")
            except Exception as e:
                print(f"处理控制面板指令时出错: {e}")

    except WebSocketDisconnect:
        print("控制面板连接正常关闭。")
    finally:
        manager.disconnect_control(websocket)
        print("控制面板清理完成。")

# 注意： /ws/{client_id} 端点已被移除，因为无人机不再通过WebSocket连接。