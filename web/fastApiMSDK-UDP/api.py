# app/api.py
"""
处理所有 RESTful API 请求的路由。
"""
import json
import math

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import httpx
from websocket_router import manager  # 从 websockets 模块导入共享的 manager 实例
from models import (
    Command, 
    RoutePlanningRequest,
    RouteWaypointModel,
    RouteModel,
    RoutePlanningResponse,
    ValidationError,
    ValidationResponse,
    MissionSaveRequest,
    MissionSaveResponse,
    ConversationAssociateRequest,
    TaskPlanEnhanceRequest,
    TaskPlanEnhanceResponse
)
import os
from openai import OpenAI
from pydantic import BaseModel
from auth import get_current_user
from db import User, AiTaskConversation, get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import AiTaskMessage
from geocoding_service import GeocodingService
from task_plan_enhancer import TaskPlanEnhancer
import logging

# RTSP直播配置
MEDIAMTX_HOST = "localhost"
MEDIAMTX_HLS_PORT = 8888
MEDIAMTX_WEBRTC_PORT = 8889
# STREAM_PATH_NAME = "drone_rtmp_feed" # REMOVED: 不再需要静态的流名称

router = APIRouter(prefix="/api")  # 为所有路由添加 /api 前缀

# 初始化日志
logger = logging.getLogger(__name__)

# 初始化地理编码服务
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "2f113e143536f78924fec4887a9ddccd")
geocoding_service = None
task_plan_enhancer = None

if AMAP_API_KEY:
    try:
        geocoding_service = GeocodingService(api_key=AMAP_API_KEY)
        task_plan_enhancer = TaskPlanEnhancer(geocoding_service)
        logger.info("Geocoding service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize geocoding service: {e}")
else:
    logger.warning("AMAP_API_KEY not configured, geocoding功能 disabled")

# 为 LLM 请求定义 Pydantic 模型
class LLMPrompt(BaseModel):
    prompt: str

# 初始化 DeepSeek 客户端
# 从环境变量中安全地读取 API 密钥
api_key = "sk-bd7fa39f9d5c4618b60a55cd2246773c"
llm_client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# 这是给大模型的“系统提示”，用于指导它如何正确地格式化输出
SYSTEM_PROMPT = """
你是一个专门用于无人机控制的AI助手。
你的任务是将用户的自然语言指令转换为一行结构化的命令代码。
命令格式为：type x y z yaw time

- type: 指令类型。'p' 代表位置指令 (position)，'v' 代表速度指令 (velocity)。
- x, y, z: 分别代表三个轴向的值。单位是米(m)或米每秒(m/s)。
- yaw: 偏航角（旋转）。单位是度(°)。
- time: 持续时间。仅对速度指令('v')有效。单位是秒(s)。

速度指令坐标系定义:
- +x: 
- +y: 无人机机头朝向（向前）
- +z: 无人机上方（向上）
- yaw: 逆时针为正

位置指令坐标系定义:
- +x: 无人机机头朝向（向前）
- +y: 无人机右侧
- +z: 无人机上方（向上）
- yaw: 逆时针为正

例子:
- 用户: "向前飞10米" -> p 10 0 0 0 0
- 用户: "向左飞5米，然后向上飞2米" -> p 0 -5 2 0 0 
- 用户: "原地逆时针旋转90度" -> p 0 0 0 90 0
- 用户: "以每秒2米的速度向前飞3秒" -> v 0 2 0 0 3
- 用户: "以1m/s的速度下降2秒" -> v 0 0 -1 0 2

你的回答必须且只能是这一行结构化的命令代码，不要包含任何额外的解释、文字或代码块标记。
"""


@router.post("/process-llm-command")
async def process_llm_command(llm_prompt: LLMPrompt, current_user: User = Depends(get_current_user)):
    """
    接收用户的自然语言指令，调用大模型处理，并返回结构化指令。
    """
    if not llm_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service is not configured on the server. (DEEPSEEK_API_KEY is missing)"
        )

    try:
        response = llm_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": llm_prompt.prompt},
            ],
            stream=False,
            temperature=0.1  # 使用较低的温度以获得更稳定、可预测的输出
        )

        command_string = response.choices[0].message.content.strip()
        print(response)
        # 基本的格式验证
        parts = command_string.split()
        if not (len(parts) == 6 and parts[0] in ['p', 'v']):
            raise ValueError("LLM returned an invalid command format.")

        print(f"LLM processed: '{llm_prompt.prompt}' -> '{command_string}'")
        return {"command": command_string}

    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process command with LLM: {e}"
        )

