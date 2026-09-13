"""
任务规划增强器模块
识别并增强任务规划中的地理位置信息
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from geocoding_service import GeocodingService

logger = logging.getLogger(__name__)


@dataclass
class LocationField:
    """地点字段信息"""
    field_path: str  # JSON路径，如 "startPoint" 或 "waypoints[0]"
    name: str  # 地点名称
    current_lat: Optional[float] = None  # 当前纬度（如果有）
    current_lng: Optional[float] = None  # 当前经度（如果有）


class TaskPlanEnhancer:
    """
    任务规划增强器
    识别并增强任务规划中的地理位置信息
    """
    
    # 需要地理编码的字段名称
    LOCATION_FIELDS = [
        "startPoint", "start_point", "start",
        "endPoint", "end_point", "end", "destination",
        "targetPoint", "target_point", "target"
    ]
    
    # 嵌套路径中的地点字段
    NESTED_LOCATION_PATHS = [
        ("route", "from"),
        ("route", "to"),
        ("route", "startPoint"),
        ("route", "destination"),
        ("patrolArea", "center"),
        ("searchArea", "center")
    ]
    
    def __init__(self, geocoding_service: GeocodingService):
        """
        初始化任务规划增强器
        
        Args:
            geocoding_service: 地理编码服务实例
        """
        self.geocoding_service = geocoding_service
        logger.info("TaskPlanEnhancer initialized")
    
    def _is_location_field(self, key: str) -> bool:
        """
        判断字段是否是地点字段
        
        Args:
            key: 字段名
            
        Returns:
            是否是地点字段
        """
        return key in self.LOCATION_FIELDS
    
    def _extract_location_name(self, value: Any) -> Optional[str]:
        """
        从字段值中提取地点名称
        
        Args:
            value: 字段值（可能是字符串或字典）
            
        Returns:
            地点名称，如果无法提取返回None
        """
        if isinstance(value, str):
            return value.strip() if value.strip() else None
        elif isinstance(value, dict):
            # 如果是字典，尝试获取name字段
            return value.get("name") or value.get("地点") or value.get("location")
        return None
    
    def _has_coordinates(self, value: Any) -> bool:
        """
        检查字段值是否已经包含坐标
        
        Args:
            value: 字段值
            
        Returns:
            是否包含坐标
        """
        if isinstance(value, dict):
            return ("lat" in value and "lng" in value) or \
                   ("latitude" in value and "longitude" in value)
        return False
    
    def _identify_locations(
        self,
        task_plan: Dict[str, Any]
    ) -> List[LocationField]:
        """
        识别任务规划中需要地理编码的地点字段
        
        Args:
            task_plan: 任务规划JSON
            
        Returns:
            需要地理编码的地点列表
        """
        locations = []
        
        # 1. 检查顶层地点字段
        for key, value in task_plan.items():
            if self._is_location_field(key):
                location_name = self._extract_location_name(value)
                if location_name and not self._has_coordinates(value):
                    locations.append(LocationField(
                        field_path=key,
                        name=location_name
                    ))
        
        # 2. 检查嵌套路径中的地点
        for parent_key, child_key in self.NESTED_LOCATION_PATHS:
            if parent_key in task_plan and isinstance(task_plan[parent_key], dict):
                parent_obj = task_plan[parent_key]
                if child_key in parent_obj:
                    value = parent_obj[child_key]
                    location_name = self._extract_location_name(value)
                    if location_name and not self._has_coordinates(value):
                        locations.append(LocationField(
                            field_path=f"{parent_key}.{child_key}",
                            name=location_name
                        ))
        
        # 3. 检查waypoints数组
        if "waypoints" in task_plan and isinstance(task_plan["waypoints"], list):
            for i, waypoint in enumerate(task_plan["waypoints"]):
                if isinstance(waypoint, dict):
                    location_name = self._extract_location_name(waypoint)
                    if location_name and not self._has_coordinates(waypoint):
                        locations.append(LocationField(
                            field_path=f"waypoints[{i}]",
                            name=location_name
                        ))
        
        logger.info(f"Identified {len(locations)} locations for geocoding")
        return locations
    
    def _update_location_coordinates(
        self,
        task_plan: Dict[str, Any],
        location_field: LocationField,
        geocode_result: Dict[str, Any]
    ) -> None:
        """
        更新任务规划中的坐标信息
        
        Args:
            task_plan: 任务规划JSON（会被修改）
            location_field: 地点字段信息
            geocode_result: 地理编码结果
        """
        field_path = location_field.field_path
        
        # 解析字段路径
        if "[" in field_path:
            # 处理数组索引，如 "waypoints[0]"
            parts = field_path.split("[")
            array_key = parts[0]
            index = int(parts[1].rstrip("]"))
            
            if array_key in task_plan and isinstance(task_plan[array_key], list):
                if index < len(task_plan[array_key]):
                    item = task_plan[array_key][index]
                    if isinstance(item, dict):
                        item["lat"] = geocode_result["lat"]
                        item["lng"] = geocode_result["lng"]
                        if "name" not in item:
                            item["name"] = geocode_result["name"]
                    else:
                        # 如果是字符串，转换为字典
                        task_plan[array_key][index] = {
                            "name": geocode_result["name"],
                            "lat": geocode_result["lat"],
                            "lng": geocode_result["lng"]
                        }
        
        elif "." in field_path:
            # 处理嵌套路径，如 "route.from"
            parts = field_path.split(".")
            parent_key = parts[0]
            child_key = parts[1]
            
            if parent_key in task_plan and isinstance(task_plan[parent_key], dict):
                parent_obj = task_plan[parent_key]
                value = parent_obj.get(child_key)
                
                if isinstance(value, dict):
                    value["lat"] = geocode_result["lat"]
                    value["lng"] = geocode_result["lng"]
                    if "name" not in value:
                        value["name"] = geocode_result["name"]
                else:
                    # 如果是字符串，转换为字典
                    parent_obj[child_key] = {
                        "name": geocode_result["name"],
                        "lat": geocode_result["lat"],
                        "lng": geocode_result["lng"]
                    }
        
        else:
            # 处理顶层字段
            if field_path in task_plan:
                value = task_plan[field_path]
                
                if isinstance(value, dict):
                    value["lat"] = geocode_result["lat"]
                    value["lng"] = geocode_result["lng"]
                    if "name" not in value:
                        value["name"] = geocode_result["name"]
                else:
                    # 如果是字符串，转换为字典
                    task_plan[field_path] = {
                        "name": geocode_result["name"],
                        "lat": geocode_result["lat"],
                        "lng": geocode_result["lng"]
                    }
    
    async def enhance_task_plan(
        self,
        task_plan: Dict[str, Any],
        conversation_context: str = ""
    ) -> Dict[str, Any]:
        """
        增强任务规划中的地理位置信息
        
        Args:
            task_plan: AI生成的任务规划JSON
            conversation_context: 对话上下文（用于提取城市信息）
            
        Returns:
            增强后的任务规划，包含精确坐标
        """
        try:
            # 提取城市信息
            city = self.geocoding_service._extract_city_from_context(
                conversation_context
            )
            logger.info(f"Extracted city from context: {city}")
            
            # 识别需要地理编码的地点
            locations = self._identify_locations(task_plan)
            
            if not locations:
                logger.info("No locations found for geocoding")
                return task_plan
            
            # 批量地理编码
            addresses = [loc.name for loc in locations]
            geocode_results = await self.geocoding_service.batch_geocode(
                addresses, city
            )
            
            # 更新任务规划中的坐标
            success_count = 0
            for location, result in zip(locations, geocode_results):
                if result:
                    self._update_location_coordinates(
                        task_plan, location, result
                    )
                    success_count += 1
                else:
                    logger.warning(
                        f"Failed to geocode location: {location.name}"
                    )
            
            logger.info(
                f"Enhanced task plan: {success_count}/{len(locations)} "
                f"locations geocoded successfully"
            )
            
            return task_plan
            
        except Exception as e:
            logger.error(f"Error enhancing task plan: {e}")
            # 出错时返回原始任务规划
            return task_plan

