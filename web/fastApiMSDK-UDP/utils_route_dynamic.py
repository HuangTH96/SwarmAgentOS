"""
动态路径规划器
不依赖预定义的CSV文件，直接使用前端传递的坐标点进行路径规划
"""
import math
import numpy as np
from haversine import haversine
import networkx as nx
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from sklearn.cluster import KMeans
from shapely.geometry import Point, LineString
from typing import List, Dict, Any, Tuple


class DynamicRoutePlanner:
    """
    动态路径规划器
    根据前端传递的坐标点和无人机数量进行路径规划
    """
    
    def __init__(self):
        """初始化规划器"""
        print("[动态规划器] 初始化完成")
    
    def build_graph_from_points(
        self,
        start_point: Dict[str, Any],
        end_point: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        num_uavs: int,
        no_fly_zones: List[Dict[str, Any]] = None
    ) -> Tuple[nx.Graph, List[Dict[str, Any]], int, int]:
        """
        根据传入的点构建图结构
        
        Args:
            start_point: 起点 {"name": str, "lat": float, "lng": float}
            end_point: 终点 {"name": str, "lat": float, "lng": float}
            waypoints: 途经点列表 [{"name": str, "lat": float, "lng": float}, ...]
            num_uavs: 无人机数量
            no_fly_zones: 禁飞区列表 [{"center": {"lat": float, "lng": float}, "radius": float, "name": str}, ...]
            
        Returns:
            (图对象, 点列表, 起点索引, 终点索引)
        """
        if no_fly_zones is None:
            no_fly_zones = []
        
        # 统一禁飞区格式（圆形转矩形）
        normalized_zones = self.normalize_no_fly_zones(no_fly_zones)
        
        # 构建点列表
        points_list = []
        point_names = []
        
        # 添加起点
        points_list.append({
            'name': start_point.get('name', 'Start'),
            'latitude': start_point['lat'],
            'longitude': start_point['lng'],
            'type': 'start'
        })
        point_names.append(start_point.get('name', 'Start'))
        start_index = 0
        
        # 添加途经点
        for wp in waypoints:
            if wp.get('name') not in point_names:
                points_list.append({
                    'name': wp.get('name', f'Waypoint_{len(points_list)}'),
                    'latitude': wp['lat'],
                    'longitude': wp['lng'],
                    'type': 'waypoint'
                })
                point_names.append(wp.get('name', f'Waypoint_{len(points_list)-1}'))
        
        # 添加终点
        end_name = end_point.get('name', 'End')
        if end_name not in point_names:
            points_list.append({
                'name': end_name,
                'latitude': end_point['lat'],
                'longitude': end_point['lng'],
                'type': 'end'
            })
            point_names.append(end_name)
            end_index = len(points_list) - 1
        else:
            # 终点和起点相同
            end_index = point_names.index(end_name)
        
        # 检查哪些边会穿越哪些禁飞区
        from shapely.geometry import LineString, box
        
        zones_blocking_paths = set()  # 记录哪些禁飞区实际阻挡了路径
        
        for i in range(len(points_list)):
            for j in range(i + 1, len(points_list)):
                point_i = points_list[i]
                point_j = points_list[j]
                
                # 创建路径线段
                line = LineString([
                    (point_i['longitude'], point_i['latitude']),
                    (point_j['longitude'], point_j['latitude'])
                ])
                
                # 检查这条边穿越了哪些禁飞区
                for zone_idx, zone in enumerate(normalized_zones):
                    try:
                        bounds = zone['bounds']
                        rectangle = box(
                            bounds['west'],
                            bounds['south'],
                            bounds['east'],
                            bounds['north']
                        )
                        
                        if line.intersects(rectangle):
                            zones_blocking_paths.add(zone_idx)
                    except Exception as e:
                        continue
        
        # 只为实际阻挡路径的禁飞区生成绕行点
        detour_points_added = 0
        if zones_blocking_paths:
            print(f"[绕行点生成] 发现 {len(zones_blocking_paths)} 个禁飞区阻挡路径，生成绕行点")
            
            for zone_idx in zones_blocking_paths:
                zone = normalized_zones[zone_idx]
                bounds = zone['bounds']
                zone_name = zone.get('name', f'Zone{zone_idx}')
                
                # 生成禁飞区四个角点（稍微外扩50米作为安全距离）
                safety_margin_lat = 50 / 111000.0
                center_lat = (bounds['north'] + bounds['south']) / 2
                safety_margin_lng = 50 / (111000.0 * math.cos(center_lat * math.pi / 180))
                
                corner_points = [
                    {'name': f'角点_{zone_name}_东北', 'lat': bounds['north'] + safety_margin_lat, 'lng': bounds['east'] + safety_margin_lng},
                    {'name': f'角点_{zone_name}_东南', 'lat': bounds['south'] - safety_margin_lat, 'lng': bounds['east'] + safety_margin_lng},
                    {'name': f'角点_{zone_name}_西南', 'lat': bounds['south'] - safety_margin_lat, 'lng': bounds['west'] - safety_margin_lng},
                    {'name': f'角点_{zone_name}_西北', 'lat': bounds['north'] + safety_margin_lat, 'lng': bounds['west'] - safety_margin_lng},
                ]
                
                for corner in corner_points:
                    if corner['name'] not in point_names:
                        points_list.append({
                            'name': corner['name'],
                            'latitude': corner['lat'],
                            'longitude': corner['lng'],
                            'type': 'detour'
                        })
                        point_names.append(corner['name'])
                        detour_points_added += 1
            
            print(f"[绕行点生成] 共生成 {detour_points_added} 个角点绕行点")
        else:
            print(f"[绕行点生成] 没有禁飞区阻挡路径，无需生成绕行点")
        
        print(f"[图构建] 总节点数: {len(points_list)}")
        print(f"[图构建] 起点索引: {start_index} ({points_list[start_index]['name']})")
        print(f"[图构建] 终点索引: {end_index} ({points_list[end_index]['name']})")
        print(f"[图构建] 禁飞区数量: {len(normalized_zones)}")
        
        # 构建图
        G = nx.Graph()
        
        # 添加节点
        for i, point in enumerate(points_list):
            G.add_node(i,
                      name=point['name'],
                      lat=point['latitude'],
                      lon=point['longitude'],
                      type=point['type'])
        
        # 添加边（使用硬约束：完全阻止穿越禁飞区的边）
        edges_added = 0
        edges_blocked = 0
        
        for i in range(len(points_list)):
            for j in range(i + 1, len(points_list)):
                point_i = points_list[i]
                point_j = points_list[j]
                
                # 计算直线距离（米）
                dist = haversine(
                    (point_i['latitude'], point_i['longitude']),
                    (point_j['latitude'], point_j['longitude'])
                ) * 1000
                
                # 检查路径是否穿越禁飞区
                intersects_nofly = self.check_no_fly_zone_intersection_bool(
                    point_i, point_j, normalized_zones
                )
                
                if intersects_nofly:
                    # 完全不添加穿越禁飞区的边（硬约束）
                    edges_blocked += 1
                else:
                    # 只添加不穿越禁飞区的边
                    G.add_edge(i, j, weight=dist, distance=dist)
                    edges_added += 1
        
        print(f"[图构建] 添加边数: {edges_added}, 阻止边数: {edges_blocked}")
        
        return G, points_list, start_index, end_index
    
    def generate_detour_points_around_zone(
        self,
        zone: Dict[str, Any],
        zone_idx: int
    ) -> List[Dict[str, Any]]:
        """
        在矩形禁飞区四周生成绕行点
        在矩形的四个角外侧生成点
        
        Args:
            zone: 禁飞区（矩形格式）
            zone_idx: 禁飞区索引
            
        Returns:
            绕行点列表
        """
        bounds = zone['bounds']
        name = zone.get('name', f'Zone{zone_idx}')
        
        # 计算矩形的中心和尺寸
        center_lat = (bounds['north'] + bounds['south']) / 2
        center_lng = (bounds['east'] + bounds['west']) / 2
        height_deg = bounds['north'] - bounds['south']
        width_deg = bounds['east'] - bounds['west']
        
        # 安全距离：在矩形外侧50米
        safety_margin_lat = 50 / 111000.0
        safety_margin_lng = 50 / (111000.0 * math.cos(center_lat * math.pi / 180))
        
        # 在四个角外侧生成绕行点
        detour_points = []
        
        # 东北角外侧
        detour_points.append({
            'name': f'绕行_{name}_东北',
            'lat': bounds['north'] + safety_margin_lat,
            'lng': bounds['east'] + safety_margin_lng,
            'type': 'detour'
        })
        
        # 东南角外侧
        detour_points.append({
            'name': f'绕行_{name}_东南',
            'lat': bounds['south'] - safety_margin_lat,
            'lng': bounds['east'] + safety_margin_lng,
            'type': 'detour'
        })
        
        # 西南角外侧
        detour_points.append({
            'name': f'绕行_{name}_西南',
            'lat': bounds['south'] - safety_margin_lat,
            'lng': bounds['west'] - safety_margin_lng,
            'type': 'detour'
        })
        
        # 西北角外侧
        detour_points.append({
            'name': f'绕行_{name}_西北',
            'lat': bounds['north'] + safety_margin_lat,
            'lng': bounds['west'] - safety_margin_lng,
            'type': 'detour'
        })
        
        return detour_points
    
    def normalize_no_fly_zones(
        self,
        no_fly_zones: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将所有禁飞区统一转换为矩形格式
        圆形禁飞区转换为正方形（边长=直径）
        
        Args:
            no_fly_zones: 原始禁飞区列表（可能包含圆形和矩形）
            
        Returns:
            统一的矩形禁飞区列表
        """
        normalized_zones = []
        
        for zone in no_fly_zones:
            shape = zone.get('shape', 'circle')
            
            if shape == 'rectangle' and 'bounds' in zone:
                # 已经是矩形，直接使用
                normalized_zones.append({
                    'bounds': zone['bounds'],
                    'name': zone.get('name', 'NoFlyZone')
                })
            elif shape == 'circle' and 'center' in zone and 'radius' in zone:
                # 圆形转换为正方形
                center_lat = zone['center']['lat']
                center_lng = zone['center']['lng']
                radius = zone['radius']
                
                # 将半径从米转换为度
                radius_lat = radius / 111000.0
                radius_lng = radius / (111000.0 * math.cos(center_lat * math.pi / 180))
                
                # 创建正方形边界（边长=直径）
                normalized_zones.append({
                    'bounds': {
                        'north': center_lat + radius_lat,
                        'south': center_lat - radius_lat,
                        'east': center_lng + radius_lng,
                        'west': center_lng - radius_lng
                    },
                    'name': zone.get('name', 'NoFlyZone')
                })
                print(f"[禁飞区转换] 圆形 -> 矩形: {zone.get('name', 'Unknown')}")
        
        return normalized_zones
    
    def check_no_fly_zone_intersection_bool(
        self,
        point_a: Dict[str, Any],
        point_b: Dict[str, Any],
        no_fly_zones: List[Dict[str, Any]]
    ) -> bool:
        """
        检查两点之间的直线路径是否穿越禁飞区（支持矩形）
        
        Args:
            point_a: 起点
            point_b: 终点
            no_fly_zones: 禁飞区列表（统一为矩形格式）
            
        Returns:
            True 如果穿越禁飞区，False 否则
        """
        if not no_fly_zones:
            return False
        
        from shapely.geometry import LineString, box
        
        # 创建路径线段
        line = LineString([
            (point_a['longitude'], point_a['latitude']),
            (point_b['longitude'], point_b['latitude'])
        ])
        
        for zone in no_fly_zones:
            try:
                bounds = zone['bounds']
                
                # 创建矩形
                rectangle = box(
                    bounds['west'],
                    bounds['south'],
                    bounds['east'],
                    bounds['north']
                )
                
                # 检查线段是否与矩形相交
                if line.intersects(rectangle):
                    return True
            except Exception as e:
                print(f"[禁飞区检测] 检查失败: {str(e)}")
                continue
        
        return False
    
    def calculate_no_fly_zone_penalty(
        self,
        point_a: Dict[str, Any],
        point_b: Dict[str, Any],
        no_fly_zones: List[Dict[str, Any]]
    ) -> float:
        """
        计算路径与禁飞区的距离惩罚
        用于A*算法的启发式函数
        
        Args:
            point_a: 起点
            point_b: 终点
            no_fly_zones: 禁飞区列表
            
        Returns:
            惩罚值（米）
        """
        if not no_fly_zones:
            return 0.0
        
        from shapely.geometry import LineString, box, Point
        
        # 创建路径线段
        line = LineString([
            (point_a['longitude'], point_a['latitude']),
            (point_b['longitude'], point_b['latitude'])
        ])
        
        # 线段中点
        mid_point = Point(
            (point_a['longitude'] + point_b['longitude']) / 2,
            (point_a['latitude'] + point_b['latitude']) / 2
        )
        
        min_distance = float('inf')
        
        for zone in no_fly_zones:
            try:
                bounds = zone['bounds']
                rectangle = box(
                    bounds['west'],
                    bounds['south'],
                    bounds['east'],
                    bounds['north']
                )
                
                # 如果穿越禁飞区，返回大惩罚
                if line.intersects(rectangle):
                    return 100000.0  # 100km惩罚
                
                # 计算到禁飞区的最小距离
                distance = mid_point.distance(rectangle)
                min_distance = min(min_distance, distance)
                
            except Exception as e:
                continue
        
        # 距离越近，惩罚越大（在50米内开始惩罚）
        if min_distance < float('inf'):
            distance_meters = min_distance * 111000.0
            if distance_meters < 50:
                return (50 - distance_meters) * 100  # 最多5000米惩罚
        
        return 0.0

    
    def optimize_route_path(
        self,
        route: List[int],
        points: List[Dict[str, Any]],
        required_point_indices: set,
        no_fly_zones: List[Dict[str, Any]]
    ) -> List[int]:
        """
        优化单条路径，移除不必要的绕行点
        
        算法：迭代地检查每个非必经点，如果移除后不会穿越禁飞区则移除
        
        Args:
            route: 路径索引列表
            points: 所有点的列表
            required_point_indices: 必经点索引集合（起点、终点、waypoints）
            no_fly_zones: 禁飞区列表（统一为矩形格式）
            
        Returns:
            优化后的路径索引列表
        """
        if len(route) <= 2:
            return route
        
        # 统一禁飞区格式
        normalized_zones = self.normalize_no_fly_zones(no_fly_zones)
        
        optimized = True
        iteration = 0
        max_iterations = 10  # 防止无限循环
        
        while optimized and iteration < max_iterations:
            optimized = False
            iteration += 1
            new_route = [route[0]]  # 保留起点
            
            i = 1
            while i < len(route) - 1:
                current_idx = route[i]
                prev_idx = new_route[-1]
                next_idx = route[i + 1]
                
                # 如果是必经点，必须保留
                if current_idx in required_point_indices:
                    new_route.append(current_idx)
                    i += 1
                    continue
                
                # 检查是否可以跳过当前点（直接从prev到next）
                prev_point = points[prev_idx]
                next_point = points[next_idx]
                
                # 检查prev到next的直连是否穿越禁飞区
                can_skip = not self.check_no_fly_zone_intersection_bool(
                    prev_point, next_point, normalized_zones
                )
                
                if can_skip:
                    # 可以跳过当前点，不添加到新路径
                    optimized = True
                    print(f"[路径优化] 移除不必要的绕行点: {points[current_idx]['name']}")
                else:
                    # 不能跳过，保留当前点
                    new_route.append(current_idx)
                
                i += 1
            
            # 添加终点
            new_route.append(route[-1])
            route = new_route
        
        if iteration > 1:
            print(f"[路径优化] 完成，迭代次数: {iteration - 1}, 优化后路径长度: {len(route)}")
        
        return route
    
    def optimize_all_routes(
        self,
        routes: List[List[int]],
        points: List[Dict[str, Any]],
        start_index: int,
        end_index: int,
        waypoints_indices: List[int],
        no_fly_zones: List[Dict[str, Any]]
    ) -> List[List[int]]:
        """
        优化所有路径
        
        Args:
            routes: 原始路径列表
            points: 所有点的列表
            start_index: 起点索引
            end_index: 终点索引
            waypoints_indices: 途经点索引列表
            no_fly_zones: 禁飞区列表
            
        Returns:
            优化后的路径列表
        """
        # 构建必经点集合
        required_point_indices = {start_index, end_index}
        required_point_indices.update(waypoints_indices)
        
        print(f"[路径优化] 开始优化 {len(routes)} 条路径")
        print(f"[路径优化] 必经点数量: {len(required_point_indices)}")
        
        optimized_routes = []
        for route_idx, route in enumerate(routes):
            original_length = len(route)
            optimized_route = self.optimize_route_path(
                route, points, required_point_indices, no_fly_zones
            )
            optimized_length = len(optimized_route)
            
            if optimized_length < original_length:
                print(f"[路径优化] 路径 {route_idx}: {original_length} -> {optimized_length} 个点")
            
            optimized_routes.append(optimized_route)
        
        return optimized_routes
    
    def find_optimal_routes(
        self,
        start_point: Dict[str, Any],
        end_point: Dict[str, Any],
        waypoints: List[Dict[str, Any]],
        num_uavs: int,
        no_fly_zones: List[Dict[str, Any]] = None
    ) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
        """
        寻找最优路径
        
        Args:
            start_point: 起点
            end_point: 终点
            waypoints: 途经点列表
            num_uavs: 无人机数量
            no_fly_zones: 禁飞区列表
            
        Returns:
            (路径列表, 点列表)
        """
        if no_fly_zones is None:
            no_fly_zones = []
        
        G, points, start_index, end_index = self.build_graph_from_points(
            start_point, end_point, waypoints, num_uavs, no_fly_zones
        )
        
        if num_uavs == 1 or len(points) <= 2:
            # 单无人机：使用TSP算法
            routes = self.solve_tsp(G, points, start_index, end_index)
        else:
            # 多无人机：车辆路径问题
            routes = self.solve_vrp(G, points, num_uavs, start_index, end_index)
        
        # 确定必经点索引（起点、终点、所有waypoints）
        required_point_indices = {start_index, end_index}
        for point_idx, point in enumerate(points):
            if point.get('type') == 'waypoint':
                required_point_indices.add(point_idx)
        
        # 对每条路径进行优化，移除不必要的绕行点
        if no_fly_zones:
            print(f"[路径优化] 开始优化 {len(routes)} 条路径")
            optimized_routes = []
            for route_idx, route in enumerate(routes):
                print(f"[路径优化] 优化路径 {route_idx + 1}/{len(routes)}, 原始长度: {len(route)}")
                optimized_route = self.optimize_route_path(
                    route, points, required_point_indices, no_fly_zones
                )
                optimized_routes.append(optimized_route)
            routes = optimized_routes
        
        return routes, points
    
    def solve_tsp(
        self,
        G: nx.Graph,
        points: List[Dict[str, Any]],
        start_index: int,
        end_index: int
    ) -> List[List[int]]:
        """
        使用OR-Tools求解TSP（单无人机）
        
        Args:
            G: 图对象
            points: 点列表
            start_index: 起点索引
            end_index: 终点索引
            
        Returns:
            路径列表（只有一条路径）
        """
        if len(points) <= 2:
            if start_index == end_index:
                return [[start_index]]
            else:
                return [[start_index, end_index]]
        
        # 创建距离矩阵
        num_locations = len(points)
        distance_matrix = []
        
        for i in range(num_locations):
            row = []
            for j in range(num_locations):
                if i == j:
                    row.append(0)
                elif G.has_edge(i, j):
                    row.append(int(G[i][j]['distance']))
                else:
                    row.append(999999)
            distance_matrix.append(row)
        
        try:
            # 使用OR-Tools求解TSP
            if start_index == end_index:
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, 1, start_index
                )
            else:
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, 1, [start_index], [end_index]
                )
            
            routing = pywrapcp.RoutingModel(manager)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return distance_matrix[from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # 设置搜索参数
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = 5
            
            # 求解
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                route = []
                index = routing.Start(0)
                route_distance = 0
                
                while not routing.IsEnd(index):
                    node_index = manager.IndexToNode(index)
                    route.append(node_index)
                    previous_index = index
                    index = solution.Value(routing.NextVar(index))
                    
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    route_distance += distance_matrix[from_node][to_node]
                
                route.append(manager.IndexToNode(routing.End(0)))
                
                print(f"[TSP] OR-Tools求解成功，距离: {route_distance:.0f}米")
                return [route]
            else:
                print(f"[TSP] OR-Tools求解失败，使用简单路径")
                return self.simple_path(points, start_index, end_index)
        
        except Exception as e:
            print(f"[TSP] 异常: {str(e)}，使用简单路径")
            return self.simple_path(points, start_index, end_index)
    
    def solve_vrp(
        self,
        G: nx.Graph,
        points: List[Dict[str, Any]],
        num_vehicles: int,
        start_index: int,
        end_index: int
    ) -> List[List[int]]:
        """
        使用OR-Tools求解VRP（多无人机）
        
        Args:
            G: 图对象
            points: 点列表
            num_vehicles: 无人机数量
            start_index: 起点索引
            end_index: 终点索引
            
        Returns:
            路径列表
        """
        # 创建距离矩阵
        num_locations = len(points)
        distance_matrix = []
        
        for i in range(num_locations):
            row = []
            for j in range(num_locations):
                if i == j:
                    row.append(0)
                elif G.has_edge(i, j):
                    row.append(int(G[i][j]['distance']))
                else:
                    row.append(999999)
            distance_matrix.append(row)
        
        print(f"[VRP] 节点数: {num_locations}, 无人机数: {num_vehicles}")
        
        try:
            # 使用OR-Tools求解VRP
            if start_index == end_index:
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, num_vehicles, start_index
                )
            else:
                starts = [start_index] * num_vehicles
                ends = [end_index] * num_vehicles
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, num_vehicles, starts, ends
                )
            
            routing = pywrapcp.RoutingModel(manager)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return distance_matrix[from_node][to_node]
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # 添加距离约束
            dimension_name = 'Distance'
            routing.AddDimension(
                transit_callback_index,
                0,
                500000,
                True,
                dimension_name
            )
            
            # 设置搜索参数
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
            )
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )
            search_parameters.time_limit.seconds = 5
            
            # 求解
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                print(f"[VRP] OR-Tools求解成功")
                routes = []
                total_distance = 0
                
                for vehicle_id in range(num_vehicles):
                    route = []
                    index = routing.Start(vehicle_id)
                    route_distance = 0
                    
                    while not routing.IsEnd(index):
                        node_index = manager.IndexToNode(index)
                        route.append(node_index)
                        previous_index = index
                        index = solution.Value(routing.NextVar(index))
                        
                        from_node = manager.IndexToNode(previous_index)
                        to_node = manager.IndexToNode(index)
                        route_distance += distance_matrix[from_node][to_node]
                    
                    route.append(manager.IndexToNode(routing.End(vehicle_id)))
                    routes.append(route)
                    total_distance += route_distance
                    
                    if len(route) > 2 or (len(route) == 2 and route[0] != route[1]):
                        print(f"  无人机 {vehicle_id + 1}: {len(route)}个节点, {route_distance:.0f}米")
                
                print(f"  总飞行距离: {total_distance:.0f}米")
                
                # 过滤空路径
                valid_routes = []
                for route in routes:
                    if len(route) > 2 or (len(route) == 2 and route[0] != route[1]):
                        valid_routes.append(route)
                
                # 如果有效路径少于无人机数量，使用聚类分配
                if len(valid_routes) < num_vehicles:
                    print(f"[VRP] 有效路径不足，使用聚类分配")
                    return self.cluster_and_assign(points, num_vehicles, start_index, end_index)
                
                return valid_routes
            else:
                print(f"[VRP] OR-Tools求解失败，使用聚类分配")
                return self.cluster_and_assign(points, num_vehicles, start_index, end_index)
        
        except Exception as e:
            print(f"[VRP] 异常: {str(e)}，使用聚类分配")
            import traceback
            traceback.print_exc()
            return self.cluster_and_assign(points, num_vehicles, start_index, end_index)
    
    def cluster_and_assign(
        self,
        points: List[Dict[str, Any]],
        num_uavs: int,
        start_index: int,
        end_index: int
    ) -> List[List[int]]:
        """
        使用K-means聚类分配点到各无人机
        
        Args:
            points: 点列表
            num_uavs: 无人机数量
            start_index: 起点索引
            end_index: 终点索引
            
        Returns:
            路径列表
        """
        print(f"[聚类分配] 节点总数: {len(points)}, 无人机数: {num_uavs}")
        
        if len(points) <= 2:
            routes = []
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            return routes
        
        # 提取坐标进行聚类（排除起点和终点）
        coords = []
        indices = []
        for i, point in enumerate(points):
            if i != start_index and i != end_index:
                coords.append([point['longitude'], point['latitude']])
                indices.append(i)
        
        if not coords:
            routes = []
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            return routes
        
        # 聚类数量
        n_clusters = min(num_uavs, len(coords))
        print(f"[聚类分配] 聚类数量: {n_clusters}")
        
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            coords_array = np.array(coords)
            labels = kmeans.fit_predict(coords_array)
            
            # 分配点到各簇
            clusters = [[] for _ in range(n_clusters)]
            for coord_idx, point_idx in enumerate(indices):
                cluster_idx = labels[coord_idx]
                clusters[cluster_idx].append(point_idx)
            
            # 为每个簇创建路径
            routes = []
            for cluster_idx in range(n_clusters):
                route = [start_index]
                
                if clusters[cluster_idx]:
                    # 按距离起点排序
                    cluster_points = clusters[cluster_idx]
                    if len(cluster_points) > 1:
                        start_coord = (points[start_index]['longitude'], points[start_index]['latitude'])
                        distances = []
                        for point_idx in cluster_points:
                            point_coord = (points[point_idx]['longitude'], points[point_idx]['latitude'])
                            dist = haversine(
                                (start_coord[1], start_coord[0]),
                                (point_coord[1], point_coord[0])
                            ) * 1000
                            distances.append((point_idx, dist))
                        
                        distances.sort(key=lambda x: x[1])
                        cluster_points_sorted = [x[0] for x in distances]
                        route.extend(cluster_points_sorted)
                    else:
                        route.extend(cluster_points)
                
                # 添加终点
                if start_index != end_index or len(route) > 1:
                    route.append(end_index)
                
                routes.append(route)
                print(f"  无人机 {cluster_idx + 1}: {[points[idx]['name'] for idx in route]}")
            
            # 确保返回的路径数量等于无人机数量
            while len(routes) < num_uavs:
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            
            return routes
        
        except Exception as e:
            print(f"[聚类分配] 失败: {str(e)}，使用简单分配")
            return self.simple_split(points, num_uavs, start_index, end_index)
    
    def simple_path(
        self,
        points: List[Dict[str, Any]],
        start_index: int,
        end_index: int
    ) -> List[List[int]]:
        """
        创建简单路径（按顺序访问所有点）
        
        Args:
            points: 点列表
            start_index: 起点索引
            end_index: 终点索引
            
        Returns:
            路径列表（只有一条路径）
        """
        route = [start_index]
        for i in range(len(points)):
            if i != start_index and i != end_index:
                route.append(i)
        if start_index != end_index:
            route.append(end_index)
        return [route]
    
    def simple_split(
        self,
        points: List[Dict[str, Any]],
        num_uavs: int,
        start_index: int,
        end_index: int
    ) -> List[List[int]]:
        """
        简单平均分配
        
        Args:
            points: 点列表
            num_uavs: 无人机数量
            start_index: 起点索引
            end_index: 终点索引
            
        Returns:
            路径列表
        """
        routes = []
        middle_points = [i for i in range(len(points)) if i != start_index and i != end_index]
        
        if not middle_points:
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            return routes
        
        points_per_uav = max(1, len(middle_points) // num_uavs)
        
        for i in range(num_uavs):
            start_idx = i * points_per_uav
            end_idx = start_idx + points_per_uav if i < num_uavs - 1 else len(middle_points)
            
            if start_idx < len(middle_points):
                route = [start_index]
                route.extend(middle_points[start_idx:end_idx])
                route.append(end_index)
                routes.append(route)
            else:
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
        
        return routes