#  端点现在接收 client_id 作为路径参数
@router.post("/webrtc-stream/{client_id}")
async def get_webrtc_stream(client_id: str, request: Request, current_user: User = Depends(get_current_user)):
    """
    处理特定客户端的 WebRTC 信令交换。
    1. 从前端接收 SDP Offer 和 client_id。
    2. 使用 manager 查询 client_id 对应的推流路径 (stream_path)。
    3. 将 Offer POST 到 mediamtx 的动态 WebRTC API 地址。
    4. 从 mediamtx 接收 SDP Answer。
    5. 将 Answer 返回给前端。
    """
    # NEW: 使用 manager 查询推流路径
    stream_path = manager.get_stream_key_for_client(client_id)

    # NEW: 如果客户端不存在或未开始推流，则返回错误
    if not stream_path:
        raise HTTPException(
            status_code=404,
            detail=f"Stream for client '{client_id}' not found. The client may be disconnected or has not started streaming."
        )

    # 1. Mediamtx WebRTC API 地址 (现在是动态的)
    mediamtx_api_url = f"http://{MEDIAMTX_HOST}:{MEDIAMTX_WEBRTC_PORT}/{stream_path}/whep"
    print(f"Proxying WebRTC request for client '{client_id}' to: {mediamtx_api_url}") # 增加日志，方便调试

    # 2. 从前端请求体中获取 SDP Offer
    offer_sdp = await request.body()
    if not offer_sdp:
        raise HTTPException(status_code=400, detail="SDP offer is missing.")

    # 3. 使用 httpx 将 Offer 转发给 mediamtx
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                mediamtx_api_url,
                content=offer_sdp,
                headers={"Content-Type": "application/sdp"},
                timeout=10.0
            )

        response.raise_for_status()

        # 4. 成功，返回从 mediamtx 获取的 SDP Answer
        # 注意：这里我们不再需要返回一个JSON对象，WHEP协议可以直接代理响应。
        # 直接返回 mediamtx 的响应，包括它的 body 和 headers，这样更符合 WHEP 规范。
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Cannot connect to mediamtx WebRTC service: {exc}"
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Mediamtx returned an error for stream '{stream_path}': {exc.response.text}"
        )

# --- 其他 API 端点保持不变 ---

@router.get("/clients")
async def get_clients(current_user: User = Depends(get_current_user)):
    return {"clients": manager.get_active_clients_info()}

@router.get("/telemetry/{client_id}")
async def get_latest_telemetry(client_id: str, current_user: User = Depends(get_current_user)):
    telemetry = manager.get_telemetry(client_id)
    if telemetry:
        return {"client_id": client_id, "telemetry": telemetry}
    raise HTTPException(status_code=404, detail=f"Telemetry not found for client '{client_id}'.")

@router.post("/send-command")
async def send_command_to_client(command: Command, current_user: User = Depends(get_current_user)):
    """
    通过 API 向指定客户端发送指令。
    此函数现在会调用 manager 中基于UDP的、可靠的发送方法。
    """
    # Manager 的接口保持不变，但内部实现已改为UDP
    success = await manager.send_personal_message(command.command, command.client_id)
    if success:
        return {"status": "success", "message": f"Command sent to {command.client_id} and acknowledged."}
    else:
        # 失败现在意味着所有重试都超时了
        raise HTTPException(status_code=404, detail=f"Client '{command.client_id}' not found or command failed to be acknowledged after retries.")


