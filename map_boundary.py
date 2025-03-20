import math

class MapBoundaryManager:
    def __init__(self, initial_bounds=(0, 0, 5000, 3000)):
        self.x_min, self.y_min, self.x_max, self.y_max = initial_bounds
        self.visited_positions = []  # 記錄已訪問位置
        self.dynamic_bounds = initial_bounds  # 動態邊界
        
    def update_from_position(self, position):
        """根據當前位置更新邊界"""
        x, y = position
        # 添加緩衝區
        buffer = 500  # 在已知位置周圍添加緩衝區
        
        # 更新邊界
        self.x_min = min(self.x_min, x - buffer)
        self.y_min = min(self.y_min, y - buffer)
        self.x_max = max(self.x_max, x + buffer)
        self.y_max = max(self.y_max, y + buffer)
        
        # 記錄位置
        self.visited_positions.append((x, y))
        self.dynamic_bounds = (self.x_min, self.y_min, self.x_max, self.y_max)
        
    def update_from_detections(self, detections, coordinate_transformer):
        """根據檢測到的物體更新邊界"""
        for detection in detections:
            if detection["class"] in ["wall", "obstacle", "platform", "portal"]:
                # 轉換為世界坐標
                world_pos = coordinate_transformer.screen_to_world(
                    (detection["x_center"], detection["y_center"])
                )
                self.update_from_position(world_pos)
        
    def get_current_bounds(self):
        """獲取當前邊界"""
        return self.dynamic_bounds
    
    def is_within_bounds(self, position, margin=100):
        """檢查位置是否在邊界內（帶邊緣檢測）"""
        x, y = position
        return (self.x_min + margin <= x <= self.x_max - margin and
                self.y_min + margin <= y <= self.y_max - margin)
