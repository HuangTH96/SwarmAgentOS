import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from haversine import haversine
import networkx as nx
from shapely.geometry import Point, Polygon, LineString
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import geopandas as gpd
import contextily as ctx
from matplotlib.legend_handler import HandlerBase
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import warnings
from sklearn.cluster import KMeans

warnings.filterwarnings('ignore')


class NUAARoutePlanner:
    def __init__(self):
        # 加载校园数据
        try:
            self.points_df = pd.read_csv('./data/nuaa_campus_points.csv')
            print(f"成功加载 {len(self.points_df)} 个校园点")
        except FileNotFoundError:
            print("错误: 找不到数据文件")
            raise

        # 加载禁飞区
        try:
            with open('./data/nuaa_nofly_zones.json', 'r') as f:
                self.nofly_zones = json.load(f)
            print(f"成功加载 {len(self.nofly_zones)} 个禁飞区")
        except FileNotFoundError:
            print("警告: 找不到禁飞区文件，使用空禁飞区")
            self.nofly_zones = []

        # 系统提示词
        self.system_prompt = """
        解析南京航空航天大学将军路校区的无人机任务指令，提取关键信息。

        步骤：
        1. 识别起点和终点
        2. 识别无人机数量
        3. 识别任务类型：patrol（巡逻）、delivery（配送）、inspection（巡检）
        4. 识别中转点（可选）
        5. 识别任务约束：避开特定区域等

        输出必须是有效的JSON格式，结构如下：
        {
            "start_point": string,        # 起点名称
            "end_point": string,          # 终点名称
            "number_uavs": integer,       # 无人机数量
            "mission_type": string,       # 任务类型
            "waypoints": [string],        # 中转点列表
            "constraints": {              # 约束条件
                "avoid_areas": [string]   # 需要避开的区域
            }
        }
        """

        # 默认任务配置
        self.default_mission = {
            "start_point": "Main_Quad",
            "end_point": "Main_Quad",
            "number_uavs": 1,
            "mission_type": "patrol",
            "waypoints": [],
            "constraints": {
                "avoid_areas": []
            }
        }

        # 校园边界（南航将军路校区）
        self.campus_bounds = {
            'min_lon': 118.822,
            'max_lon': 118.829,
            'min_lat': 31.934,
            'max_lat': 31.940
        }

        # 地图源
        self.map_source = ctx.providers.OpenStreetMap.Mapnik  # 校园地图使用OpenStreetMap

    def find_point_by_name(self, name):
        """通过名称查找点"""
        if name is None:
            return None

        # 精确匹配
        matches = self.points_df[self.points_df['name'] == name]
        if len(matches) > 0:
            return matches.iloc[0]

        # 部分匹配
        matches = self.points_df[self.points_df['name'].str.contains(name, case=False, na=False)]
        if len(matches) > 0:
            return matches.iloc[0]

        print(f"警告: 未找到点 '{name}'，使用默认起点")
        return self.points_df.iloc[0]

    def build_graph(self, mission_data):
        """构建图结构"""
        # 获取所有相关点
        points_list = []
        point_names = []

        # 添加起点
        start_point = self.find_point_by_name(mission_data['start_point'])
        points_list.append(start_point)
        point_names.append(start_point['name'])

        # 添加中转点
        for wp_name in mission_data['waypoints']:
            wp_point = self.find_point_by_name(wp_name)
            if wp_point is not None and wp_point['name'] not in point_names:
                points_list.append(wp_point)
                point_names.append(wp_point['name'])

        # 如果是巡逻任务或巡检任务，添加所有POI（包括normal类型）
        if mission_data['mission_type'] in ['patrol', 'inspection']:
            # 获取所有点，排除已经在points_list中的点
            all_points = self.points_df
            for _, point in all_points.iterrows():
                if point['name'] not in point_names:  # 只添加不在列表中的点
                    points_list.append(point)
                    point_names.append(point['name'])

        # 添加终点
        end_point = self.find_point_by_name(mission_data['end_point'])
        if end_point['name'] not in point_names:
            points_list.append(end_point)
            point_names.append(end_point['name'])

        # 记录起点和终点索引
        start_index = 0
        end_index = point_names.index(end_point['name'])

        # 构建图
        G = nx.Graph()

        # 添加节点
        for i, point in enumerate(points_list):
            G.add_node(i,
                       name=point['name'],
                       lat=point['latitude'],
                       lon=point['longitude'],
                       type=point['type'])

        # 添加边（计算直线距离）
        avoid_areas = mission_data['constraints'].get('avoid_areas', [])

        for i in range(len(points_list)):
            for j in range(i + 1, len(points_list)):
                point_i = points_list[i]
                point_j = points_list[j]

                # 计算直线距离（米）
                dist = haversine(
                    (point_i['latitude'], point_i['longitude']),
                    (point_j['latitude'], point_j['longitude'])
                ) * 1000

                # 检查是否穿越禁飞区（简化处理）
                penalty = 0
                for zone in self.nofly_zones:
                    if zone['name'] in avoid_areas:
                        penalty += 5000  # 如果需要避开，增加代价

                weight = dist + penalty
                G.add_edge(i, j, weight=weight, distance=dist)

        return G, points_list, start_index, end_index

    def find_optimal_routes(self, mission_data):
        """寻找最优路径"""
        G, points, start_index, end_index = self.build_graph(mission_data)
        num_uavs = mission_data['number_uavs']

        if num_uavs == 1 or len(points) <= 2:
            # 单无人机：使用改进的TSP算法
            return self.solve_tsp_improved(G, points, start_index, end_index)
        else:
            # 多无人机：车辆路径问题
            return self.solve_vrp(G, points, num_uavs, start_index, end_index)

    def solve_tsp_improved(self, G, points, start_index, end_index):
        """改进的TSP求解算法（使用OR-Tools和局部优化）"""
        if len(points) <= 2:
            if start_index == end_index:
                return [[start_index]]
            else:
                return [[start_index, end_index]]

        # 尝试使用OR-Tools求解
        print("[TSP优化] 尝试使用OR-Tools求解...")
        or_tools_result = self.solve_tsp_or_tools(G, points, start_index, end_index)

        if or_tools_result:
            # 使用OR-Tools求解成功，应用局部优化
            optimized_route = self.optimize_route_with_local_search(G, or_tools_result[0])
            return [optimized_route]
        else:
            # OR-Tools求解失败，使用改进的最近邻算法
            print("[TSP优化] OR-Tools求解失败，使用改进的最近邻算法")
            return self.solve_tsp_fallback(G, points, start_index, end_index)

    def solve_tsp_or_tools(self, G, points, start_index, end_index):
        """使用OR-Tools求解TSP"""
        # 创建距离矩阵
        num_locations = len(points)
        distance_matrix = []

        for i in range(num_locations):
            row = []
            for j in range(num_locations):
                if i == j:
                    row.append(0)
                elif G.has_edge(i, j):
                    # 使用整数距离（米）
                    row.append(int(G[i][j]['distance']))
                else:
                    # 使用一个大数表示不可达
                    row.append(999999)
            distance_matrix.append(row)

        try:
            # 使用OR-Tools求解TSP
            if start_index == end_index:
                # 闭合路径TSP（返回起点）
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, 1, start_index
                )
            else:
                # 开放路径TSP（起点≠终点）
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

            # 设置搜索参数（使用更优的策略）
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()

            # 尝试多种初始解策略
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.CHRISTOFIDES  # 保证3/2近似比
            )

            # 使用更强的局部搜索
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
            )

            # 增加搜索时间
            search_parameters.time_limit.seconds = 5

            # 搜索多个解
            search_parameters.solution_limit = 30

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

                    # 计算这段距离
                    from_node = manager.IndexToNode(previous_index)
                    to_node = manager.IndexToNode(index)
                    route_distance += distance_matrix[from_node][to_node]

                # 添加终点
                route.append(manager.IndexToNode(routing.End(0)))

                print(f"[TSP优化] OR-Tools求解成功，距离: {route_distance:.0f}米")
                return [route]
            else:
                return None

        except Exception as e:
            print(f"[TSP优化] OR-Tools异常: {str(e)}")
            return None

    def solve_tsp_fallback(self, G, points, start_index, end_index):
        """备用算法：改进的最近邻算法"""
        print("[TSP优化] 使用改进的最近邻算法")

        if start_index == end_index:
            # 闭合TSP
            route = self.nearest_neighbor_tsp(G, points, start_index)
        else:
            # 开放TSP
            route = self.nearest_neighbor_open_tsp(G, points, start_index, end_index)

        # 计算初始距离
        initial_distance = self.calculate_route_distance(G, route)
        print(f"[TSP优化] 初始最近邻路径距离: {initial_distance:.0f}米")

        # 应用2-opt优化
        optimized_route = self.two_opt_optimization(G, route)

        # 如果节点较多，应用3-opt优化
        if len(optimized_route) > 10:
            optimized_route = self.three_opt_optimization(G, optimized_route)

        final_distance = self.calculate_route_distance(G, optimized_route)
        improvement = (initial_distance - final_distance) / initial_distance * 100
        print(f"[TSP优化] 优化后路径距离: {final_distance:.0f}米，改善: {improvement:.1f}%")

        return [optimized_route]

    def nearest_neighbor_tsp(self, G, points, start_index):
        """最近邻算法（闭合TSP）"""
        route = [start_index]
        current = start_index
        unvisited = [i for i in range(len(points)) if i != start_index]

        while unvisited:
            # 找到最近的未访问节点
            min_dist = float('inf')
            next_node = None

            for node in unvisited:
                if G.has_edge(current, node):
                    dist = G[current][node]['distance']
                    if dist < min_dist:
                        min_dist = dist
                        next_node = node

            if next_node is None:
                # 如果没有直接连接，选择任意节点
                next_node = unvisited[0]

            route.append(next_node)
            current = next_node
            unvisited.remove(next_node)

        # 返回起点形成闭环
        route.append(start_index)
        return route

    def nearest_neighbor_open_tsp(self, G, points, start_index, end_index):
        """最近邻算法（开放TSP）"""
        route = [start_index]
        current = start_index
        unvisited = [i for i in range(len(points))
                     if i != start_index and i != end_index]

        while unvisited:
            min_dist = float('inf')
            next_node = None

            for node in unvisited:
                if G.has_edge(current, node):
                    dist = G[current][node]['distance']
                    if dist < min_dist:
                        min_dist = dist
                        next_node = node

            if next_node is None:
                next_node = unvisited[0]

            route.append(next_node)
            current = next_node
            unvisited.remove(next_node)

        # 添加终点
        route.append(end_index)
        return route

    def optimize_route_with_local_search(self, G, route):
        """对路径进行局部搜索优化"""
        initial_distance = self.calculate_route_distance(G, route)
        print(f"[TSP优化] OR-Tools初始路径距离: {initial_distance:.0f}米")

        # 应用2-opt优化
        optimized_route = self.two_opt_optimization(G, route)

        # 如果节点较多，应用3-opt优化
        if len(optimized_route) > 10:
            optimized_route = self.three_opt_optimization(G, optimized_route)

        final_distance = self.calculate_route_distance(G, optimized_route)
        improvement = (initial_distance - final_distance) / initial_distance * 100
        print(f"[TSP优化] 局部优化后距离: {final_distance:.0f}米，改善: {improvement:.1f}%")

        return optimized_route

    def two_opt_optimization(self, G, route):
        """2-opt优化算法"""
        best_route = route.copy()
        best_distance = self.calculate_route_distance(G, route)
        improved = True

        iteration = 0
        max_iterations = 100

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    # 尝试2-opt交换
                    new_route = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                    new_distance = self.calculate_route_distance(G, new_route)

                    if new_distance < best_distance - 0.1:  # 小阈值避免浮点误差
                        best_route = new_route
                        best_distance = new_distance
                        improved = True
                        route = best_route.copy()
                        break  # 找到改进就重新开始
                if improved:
                    break

        print(f"[2-opt优化] 迭代{iteration}次")
        return best_route

    def three_opt_optimization(self, G, route):
        """3-opt优化算法（更强大的局部搜索）"""
        best_route = route.copy()
        best_distance = self.calculate_route_distance(G, route)

        n = len(route)
        improved = True
        iteration = 0

        while improved and iteration < 50:
            improved = False
            iteration += 1

            for i in range(1, n - 5):
                for j in range(i + 2, n - 3):
                    for k in range(j + 2, n - 1):
                        # 尝试不同的3-opt交换模式
                        patterns = [
                            # 模式1: 交换两段
                            route[:i] + route[i:j][::-1] + route[j:k] + route[k:],
                            # 模式2: 移动一段
                            route[:i] + route[j:k] + route[i:j] + route[k:],
                            # 模式3: 旋转三段
                            route[:i] + route[j:k] + route[i:j][::-1] + route[k:],
                            # 模式4: 反向旋转
                            route[:i] + route[j:k][::-1] + route[i:j][::-1] + route[k:],
                        ]

                        for new_route in patterns:
                            new_distance = self.calculate_route_distance(G, new_route)
                            if new_distance < best_distance - 0.1:
                                best_route = new_route
                                best_distance = new_distance
                                improved = True
                                route = best_route.copy()
                                break
                    if improved:
                        break
                if improved:
                    break

        print(f"[3-opt优化] 迭代{iteration}次")
        return best_route

    def calculate_route_distance(self, G, route):
        """计算路径总距离"""
        total_distance = 0
        for i in range(len(route) - 1):
            if G.has_edge(route[i], route[i + 1]):
                total_distance += G[route[i]][route[i + 1]]['distance']
            else:
                # 如果没有直接边，估算直线距离
                total_distance += 999999  # 大惩罚值
        return total_distance

    def solve_vrp(self, G, points, num_vehicles, start_index, end_index):
        """解决车辆路径问题（修复多无人机分配）"""
        # 创建距离矩阵
        num_locations = len(points)
        distance_matrix = []

        for i in range(num_locations):
            row = []
            for j in range(num_locations):
                if i == j:
                    row.append(0)
                elif G.has_edge(i, j):
                    # 使用整数距离（米）
                    row.append(int(G[i][j]['distance']))
                else:
                    row.append(999999)
            distance_matrix.append(row)

        # 调试输出：打印距离矩阵信息
        print(f"\n[DEBUG] OR-Tools VRP 求解信息:")
        print(f"  节点数量: {num_locations}")
        print(f"  无人机数量: {num_vehicles}")
        print(f"  起点索引: {start_index} ({points[start_index]['name']})")
        print(f"  终点索引: {end_index} ({points[end_index]['name']})")

        # 检查距离矩阵是否有过大值
        max_distance = np.max(distance_matrix)
        min_distance = np.min([d for row in distance_matrix for d in row if d > 0])
        print(f"  距离矩阵范围: {min_distance} - {max_distance} 米")

        # 检查连通性
        disconnected_pairs = []
        for i in range(num_locations):
            for j in range(num_locations):
                if i != j and distance_matrix[i][j] >= 999999:
                    disconnected_pairs.append((i, j))

        if disconnected_pairs:
            print(f"  警告: 发现 {len(disconnected_pairs)} 个不连通节点对")
            if len(disconnected_pairs) <= 5:
                for i, j in disconnected_pairs[:5]:
                    print(f"    节点 {i}({points[i]['name']}) -> 节点 {j}({points[j]['name']}) 不连通")
        else:
            print(f"  图完全连通")

        # 打印节点信息
        print(f"\n[DEBUG] 节点信息:")
        for i, point in enumerate(points):
            print(f"  节点 {i}: {point['name']} ({point['type']}) - "
                  f"坐标({point['longitude']:.4f}, {point['latitude']:.4f})")

        # 使用OR-Tools解决VRP
        try:
            print(f"\n[DEBUG] 开始OR-Tools求解...")

            # 设置起点和终点
            # 重要：根据起点和终点是否相同选择不同的构造函数
            if start_index == end_index:
                # 所有车辆从同一起点出发并返回同一起点
                print(f"  使用3参数构造函数 (起点=终点)")
                manager = pywrapcp.RoutingIndexManager(
                    num_locations, num_vehicles, start_index
                )
            else:
                # 每辆车都有相同的起点和终点（但起点和终点不同）
                print(f"  使用4参数构造函数 (起点≠终点)")
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
                0,  # 无容量限制
                500000,  # 最大距离限制（米）
                True,  # 开始累积为零
                dimension_name
            )
            distance_dimension = routing.GetDimensionOrDie(dimension_name)

            # 设置每辆车的最大距离
            max_route_distance = 5000
            for vehicle_id in range(num_vehicles):
                distance_dimension.SetCumulVarSoftUpperBound(
                    routing.End(vehicle_id), max_route_distance, 100
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
            search_parameters.log_search = False  # 关闭详细日志减少输出

            # 求解
            solution = routing.SolveWithParameters(search_parameters)

            if solution:
                print(f"[DEBUG] OR-Tools求解成功!")
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

                        # 计算这段距离
                        from_node = manager.IndexToNode(previous_index)
                        to_node = manager.IndexToNode(index)
                        route_distance += distance_matrix[from_node][to_node]

                    # 添加终点（OR-Tools的End节点）
                    route.append(manager.IndexToNode(routing.End(vehicle_id)))
                    routes.append(route)

                    # 统计总距离
                    total_distance += route_distance
                    if len(route) > 2 or (len(route) == 2 and route[0] != route[1]):
                        print(f"  无人机 {vehicle_id + 1}: {len(route)}个节点, {route_distance:.0f}米")
                    else:
                        print(f"  无人机 {vehicle_id + 1}: 空路径或无效路径")

                print(f"  总飞行距离: {total_distance:.0f} 米")

                # 过滤空路径（只包含起点和终点的路径）
                valid_routes = []
                for i, route in enumerate(routes):
                    if len(route) > 2 or (len(route) == 2 and route[0] != route[1]):
                        valid_routes.append(route)
                        print(f"  无人机 {i + 1} 有效路径: {[points[idx]['name'] for idx in route]}")
                    else:
                        print(f"  无人机 {i + 1} 空路径或无效路径")

                # 如果有无效路径，重新分配
                if len(valid_routes) < num_vehicles:
                    print(f"[DEBUG] 警告: {num_vehicles - len(valid_routes)} 架无人机没有分配到任务，使用聚类重新分配")
                    return self.cluster_and_assign_points(points, num_vehicles, start_index, end_index)

                return valid_routes
            else:
                print(f"[DEBUG] OR-Tools求解失败: 未找到可行解")
                print(f"[DEBUG] 回退到聚类分配算法...")
                return self.cluster_and_assign_points(points, num_vehicles, start_index, end_index)

        except Exception as e:
            print(f"[DEBUG] OR-Tools求解过程中发生异常: {str(e)}")
            print(f"[DEBUG] 回退到聚类分配算法...")
            import traceback
            traceback.print_exc()
            return self.cluster_and_assign_points(points, num_vehicles, start_index, end_index)

    def cluster_and_assign_points(self, points, num_uavs, start_index, end_index):
        """使用K-means聚类分配点到各无人机"""
        print(f"[DEBUG] 使用K-means聚类分配点...")
        print(f"  节点总数: {len(points)}")
        print(f"  起点: {points[start_index]['name']} (索引 {start_index})")
        print(f"  终点: {points[end_index]['name']} (索引 {end_index})")

        # 如果只有起点和终点（或点数少于无人机数），为每个无人机创建相同路径
        if len(points) <= 2:
            routes = []
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])  # 单点路径
                else:
                    routes.append([start_index, end_index])
            return routes

        # 提取坐标进行聚类
        coords = []
        indices = []
        for i, point in enumerate(points):
            if i != start_index and i != end_index:  # 排除起点和终点
                coords.append([point['longitude'], point['latitude']])
                indices.append(i)

        print(f"  可聚类点数量: {len(coords)}")

        if not coords:
            # 只有起点和终点
            routes = []
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            return routes

        # 聚类数量等于无人机数量，但不能超过点数
        n_clusters = min(num_uavs, len(coords) + 1)  # +1因为起点终点除外
        print(f"  聚类数量: {n_clusters}")

        # 执行K-means聚类
        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            coords_array = np.array(coords)
            labels = kmeans.fit_predict(coords_array)

            # 将点分配到各个簇
            clusters = [[] for _ in range(n_clusters)]

            # 重建索引映射
            for coord_idx, point_idx in enumerate(indices):
                cluster_idx = labels[coord_idx]
                clusters[cluster_idx].append(point_idx)

            # 统计每个簇的大小
            cluster_sizes = [len(c) for c in clusters]
            print(f"  各簇大小: {cluster_sizes}")

            # 为每个簇创建路径
            routes = []
            for cluster_idx in range(n_clusters):
                route = [start_index]

                # 如果簇中有点，添加到路径中
                if cluster_idx < len(clusters) and clusters[cluster_idx]:
                    # 对簇中的点进行排序（按距离起点远近）
                    cluster_points = clusters[cluster_idx]
                    if len(cluster_points) > 1:
                        # 计算每个点到起点的距离
                        start_coord = (points[start_index]['longitude'], points[start_index]['latitude'])
                        distances = []
                        for point_idx in cluster_points:
                            point_coord = (points[point_idx]['longitude'], points[point_idx]['latitude'])
                            dist = haversine(
                                (start_coord[1], start_coord[0]),
                                (point_coord[1], point_coord[0])
                            ) * 1000
                            distances.append((point_idx, dist))

                        # 按距离排序
                        distances.sort(key=lambda x: x[1])
                        cluster_points_sorted = [x[0] for x in distances]
                        route.extend(cluster_points_sorted)
                    else:
                        route.extend(cluster_points)

                # 始终添加终点（无论是相同还是不同的起点终点）
                if start_index != end_index:
                    route.append(end_index)
                else:
                    # 如果起点和终点相同，也添加终点形成闭环
                    route.append(end_index)

                routes.append(route)
                print(f"  无人机 {cluster_idx + 1} 路径: {[points[idx]['name'] for idx in route]}")

            # 确保返回的路径数量等于无人机数量
            if len(routes) < num_uavs:
                for i in range(num_uavs - len(routes)):
                    if start_index == end_index:
                        routes.append([start_index])
                    else:
                        routes.append([start_index, end_index])

            return routes

        except Exception as e:
            print(f"[DEBUG] K-means聚类失败: {str(e)}")
            # 如果聚类失败，使用简单分配
            return self.split_points_evenly_fallback(points, num_uavs, start_index, end_index)

    def split_points_evenly_fallback(self, points, num_uavs, start_index, end_index):
        """简单的平均分配回退方法"""
        print(f"[DEBUG] 使用简单平均分配...")
        routes = []

        # 获取所有中间点
        middle_points = [i for i in range(len(points)) if i != start_index and i != end_index]

        if not middle_points:
            # 只有起点和终点
            for i in range(num_uavs):
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])
            return routes

        # 平均分配中间点
        points_per_uav = max(1, len(middle_points) // num_uavs)

        for i in range(num_uavs):
            start_idx = i * points_per_uav
            end_idx = start_idx + points_per_uav if i < num_uavs - 1 else len(middle_points)

            if start_idx < len(middle_points):
                route = [start_index]
                route.extend(middle_points[start_idx:end_idx])
                # 始终添加终点
                route.append(end_index)
                routes.append(route)
            else:
                # 没有更多点分配，创建简单路径
                if start_index == end_index:
                    routes.append([start_index])
                else:
                    routes.append([start_index, end_index])

        return routes

    def plot_routes(self, mission_data, routes, points):
        """绘制路径图"""
        # 将points转换为DataFrame以便处理
        points_df = pd.DataFrame(points)
        points_df['type'] = points_df['type'].fillna('unknown')

        # 获取需要避开的区域
        avoid_areas = mission_data['constraints'].get('avoid_areas', [])

        # 创建GeoDataFrame
        geometry = [Point(lon, lat) for lon, lat in zip(points_df['longitude'], points_df['latitude'])]
        mission_gdf = gpd.GeoDataFrame(points_df, geometry=geometry, crs="EPSG:4326")

        # 计算边界
        x_min, y_min, x_max, y_max = mission_gdf.geometry.total_bounds
        center_x, center_y = (x_max + x_min) / 2, (y_max + y_min) / 2
        half_size = max(x_max - x_min, y_max - y_min) / 2 * 1.5

        # 设置图像大小和边界
        fig, ax = plt.subplots(figsize=(12, 10))

        # 计算宽高比，保持和原项目一致
        ratio = 602 / 790
        ax.set_xlim(center_x - half_size, center_x + half_size)
        ax.set_ylim(center_y - half_size * ratio, center_y + half_size * ratio)

        # 添加底图 - 使用OpenStreetMap作为校园地图
        try:
            ctx.add_basemap(ax, crs=mission_gdf.crs, source=self.map_source)
            print("已添加OpenStreetMap底图")
        except Exception as e:
            print(f"添加底图失败: {e}")
            # 如果没有网络或contextily不可用，使用简单网格
            ax.grid(True, alpha=0.3, linestyle='--')

        # 只绘制需要避开的禁飞区
        if avoid_areas:
            print(f"需要避开的禁飞区: {avoid_areas}")

            # 绘制禁飞区
            for zone in self.nofly_zones:
                if zone['name'] in avoid_areas and 'geometry' in zone and zone['geometry']:
                    try:
                        zone_coords = [(lon, lat) for lat, lon in zone['geometry']]
                        if len(zone_coords) >= 3:
                            polygon = patches.Polygon(zone_coords, closed=True,
                                                      alpha=0.3, color='red',
                                                      label='No-Fly Zone' if avoid_areas.index(
                                                          zone['name']) == 0 else "")
                            ax.add_patch(polygon)
                    except Exception as e:
                        print(f"绘制禁飞区 {zone['name']} 失败: {e}")
        else:
            print("当前任务无需避开任何禁飞区")

        # 绘制起点和终点（星形标记）
        # 从任务数据获取起点和终点名称
        start_name = mission_data.get('start_point', '')
        end_name = mission_data.get('end_point', '')

        # 查找起点和终点在points中的索引
        start_index = None
        end_index = None
        for i, point in enumerate(points):
            if point['name'] == start_name:
                start_index = i
            if point['name'] == end_name:
                end_index = i

        # 绘制起点
        if start_index is not None:
            start_point = points[start_index]
            ax.plot(start_point['longitude'], start_point['latitude'],
                    color='red', marker='*', markersize=25,
                    markeredgecolor='black', markeredgewidth=2,
                    label='Start/End Point',
                    zorder=10)

        # 绘制终点（如果与起点不同）
        if end_index is not None and end_index != start_index:
            end_point = points[end_index]
            ax.plot(end_point['longitude'], end_point['latitude'],
                    color='red', marker='*', markersize=25,
                    markeredgecolor='black', markeredgewidth=2,
                    zorder=10)

        # 绘制中间点（POIs） - 只标记路径中的中间点
        poi_types_in_routes = set()
        route_poi_points = []

        for route in routes:
            if len(route) > 2:  # 有中间点
                for idx in route[1:-1]:  # 排除起点和终点
                    if idx < len(points):
                        point = points[idx]
                        # 现在所有点都可以是中间点，不需要排除normal类型
                        poi_types_in_routes.add(point['type'])
                        route_poi_points.append({
                            'longitude': point['longitude'],
                            'latitude': point['latitude'],
                            'type': point['type']
                        })

        # 按类型分组绘制中间点
        if route_poi_points:
            # 为不同类型的POI设置不同颜色
            poi_types_sorted = sorted(list(poi_types_in_routes))
            colors = ['green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'brown']

            # 创建类型到颜色的映射
            type_to_color = {}
            for i, poi_type in enumerate(poi_types_sorted):
                type_to_color[poi_type] = colors[i % len(colors)]

            # 按类型绘制点
            for poi_type in poi_types_sorted:
                type_points = [p for p in route_poi_points if p['type'] == poi_type]
                if type_points:
                    lons = [p['longitude'] for p in type_points]
                    lats = [p['latitude'] for p in type_points]
                    ax.scatter(lons, lats,
                               color=type_to_color[poi_type], marker='o', s=80,
                               edgecolor='black', linewidth=1.5,
                               label=poi_type, zorder=9)

        # 绘制路径
        colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown']
        total_distance = 0
        active_uavs = 0

        for i, route in enumerate(routes):
            if len(route) <= 1:
                continue  # 跳过空路径

            color = colors[i % len(colors)]
            active_uavs += 1

            # 收集路径上的点
            route_points = []
            for idx in route:
                if idx < len(points_df):
                    point = points_df.iloc[idx]
                    route_points.append((point['longitude'], point['latitude']))

            # 绘制路径线
            if len(route_points) >= 2:
                # 创建LineString几何对象
                line = LineString(route_points)
                line_gdf = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")
                line_gdf.plot(ax=ax, color=color, linewidth=2.5,
                              linestyle='-', alpha=0.8, label=f'UAV {i + 1}' if i == 0 else "", zorder=8)

                # 添加箭头
                for j in range(len(route_points) - 1):
                    start_point = route_points[j]
                    end_point = route_points[j + 1]

                    # 计算中点
                    mid_x = (start_point[0] + end_point[0]) / 2
                    mid_y = (start_point[1] + end_point[1]) / 2

                    # 计算方向
                    dx = end_point[0] - start_point[0]
                    dy = end_point[1] - start_point[1]

                    # 添加箭头
                    ax.annotate('', xy=(mid_x + dx * 0.1, mid_y + dy * 0.1),
                                xytext=(mid_x, mid_y),
                                arrowprops=dict(arrowstyle='wedge,tail_width=0.25',
                                                fc=color, ec='black', lw=1.5,
                                                mutation_scale=20), zorder=9)

                # 计算路径距离
                route_distance = 0
                for j in range(len(route_points) - 1):
                    start_point = route_points[j]
                    end_point = route_points[j + 1]
                    dist = haversine((start_point[1], start_point[0]),
                                     (end_point[1], end_point[0])) * 1000
                    route_distance += dist

                total_distance += route_distance

                # 添加路径标签
                if route_points:
                    first_point = route_points[0]
                    ax.text(first_point[0], first_point[1] - 0.00015,
                            f'UAV {i + 1}: {route_distance:.0f}m',
                            fontsize=9, color=color, ha='center',
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))

        # 创建自定义图例
        class HandlerColorLine(HandlerBase):
            def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
                num_stripes = len(orig_handle.get_colors())
                stripe_width = width / num_stripes
                segments = []
                for i, color in enumerate(orig_handle.get_colors()):
                    segment = Line2D([xdescent + i * stripe_width, xdescent + (i + 1) * stripe_width],
                                     [ydescent + height / 2, ydescent + height / 2],
                                     color=color, linewidth=orig_handle.get_linewidth())
                    segment.set_transform(trans)
                    segments.append(segment)
                return segments

        class ColorLine(Line2D):
            def __init__(self, colors, **kwargs):
                super().__init__([0], [0], **kwargs)
                self._colors = colors

            def get_colors(self):
                return self._colors

        # 创建图例元素
        legend_elements = []

        # 起点/终点标记
        legend_elements.append(Line2D([0], [0], marker='*', color='w',
                                      markerfacecolor='red', markeredgecolor='black',
                                      markersize=15, label='Start/End Point'))

        # POI类型标记（只显示在路径中出现的类型）
        if route_poi_points:
            poi_types_sorted = sorted(list(poi_types_in_routes))
            colors = ['green', 'blue', 'orange', 'purple', 'cyan', 'magenta', 'yellow', 'brown']
            for i, poi_type in enumerate(poi_types_sorted[:3]):  # 只显示前3种
                color = colors[i % len(colors)]
                legend_elements.append(Line2D([0], [0], marker='o', color='w',
                                              markerfacecolor=color, markeredgecolor='black',
                                              markersize=10, label=poi_type))

        # UAV路径标记（彩色线条）
        if active_uavs > 0:
            rainbow_colors = colors[:min(active_uavs, 3)]
            colorline = ColorLine(rainbow_colors, linewidth=2)
            legend_elements.append(colorline)

        # 如果有需要避开的禁飞区，添加禁飞区图例
        if avoid_areas:
            legend_elements.append(patches.Patch(facecolor='red', alpha=0.3,
                                                 edgecolor='red', label='No-Fly Zone'))

        # 设置图例标签
        labels = ['Start/End Point']
        if route_poi_points:
            poi_types_sorted = sorted(list(poi_types_in_routes))
            labels.extend([poi_types_sorted[i] for i in range(min(len(poi_types_sorted), 3))])
        if active_uavs > 0:
            labels.append('UAV Routes')
        if avoid_areas:
            labels.append('No-Fly Zone')

        # 添加图例
        if legend_elements:
            ax.legend(legend_elements, labels,
                      handler_map={ColorLine: HandlerColorLine()},
                      loc='lower left', bbox_to_anchor=(0.02, 0.02),
                      fontsize=10, fancybox=True, shadow=True)

        # 设置标题
        mission_type_map = {
            'patrol': 'Patrol',
            'delivery': 'Delivery',
            'inspection': 'Inspection'
        }

        mission_name = mission_type_map.get(mission_data['mission_type'],
                                            mission_data['mission_type'])

        # 在标题中显示需要避开的区域数量
        avoid_info = f", Avoid {len(avoid_areas)} no-fly zone(s)" if avoid_areas else ""
        ax.set_title(f'NUAA Campus UAV {mission_name} Mission ({active_uavs} UAVs active{avoid_info})',
                     fontsize=14, fontweight='bold')

        # 移除坐标轴
        ax.set_axis_off()

        # 保存图像
        plt.tight_layout()
        plt.savefig('./temp/fig_route_nuaa.png', bbox_inches='tight',
                    pad_inches=0.1, dpi=150, facecolor='white')
        plt.close()

        print(f"已保存路径图到 ./temp/fig_route_nuaa.png")
        print(f"总飞行距离: {total_distance:.0f}米")
        print(f"活跃无人机数量: {active_uavs}/{len(routes)}")

    def save_route_to_txt(self, routes, points):
        """保存路径坐标到文本文件"""
        import os
        os.makedirs('./temp', exist_ok=True)

        for route_id, route in enumerate(routes):
            if len(route) <= 1:
                continue  # 跳过空路径

            route_points = []
            for idx in route:
                if idx < len(points):
                    point = points[idx]
                    route_points.append([point['latitude'], point['longitude'], 0])

            if route_points:
                filename = f"./temp/route_coordinates_uav{route_id + 1}.txt"
                np.savetxt(filename, route_points, fmt='%.6f')
                print(f"UAV-{route_id + 1} 路径坐标已保存到 {filename}")

        # 保存所有路径
        all_points = []
        for route_id, route in enumerate(routes):
            if len(route) <= 1:
                continue
            for idx in route:
                if idx < len(points):
                    point = points[idx]
                    all_points.append([point['latitude'], point['longitude'], 0])

        if all_points:
            np.savetxt("./temp/route_coordinates_all.txt", all_points, fmt='%.6f')

    def plan_route(self, mission_data):
        """主规划函数"""
        print("=" * 60)
        print("NUAA Campus UAV Route Planning System (FIXED)")
        print("=" * 60)

        # 填充缺失的字段
        for key in self.default_mission:
            if key not in mission_data:
                mission_data[key] = self.default_mission[key]

        # 打印任务信息
        print(f"\nMission Parameters:")
        print(f"  Start Point: {mission_data['start_point']}")
        print(f"  End Point: {mission_data['end_point']}")
        print(f"  Number of UAVs: {mission_data['number_uavs']}")
        print(f"  Mission Type: {mission_data['mission_type']}")
        print(f"  Waypoints: {mission_data['waypoints']}")
        print(f"  Constraints: {mission_data['constraints']}")
        print("-" * 60)

        # 寻找最优路径
        routes = self.find_optimal_routes(mission_data)

        # 获取所有点
        G, points, start_index, end_index = self.build_graph(mission_data)

        # 打印点信息
        print(f"\n所有节点 ({len(points)}个):")
        for i, point in enumerate(points):
            print(f"  {i}: {point['name']} ({point['type']})")

        # 打印路径信息
        print("\nPlanned Routes:")
        active_routes = 0
        for i, route in enumerate(routes):
            if len(route) > 1 or (len(route) == 1 and start_index != end_index):
                route_names = [points[idx]['name'] for idx in route]
                print(f"  UAV {i + 1}: {' -> '.join(route_names)} (共{len(route)}个点)")
                active_routes += 1
            else:
                print(f"  UAV {i + 1}: 无任务 (原地待命)")

        # 绘制路径
        self.plot_routes(mission_data, routes, points)

        # 保存路径坐标
        self.save_route_to_txt(routes, points)

        print(f"\n任务分配完成: {active_routes}/{len(routes)} 架无人机有任务")
        print("=" * 60)
        print("Route planning completed successfully!")
        print("Check the output files in ./temp/ directory.")
        print("=" * 60)

        return routes, points


def test_planner(task_num=1):
    """测试路径规划器 - 可通过task_num参数选择测试哪个任务"""
    planner = NUAARoutePlanner()

    # 测试任务1：单无人机巡逻
    mission1 = {
        "start_point": "Main_Quad",
        "end_point": "Main_Quad",
        "number_uavs": 1,
        "mission_type": "patrol",
        "waypoints": ["Library", "Sports_Center", "Engineering_Building"],
        "constraints": {
            "avoid_areas": ["Main_Academic_Building"]
        }
    }

    # 测试任务2：双无人机快递配送
    mission2 = {
        "start_point": "West_Field",
        "end_point": "East_Field",  # 东西跨校园配送
        "number_uavs": 2,
        "mission_type": "delivery",
        "waypoints": ["Dormitory_A", "Dormitory_B", "Library", "Cafeteria"],  # 配送点
        "constraints": {
            "avoid_areas": ["Sports_Field"]  # 避开操场区域
        }
    }

    # 测试任务3：三无人机分区巡检
    mission3 = {
        "start_point": "Main_Quad",
        "end_point": "Main_Quad",
        "number_uavs": 3,
        "mission_type": "inspection",
        "waypoints": [],  # 自动分配巡检区域
        "constraints": {
            "avoid_areas": []  # 无特殊避开要求
        }
    }

    # 测试任务4：单无人机紧急医疗物资投送
    mission4 = {
        "start_point": "Sports_Center",
        "end_point": "Dormitory_A",  # 直接送达宿舍A
        "number_uavs": 1,
        "mission_type": "delivery",
        "waypoints": ["Library"],  # 途中在图书馆补充物资
        "constraints": {
            "avoid_areas": ["Main_Academic_Building", "Engineering_Building"]  # 避开教学区
        }
    }

    # 测试任务5：四无人机协同大型活动监控
    mission5 = {
        "start_point": "East_Field",
        "end_point": "West_Field",  # 活动结束后移往西侧
        "number_uavs": 4,
        "mission_type": "patrol",
        "waypoints": ["Sports_Center", "Main_Quad", "Auditorium", "Engineering_Building"],  # 重点监控区域
        "constraints": {
            "avoid_areas": ["Library_Building"]  # 避开图书馆保持安静
        }
    }

    # 任务字典，方便选择
    missions = {
        1: ("单无人机巡逻", mission1),
        2: ("双无人机配送", mission2),
        3: ("三无人机巡检", mission3),
        4: ("单无人机紧急配送", mission4),
        5: ("四无人机协同监控", mission5)
    }

    # 根据task_num选择要测试的任务
    if task_num not in missions:
        print(f"错误: 任务编号 {task_num} 不存在，使用默认任务1")
        task_num = 1

    mission_name, mission_data = missions[task_num]
    print(f"\n测试任务{task_num}: {mission_name}")
    print("=" * 60)

    routes, points = planner.plan_route(mission_data)
    return routes


if __name__ == "__main__":
    # 在这里直接修改task_num的值来选择要测试的任务
    # 可选值: 1, 2, 3, 4, 5

    task_num = 1  # 修改这里来选择要测试的任务

    test_planner(task_num)
