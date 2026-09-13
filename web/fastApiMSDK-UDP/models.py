# app/models.py
"""
定义应用中使用的所有 Pydantic 数据模型。
这些模型用于数据验证、序列化和 API 文档生成。
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any

# --- 命令模型 ---

class Command(BaseModel):
    """从Web控制面板发送到无人机的命令结构。"""
    client_id: str
    command: str

# --- 无人机数据模型 ---

class LocationCoordinate2DModel(BaseModel):
    """二维地理坐标模型。"""
    latitude: float
    longitude: float

class QuaternionModel(BaseModel):
    w: float
    x: float
    y: float
    z: float
class VelocityModel(BaseModel):
    x: float
    y: float
    z: float

class AngularVelocityModel(BaseModel):
    x: float
    y: float
    z: float
class AccelerationModel(BaseModel):
    x: float
    y: float
    z: float
class PositionVOModel(BaseModel):
    x: float
    y: float
    z: float

class TelemetryData(BaseModel):
    """无人机遥测数据模型。"""
    # 这是 Pydantic V2 的正确配置方式
    # 它是一个类变量，不是写在内部的 Config 类里
    model_config = ConfigDict(populate_by_name=True)

    longtitude: float = Field(..., alias="longtitude")
    latitude: float
    head: float
    height: float
    distance: float
    speed: float
    ros_enabled: bool
    origin_is_set: bool
    flystate: int
    origin_location: Optional[LocationCoordinate2DModel] = Field(None, alias="origin_location")
    homeLocation: Optional[LocationCoordinate2DModel] = Field(None, alias="homeLocation")
    quaternion: Optional[QuaternionModel] = Field(None, alias="quaternion")
    velocity: Optional[VelocityModel] = Field(None, alias="velocity")
    angular_velocity: Optional[AngularVelocityModel] = Field(None, alias="angular_velocity")
    acceleration: Optional[AccelerationModel] = Field(None, alias="acceleration")
    position_vo: Optional[PositionVOModel] = Field(None, alias="position_vo")
    position_latlon: Optional[PositionVOModel] = Field(None, alias="position_latlon")

class BatteryStateModel(BaseModel):
    """单个电池的状态信息。"""
    percent: float
    full_capacity: float
    remaining_capacity: float
    voltage: float
    connected: bool

class BatteryDataListModel(BaseModel):
    """电池信息列表，因为无人机可能有多个电池。"""
    batteries: List[BatteryStateModel]

# 为 set-target 定义请求体模型
class TargetLocation(BaseModel):
    client_id: str
    lat: float
    lng: float
    height: float


# AI 任务对话模型
class AiTaskMessage(BaseModel):
    """AI 任务对话消息模型"""
    role: str  # 'user' or 'assistant'
    content: str
    task_plan: Optional[dict] = None
    timestamp: Optional[str] = None
    mission_id: Optional[int] = None  # 关联的任务 ID


class ConversationAssociateRequest(BaseModel):
    """对话历史关联请求模型"""
    mission_id: int = Field(..., description="任务 ID")
    conversation_ids: List[int] = Field(..., description="对话记录 ID 列表")


# --- 路径规划模型 ---

class CoordinateModel(BaseModel):
    """坐标模型"""
    latitude: float = Field(..., ge=-90, le=90, description="纬度")
    longitude: float = Field(..., ge=-180, le=180, description="经度")


class PointModel(BaseModel):
    """点位模型（起点、终点、必经点）"""
    name: str = Field(..., description="点位名称")
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")


class NoFlyZoneModel(BaseModel):
    """禁飞区模型（支持圆形和矩形）"""
    name: str = Field(..., description="禁飞区名称")
    shape: str = Field(default="circle", description="形状：circle（圆形）或 rectangle（矩形）")
    # 圆形参数（仅圆形时必需）
    center: Optional[CoordinateModel] = Field(None, description="圆心坐标（圆形时使用）")
    radius: Optional[float] = Field(None, description="半径（米），最大5公里（圆形时使用）")
    # 矩形参数（仅矩形时必需）
    bounds: Optional[Dict[str, float]] = Field(None, description="矩形边界 {north, south, east, west}（矩形时使用）")
    
    def model_post_init(self, __context):
        """验证：圆形必须有center和radius，矩形必须有bounds"""
        if self.shape == "circle":
            if not self.center or self.radius is None:
                raise ValueError("圆形禁飞区必须提供 center 和 radius")
            if self.radius <= 0 or self.radius > 5000:
                raise ValueError("半径必须在 0 到 5000 米之间")
        elif self.shape == "rectangle":
            if not self.bounds:
                raise ValueError("矩形禁飞区必须提供 bounds")
            required_keys = {'north', 'south', 'east', 'west'}
            if not all(key in self.bounds for key in required_keys):
                raise ValueError(f"矩形边界必须包含: {required_keys}")


class WaypointModel(BaseModel):
    """必经点模型"""
    name: str = Field(..., description="必经点名称")
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    sequence: Optional[int] = Field(None, description="序号")


class RoutePlanningRequest(BaseModel):
    """路径规划请求模型"""
    start_point: PointModel = Field(..., description="起点")
    end_point: PointModel = Field(..., description="终点")
    number_uavs: int = Field(..., ge=1, le=20, description="无人机数量，1-20架")
    mission_type: str = Field(..., description="任务类型：patrol/delivery/inspection")
    waypoints: List[WaypointModel] = Field(default=[], description="必经点列表")
    no_fly_zones: List[NoFlyZoneModel] = Field(default=[], description="禁飞区列表")


class RouteWaypointModel(BaseModel):
    """路径航点模型"""
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    altitude: float = Field(default=50.0, description="飞行高度（米）")
    sequence: int = Field(..., description="航点序号")


class RouteModel(BaseModel):
    """单架无人机的路径模型"""
    uav_id: int = Field(..., description="无人机ID")
    waypoints: List[RouteWaypointModel] = Field(..., description="航点列表")
    total_distance: float = Field(..., description="总飞行距离（米）")
    estimated_time: float = Field(..., description="预计飞行时间（秒）")


class RoutePlanningResponse(BaseModel):
    """路径规划响应模型"""
    success: bool = Field(..., description="是否成功")
    routes: List[RouteModel] = Field(default=[], description="路径列表")
    total_distance: float = Field(default=0.0, description="总飞行距离（米）")
    computation_time: float = Field(default=0.0, description="计算耗时（秒）")
    error: Optional[str] = Field(None, description="错误信息")


class ValidationError(BaseModel):
    """验证错误模型"""
    field: str = Field(..., description="错误字段")
    message: str = Field(..., description="错误信息")
    severity: str = Field(..., description="严重程度：error/warning")


class ValidationResponse(BaseModel):
    """参数验证响应模型"""
    valid: bool = Field(..., description="是否有效")
    errors: List[ValidationError] = Field(default=[], description="错误列表")
    warnings: List[ValidationError] = Field(default=[], description="警告列表")


class MissionSaveRequest(BaseModel):
    """任务保存请求模型 - 用于保存完整的任务配置"""
    name: str = Field(..., description="任务名称")
    start_point: dict = Field(..., description="起点信息")
    end_point: dict = Field(..., description="终点信息")
    num_uavs: int = Field(..., description="无人机数量")
    mission_type: str = Field(..., description="任务类型")
    no_fly_zones: List[dict] = Field(default=[], description="禁飞区列表")
    waypoints: List[dict] = Field(default=[], description="必经点列表")
    routes: List[dict] = Field(default=[], description="生成的航迹")
    task_data: Optional[dict] = Field(None, description="原始任务数据")


class MissionSaveResponse(BaseModel):
    """任务保存响应模型"""
    mission_id: int = Field(..., description="任务ID")
    success: bool = Field(True, description="是否成功")
    message: str = Field(..., description="响应消息")


# --- 地理编码模型 ---

class TaskPlanEnhanceRequest(BaseModel):
    """任务规划增强请求模型"""
    task_plan: Dict[str, Any] = Field(..., description="任务规划JSON")
    conversation_context: str = Field(default="", description="对话上下文")


class TaskPlanEnhanceResponse(BaseModel):
    """任务规划增强响应模型"""
    success: bool = Field(..., description="是否成功")
    task_plan: Dict[str, Any] = Field(..., description="增强后的任务规划")
    error: Optional[str] = Field(None, description="错误信息")