# AI 任务对话记录 API
@router.post("/ai-task-conversations")
async def save_ai_task_message(
    message: AiTaskMessage,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """保存 AI 任务对话消息到数据库"""
    try:
        conversation = AiTaskConversation(
            user_id=current_user.id,
            role=message.role,
            content=message.content,
            task_plan=json.dumps(message.task_plan, ensure_ascii=False) if message.task_plan else None,
            mission_id=message.mission_id  # 添加任务 ID 关联
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        
        return {
            "status": "success",
            "message": "对话记录已保存",
            "id": conversation.id
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存对话记录失败: {str(e)}"
        )


@router.get("/ai-task-conversations")
async def get_ai_task_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 100
):
    """获取当前用户的 AI 任务对话历史记录"""
    try:
        result = await db.execute(
            select(AiTaskConversation)
            .where(AiTaskConversation.user_id == current_user.id)
            .order_by(AiTaskConversation.timestamp.asc())
            .limit(limit)
        )
        conversations = result.scalars().all()
        
        messages = []
        for conv in conversations:
            messages.append({
                "id": conv.id,
                "role": conv.role,
                "content": conv.content,
                "task_plan": json.loads(conv.task_plan) if conv.task_plan else None,
                "timestamp": conv.timestamp.strftime("%H:%M")
            })
        
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取对话记录失败: {str(e)}"
        )


@router.delete("/ai-task-conversations")
async def clear_ai_task_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """清空当前用户的 AI 任务对话历史记录"""
    try:
        result = await db.execute(
            select(AiTaskConversation)
            .where(AiTaskConversation.user_id == current_user.id)
        )
        conversations = result.scalars().all()
        
        for conv in conversations:
            await db.delete(conv)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "对话记录已清空"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空对话记录失败: {str(e)}"
        )


@router.delete("/ai-task-conversations/mission/{mission_id}")
async def clear_mission_conversations(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """清空特定任务的对话历史记录"""
    try:
        result = await db.execute(
            select(AiTaskConversation)
            .where(
                AiTaskConversation.user_id == current_user.id,
                AiTaskConversation.mission_id == mission_id
            )
        )
        conversations = result.scalars().all()
        
        for conv in conversations:
            await db.delete(conv)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"任务 {mission_id} 的对话记录已清空"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空任务对话记录失败: {str(e)}"
        )


@router.post("/ai-task-conversations/associate")
async def associate_conversations_with_mission(
    request: ConversationAssociateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """将对话历史关联到任务"""
    try:
        # 验证任务是否属于当前用户
        from db import Mission
        result = await db.execute(
            select(Mission).where(
                Mission.id == request.mission_id,
                Mission.user_id == current_user.id
            )
        )
        mission = result.scalar_one_or_none()
        
        if not mission:
            raise HTTPException(status_code=404, detail="任务不存在或无权访问")
        
        # 更新对话记录的 mission_id
        for conv_id in request.conversation_ids:
            result = await db.execute(
                select(AiTaskConversation).where(
                    AiTaskConversation.id == conv_id,
                    AiTaskConversation.user_id == current_user.id
                )
            )
            conversation = result.scalar_one_or_none()
            
            if conversation:
                conversation.mission_id = request.mission_id
        
        await db.commit()
        
        return {
            "status": "success",
            "message": f"已关联 {len(request.conversation_ids)} 条对话记录到任务"
        }
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"关联对话记录失败: {str(e)}"
        )


