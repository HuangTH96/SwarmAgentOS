"""
地理编码服务模块
使用高德地图API将地点名称转换为GPS坐标
支持本地地点数据库优先查找
"""
import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from cachetools import TTLCache
import httpx

logger = logging.getLogger(__name__)


class GeocodingService:
    """
    地理编码服务类
    负责将地点名称转换为GPS坐标
    """
    
    # 高德地图地理编码API端点
    AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"
    
    # 默认配置
    DEFAULT_TIMEOUT = 5.0  # 5秒超时
    DEFAULT_CACHE_SIZE = 1000  # 缓存1000条
    DEFAULT_CACHE_TTL = 86400  # 24小时过期
    MAX_CONCURRENT_REQUESTS = 5  # 最多5个并发请求
    
    def __init__(
        self, 
        api_key: str,
        cache_size: int = DEFAULT_CACHE_SIZE,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        timeout: float = DEFAULT_TIMEOUT,
        local_db_path: Optional[str] = None
    ):
        """
        初始化地理编码服务
        
        Args:
            api_key: 高德地图API密钥
            cache_size: 缓存大小（默认1000条）
            cache_ttl: 缓存过期时间（秒，默认24小时）
            timeout: 请求超时时间（秒，默认5秒）
            local_db_path: 本地地点数据库路径（可选）
        """
        if not api_key:
            logger.error("AMAP API key not configured")
            raise ValueError("AMAP API key is required")
        
        self.api_key = api_key
        self.timeout = timeout
        
        # 初始化LRU缓存，带TTL
        self.cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        
        # 并发控制信号量
        self.semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)
        
        # HTTP客户端
        self.client = httpx.AsyncClient(timeout=timeout)
        
        # 加载本地地点数据库
        self.local_locations = {}
        if local_db_path is None:
            # 默认路径
            local_db_path = Path(__file__).parent / "data" / "campus_locations.json"
        
        self._load_local_database(local_db_path)
        
        logger.info(
            f"GeocodingService initialized with cache_size={cache_size}, "
            f"cache_ttl={cache_ttl}s, timeout={timeout}s, "
            f"local_locations={len(self.local_locations)}"
        )
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()
    
    def _load_local_database(self, db_path: Path):
        """
        加载本地地点数据库
        
        Args:
            db_path: 数据库文件路径
        """
        try:
            if not isinstance(db_path, Path):
                db_path = Path(db_path)
            
            if not db_path.exists():
                logger.warning(f"Local database not found: {db_path}")
                return
            
            with open(db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 构建地点名称到坐标的映射
            points = data.get("points", [])
            for point in points:
                name = point.get("name", "").strip()
                if name:
                    self.local_locations[name] = {
                        "lat": point.get("latitude"),
                        "lng": point.get("longitude"),
                        "name": name,
                        "type": point.get("type", "normal"),
                        "formatted_address": f"校园地点: {name}"
                    }
            
            logger.info(f"Loaded {len(self.local_locations)} locations from local database")
            
        except Exception as e:
            logger.error(f"Failed to load local database from {db_path}: {e}")
    
    def _search_local_location(self, address: str) -> Optional[Dict[str, Any]]:
        """
        在本地数据库中搜索地点
        
        Args:
            address: 地点名称
            
        Returns:
            坐标信息，如果未找到返回None
        """
        address = address.strip()
        
        # 精确匹配
        if address in self.local_locations:
            logger.info(f"Found exact match in local database: {address}")
            return self.local_locations[address].copy()
        
        # 模糊匹配（包含关系）
        for name, location in self.local_locations.items():
            if address in name or name in address:
                logger.info(f"Found fuzzy match in local database: {address} -> {name}")
                return location.copy()
        
        logger.debug(f"No match found in local database for: {address}")
        return None
    
    def _get_cache_key(self, address: str, city: str) -> str:
        """
        生成缓存键
        
        Args:
            address: 地点名称
            city: 城市名称
            
        Returns:
            缓存键字符串
        """
        return f"{address}:{city}"
    
    def _extract_city_from_context(self, text: str) -> str:
        """
        从文本中提取城市信息
        
        Args:
            text: 对话文本
            
        Returns:
            城市名称（如"南京"）
        """
        # 南京相关关键词
        nanjing_keywords = [
            "南航", "南京航空航天大学", "NUAA",
            "将军路", "明故宫", "江宁", "南京"
        ]
        
        for keyword in nanjing_keywords:
            if keyword in text:
                return "南京"
        
        # 可以扩展其他城市的识别
        # TODO: 添加更多城市的关键词识别
        
        # 默认返回南京
        return "南京"
    
    async def geocode(
        self, 
        address: str, 
        city: str = "南京"
    ) -> Optional[Dict[str, Any]]:
        """
        地理编码：将地址转换为坐标
        优先从本地数据库查找，找不到再调用高德API
        
        Args:
            address: 地点名称（如"南航北门"）
            city: 城市名称（默认"南京"）
            
        Returns:
            {
                "lat": 31.9365,
                "lng": 118.8245,
                "name": "南航北门",
                "formatted_address": "江苏省南京市江宁区将军大道29号"
            }
            如果失败返回None
        """
        if not address or not address.strip():
            logger.warning("Empty address provided for geocoding")
            return None
        
        address = address.strip()
        
        # 1. 优先从本地数据库查找
        local_result = self._search_local_location(address)
        if local_result:
            logger.info(f"Using local database result for: {address}")
            return local_result
        
        # 2. 检查缓存
        cache_key = self._get_cache_key(address, city)
        if cache_key in self.cache:
            logger.info(f"Cache hit for address: {address}, city: {city}")
            return self.cache[cache_key]
        
        # 3. 调用高德API
        # 使用信号量控制并发
        async with self.semaphore:
            try:
                logger.info(f"Geocoding address via AMAP API: {address}, city: {city}")
                
                # 构建请求参数
                params = {
                    "key": self.api_key,
                    "address": address,
                    "city": city,
                    "output": "JSON"
                }
                
                # 发送请求
                response = await self.client.get(
                    self.AMAP_GEOCODE_URL,
                    params=params
                )
                
                response.raise_for_status()
                data = response.json()
                
                # 解析响应
                if data.get("status") == "1" and data.get("geocodes"):
                    geocodes = data["geocodes"]
                    if geocodes and len(geocodes) > 0:
                        geocode = geocodes[0]  # 取第一个结果
                        
                        # 解析经纬度
                        location = geocode.get("location", "")
                        if location:
                            lng, lat = location.split(",")
                            
                            result = {
                                "lat": float(lat),
                                "lng": float(lng),
                                "name": address,
                                "formatted_address": geocode.get("formatted_address", "")
                            }
                            
                            # 存入缓存
                            self.cache[cache_key] = result
                            
                            logger.info(
                                f"Geocoding successful: {address} -> "
                                f"({result['lat']}, {result['lng']})"
                            )
                            
                            return result
                
                # 没有找到结果
                logger.warning(
                    f"No geocoding results for address: {address}, city: {city}"
                )
                return None
                
            except httpx.TimeoutException:
                logger.error(
                    f"Geocoding timeout for address: {address}, city: {city}"
                )
                return None
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error during geocoding: {e.response.status_code} - "
                    f"{e.response.text}"
                )
                return None
            except Exception as e:
                logger.error(f"Geocoding error for address {address}: {e}")
                return None
    
    async def batch_geocode(
        self,
        addresses: List[str],
        city: str = "南京"
    ) -> List[Optional[Dict[str, Any]]]:
        """
        批量地理编码
        
        Args:
            addresses: 地点名称列表
            city: 城市名称
            
        Returns:
            坐标列表，与输入顺序对应，失败的为None
        """
        if not addresses:
            return []
        
        logger.info(f"Batch geocoding {len(addresses)} addresses")
        
        # 并发执行地理编码
        tasks = [self.geocode(address, city) for address in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Exception during batch geocoding for address "
                    f"{addresses[i]}: {result}"
                )
                processed_results.append(None)
            else:
                processed_results.append(result)
        
        return processed_results
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        return {
            "cache_size": len(self.cache),
            "cache_maxsize": self.cache.maxsize,
            "cache_ttl": self.cache.ttl,
            "local_locations_count": len(self.local_locations)
        }

