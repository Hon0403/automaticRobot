import math
from queue import PriorityQueue

class PathPlanner:
    def __init__(self):
        self.grid = {}
        self.cell_size = 1
        self.connection_points = []

    def initialize_grid(self, map_memory):
        """初始化地圖網格"""
        self.cell_size = map_memory.cell_size
        
        # 從地圖記憶中獲取已探索區域
        for cell in map_memory.explored_cells:
            x, y = cell
            self.grid[(x, y)] = {"type": "walkable"}
        
        # 標記障礙物
        for key, value in map_memory.map_grid.items():
            if value["type"] == "obstacle":
                x, y = map(int, key.split(','))
                self.grid[(x, y)] = {"type": "obstacle"}

    def identify_connection_points(self, map_memory):
        """識別連接不同高度平台的特殊點"""
        self.connection_points = []
        
        # 添加繩索
        for key, value in map_memory.ropes.items():
            position = value["position"]
            self.connection_points.append({
                "type": "rope",
                "position": position,
                "connects": self._find_connected_platforms(position)
            })
        
        # 添加傳送點
        for key, value in map_memory.portals.items():
            position = value["position"]
            self.connection_points.append({
                "type": "portal",
                "position": position,
                "connects": self._find_connected_platforms(position)
            })

    def find_path(self, start, goal):
        """使用A*算法尋找路徑"""
        start = self._to_grid_coords(start)
        goal = self._to_grid_coords(goal)

        open_set = PriorityQueue()
        open_set.put((0, start))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}

        while not open_set.empty():
            current = open_set.get()[1]

            if current == goal:
                return self.reconstruct_path(came_from, current)

            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + self.distance(current, neighbor)

                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + self.heuristic(neighbor, goal)
                    open_set.put((f_score[neighbor], neighbor))

        return None  # 沒有找到路徑

    def heuristic(self, a, b):
        """計算啟發函數（曼哈頓距離）"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def distance(self, a, b):
        """計算兩點間的實際距離"""
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

    def get_neighbors(self, node):
        """獲取當前節點的鄰居節點，考慮平台限制"""
        x, y = node
        step_size = 1
        
        # 基本移動：左右
        neighbors = [
            (x + step_size, y),  # 右
            (x - step_size, y)   # 左
        ]
        
        # 檢查是否可以向下移動（平台邊緣）
        if not self._is_walkable((x, y + step_size)):
            # 如果下方不可行走，檢查是否有繩索
            rope = self._find_rope_at((x, y))
            if rope:
                # 可以沿繩索上下移動
                neighbors.append((x, y - step_size))  # 上
                neighbors.append((x, y + step_size))  # 下
        else:
            # 下方可行走，可以向下移動
            neighbors.append((x, y + step_size))  # 下
        
        # 檢查是否可以跳躍
        if self._can_jump_from(node):
            jump_height = 2 * step_size  # 跳躍高度
            neighbors.append((x, y - jump_height))  # 跳躍
        
        # 檢查是否有傳送點
        portal = self._find_portal_at((x, y))
        if portal and "destination" in portal:
            neighbors.append(portal["destination"])  # 傳送
        
        # 過濾掉不可行走的節點
        return [n for n in neighbors if self._is_walkable(n)]

    def _is_walkable(self, position):
        """檢查位置是否可行走"""
        x, y = position
        cell = (int(x / self.cell_size), int(y / self.cell_size))
        return cell in self.grid and self.grid[cell]["type"] != "obstacle"

    def _can_jump_from(self, position):
        """檢查是否可以從當前位置跳躍"""
        x, y = position
        
        # 確保角色站在平台上
        below = (x, y + self.cell_size)
        if not self._is_platform(below):
            return False
        
        # 確保上方有空間
        above = (x, y - self.cell_size)
        return self._is_walkable(above)

    def _is_platform(self, position):
        """檢查位置是否為平台"""
        x, y = position
        cell = (int(x / self.cell_size), int(y / self.cell_size))
        
        # 如果該位置是可行走區域但下方是空氣，則為平台
        if cell in self.grid and self.grid[cell]["type"] == "walkable":
            below = (int(x / self.cell_size), int(y / self.cell_size) + 1)
            return below not in self.grid or self.grid[below]["type"] != "walkable"
        return False

    def _find_rope_at(self, position):
        """在指定位置查找繩索"""
        for point in self.connection_points:
            if point["type"] == "rope" and point["position"] == position:
                return point
        return None

    def _find_portal_at(self, position):
        """在指定位置查找傳送點"""
        for point in self.connection_points:
            if point["type"] == "portal" and point["position"] == position:
                return point
        return None

    def _find_connected_platforms(self, position):
        """找出特殊點連接的平台"""
        # 這個方法需要根據遊戲的具體邏輯來實現
        # 例如，對於繩索，可以返回繩索頂部和底部的平台
        # 對於傳送點，可以返回傳送的目標位置
        return []

    def reconstruct_path(self, came_from, current):
        """重建路徑"""
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return list(reversed(total_path))

    def smooth_path(self, path):
        """平滑路徑，考慮跳躍和繩索"""
        if len(path) < 3:
            return path
        
        result = [path[0]]
        current_index = 0
        
        while current_index < len(path) - 1:
            # 檢查是否可以直接跳躍到更遠的點
            for i in range(len(path) - 1, current_index, -1):
                # 如果可以跳躍到達
                if self._can_reach_by_jumping(path[current_index], path[i]):
                    result.append({"action": "jump", "position": path[i]})
                    current_index = i
                    break
                # 如果可以通過繩索到達
                elif self._can_reach_by_rope(path[current_index], path[i]):
                    result.append({"action": "use_rope", "position": path[i]})
                    current_index = i
                    break
                # 如果可以通過傳送點到達
                elif self._can_reach_by_portal(path[current_index], path[i]):
                    result.append({"action": "use_portal", "position": path[i]})
                    current_index = i
                    break
                # 如果有直線視線
                elif self.has_clear_line(path[current_index], path[i]):
                    result.append({"action": "move", "position": path[i]})
                    current_index = i
                    break
            else:
                # 如果沒有找到可以直接到達的點，則添加下一個點
                current_index += 1
                if current_index < len(path):
                    result.append({"action": "move", "position": path[current_index]})
        
        return result

    def has_clear_line(self, start, end):
        """檢查兩點之間是否有清晰的視線"""
        x1, y1 = start
        x2, y2 = end
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        x = x1
        y = y1
        n = 1 + dx + dy
        x_inc = 1 if x2 > x1 else -1
        y_inc = 1 if y2 > y1 else -1
        error = dx - dy
        dx *= 2
        dy *= 2

        for _ in range(n):
            if not self._is_walkable((x, y)):
                return False
            if error > 0:
                x += x_inc
                error -= dy
            else:
                y += y_inc
                error += dx

        return True

    def _to_grid_coords(self, position):
        """將世界坐標轉換為網格坐標"""
        return (int(position[0] / self.cell_size), int(position[1] / self.cell_size))

    def _can_reach_by_jumping(self, start, end):
        """檢查是否可以通過跳躍從起點到達終點"""
        # 這個方法需要根據遊戲的具體跳躍機制來實現
        return False

    def _can_reach_by_rope(self, start, end):
        """檢查是否可以通過繩索從起點到達終點"""
        # 查找起點附近的繩索
        rope = None
        for point in self.connection_points:
            if point["type"] == "rope":
                rope_pos = point["position"]
                # 檢查繩索是否在起點附近
                if abs(rope_pos[0] - start[0]) < 30:
                    rope = point
                    break
    
        if not rope:
            return False
    
        # 檢查終點是否在繩索的垂直範圍內
        rope_pos = rope["position"]
        if abs(rope_pos[0] - end[0]) > 30:
            return False
    
        # 檢查終點是否在繩索的上方或下方
        min_y = min(rope["connects"]) if rope["connects"] else rope_pos[1] - 200
        max_y = max(rope["connects"]) if rope["connects"] else rope_pos[1] + 200
    
        return min_y <= end[1] <= max_y

    def _can_reach_by_portal(self, start, end):
        """檢查是否可以通過傳送點從起點到達終點"""
        # 查找起點附近的傳送點
        portal = None
        for point in self.connection_points:
            if point["type"] == "portal":
                portal_pos = point["position"]
                # 檢查傳送點是否在起點附近
                if self._distance(portal_pos, start) < 50:
                    portal = point
                    break
    
        if not portal or "destination" not in portal:
            return False
    
        # 檢查終點是否在傳送目的地附近
        destination = portal["destination"]
        return self._distance(destination, end) < 100

    def _distance(self, pos1, pos2):
        """計算兩點之間的距離"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5

    def heuristic(self, a, b, weight=1.2):
        """計算帶權重的啟發式函數（曼哈頓距離）"""
        # 增加權重參數，值大於1會使算法更傾向於找到目標，但可能不是最短路徑
        # 值小於1會使算法更傾向於找到最短路徑，但搜索時間更長
        return weight * (abs(a[0] - b[0]) + abs(a[1] - b[1]))

    def find_path_multilevel(self, start, goal):
        """多層尋路 - 先計算區域間路徑，再細化"""
        # 將起點和終點轉換為區域坐標
        region_size = 10  # 每個區域包含10x10個網格
        start_region = (int(start[0] / (self.cell_size * region_size)), 
                        int(start[1] / (self.cell_size * region_size)))
        goal_region = (int(goal[0] / (self.cell_size * region_size)), 
                       int(goal[1] / (self.cell_size * region_size)))
    
        # 如果起點和終點在同一區域，直接使用細粒度尋路
        if start_region == goal_region:
            return self.find_path(start, goal)
    
        # 計算區域間的路徑
        region_path = self._find_region_path(start_region, goal_region)
        if not region_path:
            return None
    
        # 細化路徑
        detailed_path = [start]
        current_pos = start
    
        for i in range(1, len(region_path)):
            # 計算當前區域的中心點
            region_center = (
                (region_path[i][0] + 0.5) * self.cell_size * region_size,
                (region_path[i][1] + 0.5) * self.cell_size * region_size
            )
        
            # 找到從當前位置到區域中心的路徑
            segment_path = self.find_path(current_pos, region_center)
            if segment_path:
                detailed_path.extend(segment_path[1:])  # 跳過第一個點（重複）
                current_pos = segment_path[-1]
    
        # 最後從最後一個區域中心到目標點
        final_segment = self.find_path(current_pos, goal)
        if final_segment:
            detailed_path.extend(final_segment[1:])
    
        return detailed_path

    def _find_region_path(self, start_region, goal_region):
        """計算區域層級的路徑"""
        # 使用簡化版的A*算法計算區域間路徑
        open_set = PriorityQueue()
        open_set.put((0, start_region))
        came_from = {}
        g_score = {start_region: 0}
        f_score = {start_region: self._region_heuristic(start_region, goal_region)}
    
        while not open_set.empty():
            current = open_set.get()[1]
        
            if current == goal_region:
                return self._reconstruct_region_path(came_from, current)
        
            for neighbor in self._get_region_neighbors(current):
                tentative_g_score = g_score[current] + 1  # 區域間距離簡化為1
            
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + self._region_heuristic(neighbor, goal_region)
                    open_set.put((f_score[neighbor], neighbor))
    
        return None

    def _region_heuristic(self, a, b):
        """區域間的啟發式函數"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _get_region_neighbors(self, region):
        """獲取相鄰區域"""
        x, y = region
        neighbors = [
            (x+1, y), (x-1, y), (x, y+1), (x, y-1)
        ]
        return [n for n in neighbors if self._is_region_walkable(n)]

    def _is_region_walkable(self, region):
        """檢查區域是否可行走（至少有一個可行走的網格）"""
        region_size = 10
        for dx in range(region_size):
            for dy in range(region_size):
                grid_x = region[0] * region_size + dx
                grid_y = region[1] * region_size + dy
                if self._is_walkable((grid_x, grid_y)):
                    return True
        return False

    def _reconstruct_region_path(self, came_from, current):
        """重建區域路徑"""
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return list(reversed(total_path))