@router.get("/ai-task-conversations/mission/{mission_id}")
async def get_mission_conversations(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取指定任务的对话历史"""
    try:
        # 验证任务是否属于当前用户
        from db import Mission
        result = await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.user_id == current_user.id
            )
        )
        mission = result.scalar_one_or_none()
        
        if not mission:
            raise HTTPException(status_code=404, detail="任务不存在或无权访问")
        
        # 查询该任务的对话历史
        result = await db.execute(
            select(AiTaskConversation)
            .where(
                AiTaskConversation.user_id == current_user.id,
                AiTaskConversation.mission_id == mission_id
            )
            .order_by(AiTaskConversation.timestamp.asc())
        )
        conversations = result.scalars().all()
        
        messages = []
        for conv in conversations:
            messages.append({
                "id": conv.id,
                "role": conv.role,
                "content": conv.content,
                "taskPlan": json.loads(conv.task_plan) if conv.task_plan else None,
                "timestamp": conv.timestamp.strftime("%H:%M"),
                "mission_id": conv.mission_id
            })
        
        return {"messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务对话历史失败: {str(e)}"
        )


# AI API 配置管理
@router.get("/ai-config")
async def get_ai_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户的 AI API 配置"""
    try:
        result = await db.execute(
            select(User).where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "ai_api_provider": user.ai_api_provider,
            "ai_api_key": user.ai_api_key,
            "ai_api_endpoint": user.ai_api_endpoint
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取 AI 配置失败: {str(e)}"
        )


@router.post("/ai-config")
async def save_ai_config(
    config: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """保存当前用户的 AI API 配置"""
    try:
        result = await db.execute(
            select(User).where(User.id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 更新配置
        user.ai_api_provider = config.get('ai_api_provider')
        user.ai_api_key = config.get('ai_api_key')
        user.ai_api_endpoint = config.get('ai_api_endpoint')
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "AI 配置已保存"
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存 AI 配置失败: {str(e)}"
        )



# 航迹规划 API
@router.post("/route-planning/plan")
async def plan_route(
    request: RoutePlanningRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    航迹规划 API（动态版本）
    直接使用前端传递的坐标点进行路径规划，不依赖预定义的CSV文件
    """
    try:
        # 导入动态路径规划器
        from utils_route_dynamic import DynamicRoutePlanner
        
        # 创建规划器实例
        planner = DynamicRoutePlanner()
        
        # 准备起点数据
        start_point = {
            "name": request.start_point.name or "Start",
            "lat": request.start_point.latitude,
            "lng": request.start_point.longitude
        }
        
        # 准备终点数据
        end_point = {
            "name": request.end_point.name or "End",
            "lat": request.end_point.latitude,
            "lng": request.end_point.longitude
        }
        
        # 准备途经点数据
        waypoints = []
        for wp in request.waypoints:
            waypoints.append({
                "name": wp.name or f"Waypoint_{len(waypoints)+1}",
                "lat": wp.latitude,
                "lng": wp.longitude
            })
        
        # 准备禁飞区数据（支持圆形和矩形）
        no_fly_zones = []
        for zone in request.no_fly_zones:
            zone_data = {
                "name": zone.name or f"NoFlyZone_{len(no_fly_zones)+1}",
                "shape": zone.shape or "circle"
            }
            
            if zone.shape == "rectangle" and zone.bounds:
                # 矩形禁飞区
                zone_data["bounds"] = {
                    "north": zone.bounds.get("north"),
                    "south": zone.bounds.get("south"),
                    "east": zone.bounds.get("east"),
                    "west": zone.bounds.get("west")
                }
            elif zone.center and zone.radius:
                # 圆形禁飞区
                zone_data["center"] = {
                    "lat": zone.center.latitude,
                    "lng": zone.center.longitude
                }
                zone_data["radius"] = zone.radius
            else:
                # 跳过无效的禁飞区
                print(f"[警告] 跳过无效禁飞区: {zone.name}")
                continue
            
            no_fly_zones.append(zone_data)
        
        print(f"\n[路径规划] 开始规划")
        print(f"  起点: {start_point['name']} ({start_point['lat']}, {start_point['lng']})")
        print(f"  终点: {end_point['name']} ({end_point['lat']}, {end_point['lng']})")
        print(f"  途经点数量: {len(waypoints)}")
        print(f"  禁飞区数量: {len(no_fly_zones)}")
        print(f"  无人机数量: {request.number_uavs}")
        print(f"  任务类型: {request.mission_type}")
        
        # 调用算法规划路径
        routes, points = planner.find_optimal_routes(
            start_point=start_point,
            end_point=end_point,
            waypoints=waypoints,
            num_uavs=request.number_uavs,
            no_fly_zones=no_fly_zones
        )
        
        # 转换结果为响应格式
        route_responses = []
        for uav_index, route in enumerate(routes):
            waypoints_list = []
            total_distance = 0
            
            for i, point_idx in enumerate(route):
                if point_idx < len(points):
                    point = points[point_idx]
                    waypoint = RouteWaypointModel(
                        latitude=point['latitude'],
                        longitude=point['longitude'],
                        altitude=50.0,
                        sequence=i
                    )
                    waypoints_list.append(waypoint)
                    
                    # 计算距离
                    if i > 0 and route[i-1] < len(points):
                        prev_point = points[route[i-1]]
                        from haversine import haversine
                        dist = haversine(
                            (prev_point['latitude'], prev_point['longitude']),
                            (point['latitude'], point['longitude'])
                        ) * 1000
                        total_distance += dist
            
            # 估算飞行时间（假设平均速度 5 m/s）
            estimated_time = total_distance / 5.0 if total_distance > 0 else 0
            
            route_response = RouteModel(
                uav_id=uav_index,
                waypoints=waypoints_list,
                total_distance=total_distance,
                estimated_time=estimated_time
            )
            route_responses.append(route_response)
        
        # 计算总距离
        total_distance_sum = sum(route.total_distance for route in route_responses)
        
        print(f"[路径规划] 完成")
        print(f"  生成路径数: {len(route_responses)}")
        print(f"  总飞行距离: {total_distance_sum:.0f}米")
        
        return RoutePlanningResponse(
            routes=route_responses,
            total_distance=total_distance_sum,
            success=True,
            message="航迹规划成功"
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"航迹规划失败: {str(e)}"
        )


@router.post("/route-planning/validate")
async def validate_parameters(
    request: RoutePlanningRequest,
    current_user: User = Depends(get_current_user)
):
    """
    参数验证 API
    验证起点、终点、禁飞区、航点等参数的有效性
    """
    try:
        errors = []
        
        # 验证起点和终点
        if request.start_point.lat < -90 or request.start_point.lat > 90:
            errors.append(ValidationError(
                field="start_point.lat",
                message="起点纬度必须在 -90 到 90 之间"
            ))
        
        if request.start_point.lng < -180 or request.start_point.lng > 180:
            errors.append(ValidationError(
                field="start_point.lng",
                message="起点经度必须在 -180 到 180 之间"
            ))
        
        if request.end_point.lat < -90 or request.end_point.lat > 90:
            errors.append(ValidationError(
                field="end_point.lat",
                message="终点纬度必须在 -90 到 90 之间"
            ))
        
        if request.end_point.lng < -180 or request.end_point.lng > 180:
            errors.append(ValidationError(
                field="end_point.lng",
                message="终点经度必须在 -180 到 180 之间"
            ))
        
        # 验证无人机数量
        if request.num_uavs < 1 or request.num_uavs > 10:
            errors.append(ValidationError(
                field="num_uavs",
                message="无人机数量必须在 1 到 10 之间"
            ))
        
        # 验证禁飞区
        for i, zone in enumerate(request.no_fly_zones):
            if zone.center.lat < -90 or zone.center.lat > 90:
                errors.append(ValidationError(
                    field=f"no_fly_zones[{i}].center.lat",
                    message=f"禁飞区 {i+1} 中心纬度必须在 -90 到 90 之间"
                ))
            
            if zone.center.lng < -180 or zone.center.lng > 180:
                errors.append(ValidationError(
                    field=f"no_fly_zones[{i}].center.lng",
                    message=f"禁飞区 {i+1} 中心经度必须在 -180 到 180 之间"
                ))
            
            if zone.radius < 10 or zone.radius > 10000:
                errors.append(ValidationError(
                    field=f"no_fly_zones[{i}].radius",
                    message=f"禁飞区 {i+1} 半径必须在 10 到 10000 米之间"
                ))
        
        # 验证航点
        for i, waypoint in enumerate(request.waypoints):
            if waypoint.lat < -90 or waypoint.lat > 90:
                errors.append(ValidationError(
                    field=f"waypoints[{i}].lat",
                    message=f"航点 {i+1} 纬度必须在 -90 到 90 之间"
                ))
            
            if waypoint.lng < -180 or waypoint.lng > 180:
                errors.append(ValidationError(
                    field=f"waypoints[{i}].lng",
                    message=f"航点 {i+1} 经度必须在 -180 到 180 之间"
                ))
        
        return ValidationResponse(
            valid=len(errors) == 0,
            errors=errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"参数验证失败: {str(e)}"
        )


@router.post("/route-planning/save")
async def save_mission(
    request: MissionSaveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    保存任务配置 API
    保存任务配置到数据库，包括起点、终点、禁飞区、航点、生成的航迹等
    """
    try:
        from db import Mission, MissionNoFlyZone, MissionWaypoint, MissionRoute
        
        # 创建任务记录
        mission = Mission(
            user_id=current_user.id,
            name=request.name,
            start_point_lat=str(request.start_point.get('lat', 0)),
            start_point_lng=str(request.start_point.get('lng', 0)),
            start_point_name=request.start_point.get('name', ''),
            end_point_lat=str(request.end_point.get('lat', 0)),
            end_point_lng=str(request.end_point.get('lng', 0)),
            end_point_name=request.end_point.get('name', ''),
            num_uavs=request.num_uavs,
            mission_type=request.mission_type
        )
        db.add(mission)
        await db.flush()  # 获取 mission.id
        
        # 保存禁飞区
        for zone in request.no_fly_zones:
            nofly_zone = MissionNoFlyZone(
                mission_id=mission.id,
                center_lat=str(zone.get('center', {}).get('lat', 0)),
                center_lng=str(zone.get('center', {}).get('lng', 0)),
                radius=zone.get('radius', 0),
                name=zone.get('name', '')
            )
            db.add(nofly_zone)
        
        # 保存航点
        for waypoint in request.waypoints:
            mission_waypoint = MissionWaypoint(
                mission_id=mission.id,
                lat=str(waypoint.get('lat', 0)),
                lng=str(waypoint.get('lng', 0)),
                name=waypoint.get('name', ''),
                sequence=waypoint.get('sequence', 0)
            )
            db.add(mission_waypoint)
        
        # 保存生成的航迹
        for route in request.routes:
            waypoints_json = json.dumps([
                {
                    "lat": wp.get('lat', 0),
                    "lng": wp.get('lng', 0),
                    "name": wp.get('name', ''),
                    "sequence": wp.get('sequence', 0)
                }
                for wp in route.get('waypoints', [])
            ], ensure_ascii=False)
            
            mission_route = MissionRoute(
                mission_id=mission.id,
                uav_index=route.get('uav_index', 0),
                waypoints=waypoints_json,
                distance=route.get('distance', 0)
            )
            db.add(mission_route)
        
        await db.commit()
        
        return MissionSaveResponse(
            mission_id=mission.id,
            success=True,
            message="任务配置保存成功"
        )
        
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存任务配置失败: {str(e)}"
        )


@router.get("/route-planning/missions")
async def get_missions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    """
    获取用户的任务列表
    """
    try:
        from db import Mission
        
        result = await db.execute(
            select(Mission)
            .where(Mission.user_id == current_user.id)
            .order_by(Mission.created_at.desc())
            .limit(limit)
        )
        missions = result.scalars().all()
        
        mission_list = []
        for mission in missions:
            mission_list.append({
                "id": mission.id,
                "name": mission.name,
                "start_point": {
                    "lat": float(mission.start_point_lat),
                    "lng": float(mission.start_point_lng),
                    "name": mission.start_point_name
                },
                "end_point": {
                    "lat": float(mission.end_point_lat),
                    "lng": float(mission.end_point_lng),
                    "name": mission.end_point_name
                },
                "num_uavs": mission.num_uavs,
                "mission_type": mission.mission_type,
                "created_at": mission.created_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {"missions": mission_list}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.get("/route-planning/missions/{mission_id}")
async def get_mission_detail(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取任务详情，包括禁飞区、航点、航迹等
    """
    try:
        from db import Mission, MissionNoFlyZone, MissionWaypoint, MissionRoute
        
        # 获取任务
        result = await db.execute(
            select(Mission).where(Mission.id == mission_id, Mission.user_id == current_user.id)
        )
        mission = result.scalar_one_or_none()
        
        if not mission:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 获取禁飞区
        result = await db.execute(
            select(MissionNoFlyZone).where(MissionNoFlyZone.mission_id == mission_id)
        )
        nofly_zones = result.scalars().all()
        
        # 获取航点
        result = await db.execute(
            select(MissionWaypoint)
            .where(MissionWaypoint.mission_id == mission_id)
            .order_by(MissionWaypoint.sequence)
        )
        waypoints = result.scalars().all()
        
        # 获取航迹
        result = await db.execute(
            select(MissionRoute)
            .where(MissionRoute.mission_id == mission_id)
            .order_by(MissionRoute.uav_index)
        )
        routes = result.scalars().all()
        
        # 构建响应
        mission_detail = {
            "id": mission.id,
            "name": mission.name,
            "start_point": {
                "lat": float(mission.start_point_lat),
                "lng": float(mission.start_point_lng),
                "name": mission.start_point_name
            },
            "end_point": {
                "lat": float(mission.end_point_lat),
                "lng": float(mission.end_point_lng),
                "name": mission.end_point_name
            },
            "num_uavs": mission.num_uavs,
            "mission_type": mission.mission_type,
            "no_fly_zones": [
                {
                    "center": {
                        "lat": float(zone.center_lat),
                        "lng": float(zone.center_lng)
                    },
                    "radius": zone.radius,
                    "name": zone.name
                }
                for zone in nofly_zones
            ],
            "waypoints": [
                {
                    "lat": float(wp.lat),
                    "lng": float(wp.lng),
                    "name": wp.name,
                    "sequence": wp.sequence
                }
                for wp in waypoints
            ],
            "routes": [
                {
                    "uav_index": route.uav_index,
                    "waypoints": json.loads(route.waypoints),
                    "distance": route.distance
                }
                for route in routes
            ],
            "created_at": mission.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return mission_detail
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}"
        )


@router.delete("/route-planning/missions/{mission_id}")
async def delete_mission(
    mission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除任务及其关联的所有数据
    """
    try:
        from db import Mission, MissionNoFlyZone, MissionWaypoint, MissionRoute
        
        # 验证任务是否属于当前用户
        result = await db.execute(
            select(Mission).where(
                Mission.id == mission_id,
                Mission.user_id == current_user.id
            )
        )
        mission = result.scalar_one_or_none()
        
        if not mission:
            raise HTTPException(status_code=404, detail="任务不存在或无权删除")
        
        # 删除关联的禁飞区
        await db.execute(
            select(MissionNoFlyZone).where(MissionNoFlyZone.mission_id == mission_id)
        )
        result = await db.execute(
            select(MissionNoFlyZone).where(MissionNoFlyZone.mission_id == mission_id)
        )
        for zone in result.scalars().all():
            await db.delete(zone)
        
        # 删除关联的航点
        result = await db.execute(
            select(MissionWaypoint).where(MissionWaypoint.mission_id == mission_id)
        )
        for wp in result.scalars().all():
            await db.delete(wp)
        
        # 删除关联的航迹
        result = await db.execute(
            select(MissionRoute).where(MissionRoute.mission_id == mission_id)
        )
        for route in result.scalars().all():
            await db.delete(route)
        
        # 删除任务本身
        await db.delete(mission)
        
        await db.commit()
        
        return {
            "status": "success",
            "message": "任务已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除任务失败: {str(e)}"
        )



# 网络拓扑 - 网络指标 API
@router.get("/network-metrics")
async def get_network_metrics(current_user: User = Depends(get_current_user)):
    """
    获取所有活跃无人机的网络性能指标
    返回包含带宽、速率、丢包率、时延、连接时间等信息
    """
    try:
        metrics = manager.get_all_network_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取网络指标失败: {str(e)}"
        )


# 地理编码 API
@router.post("/enhance-task-plan-coordinates")
async def enhance_task_plan_coordinates(
    request: TaskPlanEnhanceRequest,
    current_user: User = Depends(get_current_user)
):
    """
    增强任务规划中的坐标信息
    
    Args:
        request: 包含任务规划和对话上下文
        
    Returns:
        增强后的任务规划
    """
    if not task_plan_enhancer:
        # 地理编码服务未初始化，返回原始任务规划
        logger.warning("Geocoding service not available, returning original task plan")
        return TaskPlanEnhanceResponse(
            success=False,
            task_plan=request.task_plan,
            error="地理编码服务未配置"
        )
    
    try:
        logger.info("Enhancing task plan coordinates")
        
        enhanced_plan = await task_plan_enhancer.enhance_task_plan(
            task_plan=request.task_plan,
            conversation_context=request.conversation_context
        )
        
        return TaskPlanEnhanceResponse(
            success=True,
            task_plan=enhanced_plan,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Failed to enhance task plan coordinates: {e}")
        # 失败时返回原始任务规划
        return TaskPlanEnhanceResponse(
            success=False,
            task_plan=request.task_plan,
            error=str(e)
        )

