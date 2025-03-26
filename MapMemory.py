import os
import pickle
import time
import math

class MapMemory:
    def __init__(self, cell_size=50, save_path="map_data"):
        self.cell_size = cell_size
        self.save_path = save_path
        self.map_grid = {}
        self.current_map_id = "unknown"
        self.player_positions = []
        self.portals = {}
        self.ropes = {}
        self.explored_cells = set()  # 新增探索記錄
        
        os.makedirs(save_path, exist_ok=True)

    def is_position_explored(self, position):
        """檢查位置是否已被探索"""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        return (cell_x, cell_y) in self.explored_cells

    def get_nearby_objects(self, position, radius=5):
        """獲取附近物體（修正版）"""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        
        nearby = []
        
        # 檢查周圍網格
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                check_cell = (cell_x + dx, cell_y + dy)
                
                # 檢查傳送點
                if check_cell in self.portals:
                    nearby.append({
                        "type": "portal",
                        "position": self.portals[check_cell]["position"]
                    })
                
                # 檢查繩索
                if check_cell in self.ropes:
                    nearby.append({
                        "type": "rope",
                        "position": self.ropes[check_cell]["position"]
                    })
        
        return nearby

    def update_player_position(self, position):
        """更新玩家位置並標記探索區域"""
        x, y = position
        cell_x = int(x / self.cell_size)
        cell_y = int(y / self.cell_size)
        
        # 標記當前網格為已探索
        self.explored_cells.add((cell_x, cell_y))
        
        # 原始更新邏輯保持不變
        if not self.player_positions or self._distance(self.player_positions[-1], position) > 20:
            self.player_positions.append(position)
            key = f"{cell_x},{cell_y}"
            self.map_grid[key] = {"type": "explored", "time": time.time()}
    
    def update_player_position(self, position):
        """更新玩家位置"""
        x, y = position
        # 避免記錄過於頻繁的位置
        if not self.player_positions or self._distance(self.player_positions[-1], position) > 20:
            self.player_positions.append(position)
            
            # 標記已探索區域
            cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
            key = f"{cell_x},{cell_y}"
            self.map_grid[key] = {"type": "explored", "time": time.time()}
    
    def add_object(self, obj_type, position, obj_data=None):
        """添加遊戲物件（傳送點、繩索等）"""
        x, y = position
        cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
        key = f"{cell_x},{cell_y}"
        
        if obj_type == "portal":
            self.portals[key] = {"position": position, "data": obj_data, "time": time.time()}
        elif obj_type == "rope":
            self.ropes[key] = {"position": position, "data": obj_data, "time": time.time()}
        
        # 更新網格
        self.map_grid[key] = {"type": obj_type, "time": time.time()}
    
    def get_nearby_objects(self, position, radius=5):
        """獲取玩家附近的物件"""
        x, y = position
        cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
        
        nearby = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                key = f"{cell_x + dx},{cell_y + dy}"
                if key in self.map_grid:
                    obj_type = self.map_grid[key]["type"]
                    if obj_type == "portal" and key in self.portals:
                        nearby.append({"type": "portal", "position": self.portals[key]["position"]})
                    elif obj_type == "rope" and key in self.ropes:
                        nearby.append({"type": "rope", "position": self.ropes[key]["position"]})
        
        return nearby
    
    def is_position_walkable(self, position):
        """檢查位置是否可行走（根據已探索數據）"""
        x, y = position
        cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
        key = f"{cell_x},{cell_y}"
        
        # 如果該區域已被標記為障礙物，則不可行走
        if key in self.map_grid and self.map_grid[key]["type"] == "obstacle":
            return False
        
        return True
    
    def save_map(self):
        """保存當前地圖數據"""
        if self.current_map_id == "unknown":
            return
            
        data = {
            "map_grid": self.map_grid,
            "player_positions": self.player_positions,
            "portals": self.portals,
            "ropes": self.ropes
        }
        
        map_file = os.path.join(self.save_path, f"{self.current_map_id}.pickle")
        with open(map_file, 'wb') as f:
            pickle.dump(data, f)
    
    def load_map(self):
        """載入指定地圖數據"""
        map_file = os.path.join(self.save_path, f"{self.current_map_id}.pickle")
        
        # 清空現有數據
        self.map_grid = {}
        self.player_positions = []
        self.portals = {}
        self.ropes = {}
        
        # 如果存在保存的數據，則加載
        if os.path.exists(map_file):
            with open(map_file, 'rb') as f:
                data = pickle.load(f)
                self.map_grid = data["map_grid"]
                self.player_positions = data["player_positions"]
                self.portals = data["portals"]
                self.ropes = data["ropes"]
    
    def _distance(self, pos1, pos2):
        """計算兩點之間的距離"""
        return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2) ** 0.5
    
    def detect_platform_edges(self):
        """檢測平台邊緣"""
        platform_edges = {}
    
        # 遍歷已探索區域
        for cell_x, cell_y in self.explored_cells:
            key = f"{cell_x},{cell_y}"
        
            # 檢查是否為平台
            if key in self.map_grid and self.map_grid[key]["type"] == "explored":
                # 檢查下方是否為空氣（平台邊緣）
                below_key = f"{cell_x},{cell_y+1}"
                if below_key not in self.map_grid:
                    # 這是一個平台邊緣
                    if cell_y not in platform_edges:
                        platform_edges[cell_y] = []
                    platform_edges[cell_y].append(cell_x)
    
        # 合併相鄰的邊緣點形成完整平台
        platforms = []
        for y_level, x_points in platform_edges.items():
            x_points.sort()
            current_platform = {"y_level": y_level * self.cell_size, "x_min": x_points[0] * self.cell_size}
        
            for i in range(1, len(x_points)):
                if x_points[i] > x_points[i-1] + 1:  # 不連續的點
                    current_platform["x_max"] = x_points[i-1] * self.cell_size
                    platforms.append(current_platform)
                    current_platform = {"y_level": y_level * self.cell_size, "x_min": x_points[i] * self.cell_size}
        
            current_platform["x_max"] = x_points[-1] * self.cell_size
            platforms.append(current_platform)
    
        return platforms
    
    def update_terrain_feature(self, position, feature_type, data=None):
        """動態更新地形特徵"""
        x, y = position
        cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
        key = f"{cell_x},{cell_y}"
    
        # 更新網格信息
        if feature_type == "platform":
            # 標記為平台
            self.map_grid[key] = {"type": "platform", "time": time.time(), "data": data}
        elif feature_type == "obstacle":
            # 標記為障礙物
            self.map_grid[key] = {"type": "obstacle", "time": time.time(), "data": data}
        elif feature_type == "gap":
            # 標記為間隙（不可行走）
            self.map_grid[key] = {"type": "gap", "time": time.time(), "data": data}
    
        # 標記為已探索
        self.explored_cells.add((cell_x, cell_y))
    
        # 更新相關連接點
        self._update_connection_points()

    def _update_connection_points(self):
        """更新連接點信息（繩索和傳送點的連接平台）"""
        # 遍歷所有繩索和傳送點
        for key, value in self.ropes.items():
            position = value["position"]
            x, y = position
            cell_x, cell_y = int(x / self.cell_size), int(y / self.cell_size)
        
            # 查找繩索上下連接的平台
            platforms = []
        
            # 向上查找平台
            for dy in range(-20, 0):
                check_key = f"{cell_x},{cell_y+dy}"
                if check_key in self.map_grid and self.map_grid[check_key]["type"] == "platform":
                    platforms.append((cell_x, cell_y+dy))
                    break
        
            # 向下查找平台
            for dy in range(1, 21):
                check_key = f"{cell_x},{cell_y+dy}"
                if check_key in self.map_grid and self.map_grid[check_key]["type"] == "platform":
                    platforms.append((cell_x, cell_y+dy))
                    break
        
            # 更新繩索連接的平台信息
            self.ropes[key]["connects"] = platforms


