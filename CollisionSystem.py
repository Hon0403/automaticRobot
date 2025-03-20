class CollisionBox:
    def __init__(self, x, y, width, height, obj_type, obj_data=None):
        """
        初始化碰撞邊界盒
        
        參數：
            x, y: 邊界盒中心座標
            width, height: 邊界盒的寬和高
            obj_type: 物體類型
            obj_data: 額外數據
        """
        self.x1 = x - width / 2
        self.y1 = y - height / 2
        self.x2 = x + width / 2
        self.y2 = y + height / 2
        self.type = obj_type
        self.data = obj_data
    
    def check_collision(self, other):
        """檢查與另一個邊界盒的碰撞"""
        return (self.x1 < other.x2 and 
                self.x2 > other.x1 and 
                self.y1 < other.y2 and 
                self.y2 > other.y1)
    
    def contains_point(self, point):
        """檢查邊界盒是否包含點"""
        x, y = point
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2
    
    def get_center(self):
        """獲取邊界盒中心點"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


class CollisionSystem:
    def __init__(self, map_memory):
        """
        初始化碰撞系統
        
        參數：
            map_memory: 地圖記憶系統實例
        """
        self.map_memory = map_memory
        self.collision_boxes = []
        self.player_box = None
    
    def update_from_detections(self, detections, coordinate_transformer):
        """從檢測結果更新碰撞盒"""
        self.collision_boxes = []
        
        for detection in detections:
            obj_class = detection["class"]
            
            # 轉換座標到世界坐標
            world_pos = coordinate_transformer.screen_to_world(
                (detection["x_center"], detection["y_center"])
            )
            
            if not world_pos:
                continue
                
            x, y = world_pos
            width = detection["width"] * 1.2  # 放大20%，更寬鬆的碰撞檢測
            height = detection["height"] * 1.2
            
            # 創建不同類型的碰撞盒
            if obj_class == "minimap_player":
                self.player_box = CollisionBox(x, y, width, height, "player", detection)
                
                # 更新玩家位置到地圖記憶系統
                self.map_memory.update_player_position((x, y))
                
            elif obj_class == "minimap_portal" or obj_class == "game_portal":
                collision_box = CollisionBox(x, y, width, height, "portal", detection)
                self.collision_boxes.append(collision_box)
                
                # 添加到地圖記憶
                self.map_memory.add_object("portal", (x, y), detection)
                
            elif obj_class == "climbable_object":
                collision_box = CollisionBox(x, y, width, height * 1.5, "rope", detection)  # 繩索碰撞盒高度更大
                self.collision_boxes.append(collision_box)
                
                # 添加到地圖記憶
                self.map_memory.add_object("rope", (x, y), detection)
    
    def check_player_collisions(self):
        """檢查玩家與所有物件的碰撞"""
        if not self.player_box:
            return []
            
        collisions = []
        for box in self.collision_boxes:
            if self.player_box.check_collision(box):
                collisions.append({"type": box.type, "position": box.get_center(), "data": box.data})
        
        return collisions
    
    def is_player_near_object(self, obj_type, distance=100):
        """檢查玩家是否靠近特定類型的物件"""
        if not self.player_box:
            return False
            
        player_center = self.player_box.get_center()
        
        for box in self.collision_boxes:
            if box.type == obj_type:
                box_center = box.get_center()
                dist = ((player_center[0] - box_center[0]) ** 2 + 
                        (player_center[1] - box_center[1]) ** 2) ** 0.5
                if dist <= distance:
                    return True
        return False
