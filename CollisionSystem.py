import math
import cv2

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
            try:
                # 檢查是使用 'class_name' 還是 'class' 鍵
                if "class_name" in detection:
                    obj_class = detection["class_name"]
                elif "class" in detection:
                    obj_class = detection["class"]
                else:
                    continue

                # 檢查是使用 'bbox' 還是 'box' 鍵
                if "bbox" in detection:
                    x1, y1, x2, y2 = detection["bbox"]
                elif "box" in detection:
                    x1, y1, x2, y2 = detection["box"]
                else:
                    continue

                # 計算中心點
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2

                # 轉換座標到世界坐標
                world_pos = coordinate_transformer.screen_to_world(
                    (x_center, y_center)
                )
                
                if not world_pos:
                    continue
                    
                x, y = world_pos
                
                # 計算寬度和高度
                width = (x2 - x1) * 1.2  # 放大20%，更寬鬆的碰撞檢測
                height = (y2 - y1) * 1.2
                
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
                    collision_box = CollisionBox(x, y, width, height * 1.5, "rope", detection)
                    self.collision_boxes.append(collision_box)
                    # 添加到地圖記憶
                    self.map_memory.add_object("rope", (x, y), detection)
                # 地形識別 - 添加平台類型處理
                elif obj_class == "ground" or obj_class == "platform":
                    collision_box = CollisionBox(x, y, width, height, "platform", detection)
                    self.collision_boxes.append(collision_box)
                    # 添加到地圖記憶
                    self.map_memory.update_terrain_feature((x, y), "platform", detection)
            except Exception as e:
                print(f"處理碰撞盒時發生錯誤: {str(e)}")

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

    def predict_obstacle_collision(self, start_pos, direction, distance=100):
        """預測給定方向上是否會碰到障礙物"""
        step_size = 10  # 每步檢查的距離
        steps = int(distance / step_size)
        
        # 計算方向向量
        dir_x = 1 if direction == "right" else -1 if direction == "left" else 0
        dir_y = 1 if direction == "down" else -1 if direction == "up" else 0
        
        # 逐步檢查路徑上的點
        for i in range(1, steps + 1):
            check_x = start_pos[0] + dir_x * step_size * i
            check_y = start_pos[1] + dir_y * step_size * i
            check_pos = (check_x, check_y)
            
            # 創建一個臨時的碰撞盒來檢查碰撞
            temp_box = CollisionBox(check_x, check_y, 20, 20, "temp")
            
            # 檢查是否與任何障礙物碰撞
            for box in self.collision_boxes:
                if box.type == "obstacle" and temp_box.check_collision(box):
                    return {
                        "collision": True,
                        "position": check_pos,
                        "distance": step_size * i,
                        "obstacle": box
                    }
                    
        # 沒有檢測到碰撞
        return {"collision": False}

    def detect_platform_gaps(self, start_pos, direction, max_distance=150, visualization_img=None, terrain_objects=None):
        """檢測前方是否有平台間隙"""
        print(f"執行平台間隙檢測: 起始位置={start_pos}, 方向={direction}")
        
        # 使用傳入的地形物件或收集已知的平台
        platforms = []
        if terrain_objects:
            platforms = terrain_objects
        else:
            # 取得所有平台碰撞盒（原有方法）
            platforms = [box for box in self.collision_boxes if box.type == "platform"]
        
        print(f"目前平台數量: {len(platforms)}")
        
        if not platforms:
            print("未找到平台，無法檢測間隙")
            return {"gap": False}
            
        # 計算方向向量
        dir_x = 1 if direction == "right" else -1
        
        # 用於可視化的顏色
        ray_color = (0, 255, 255)  # 黃色
        hit_color = (0, 255, 0)    # 綠色
        gap_color = (0, 0, 255)    # 紅色
        
        # 標記起始點
        if visualization_img is not None:
            cv2.circle(visualization_img, 
                      (int(start_pos[0]), int(start_pos[1])), 
                      5, (255, 0, 0), -1)
        
        # 從玩家位置向前檢測
        for i in range(1, int(max_distance / 10) + 1):
            check_x = start_pos[0] + dir_x * 10 * i
            check_y = start_pos[1]
            
            # 如果提供了可視化圖像，繪製水平射線
            if visualization_img is not None:
                cv2.line(visualization_img, 
                        (int(start_pos[0]), int(start_pos[1])), 
                        (int(check_x), int(check_y)), 
                        ray_color, 1)
            
            # 向下檢測
            has_ground = False
            for j in range(1, 15):  # 向下檢測更多單位
                down_y = check_y + j * 10
                
                # 如果提供了可視化圖像，繪製垂直射線
                if visualization_img is not None:
                    cv2.line(visualization_img, 
                            (int(check_x), int(check_y)), 
                            (int(check_x), int(down_y)), 
                            ray_color, 1)
                
                # 檢查該點下方是否有地面
                for platform in platforms:
                    # 處理不同格式的平台數據
                    if hasattr(platform, 'type') and platform.type == "platform":
                        # 碰撞盒對象
                        if platform.contains_point((check_x, down_y)):
                            has_ground = True
                            if visualization_img is not None:
                                cv2.circle(visualization_img, 
                                        (int(check_x), int(down_y)), 
                                        3, hit_color, -1)
                            break
                    else:
                        # 直接使用檢測結果
                        bbox = platform.get("bbox", [])
                        if len(bbox) == 4:
                            x1, y1, x2, y2 = bbox
                            if x1 <= check_x <= x2 and y1 <= down_y <= y2:
                                has_ground = True
                                if visualization_img is not None:
                                    cv2.circle(visualization_img, 
                                            (int(check_x), int(down_y)), 
                                            3, hit_color, -1)
                                break
                
                if has_ground:
                    break
            
            if not has_ground:
                # 如果提供了可視化圖像，標記間隙點
                if visualization_img is not None:
                    cv2.circle(visualization_img, 
                              (int(check_x), int(check_y)), 
                              5, gap_color, -1)
                    cv2.putText(visualization_img, 
                               "間隙!", 
                               (int(check_x), int(check_y) - 10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, gap_color, 2)
                
                print(f"在位置({check_x}, {check_y})檢測到平台間隙!")
                return {"gap": True, "position": (check_x, check_y)}
        
        print("未檢測到平台間隙")
        return {"gap": False}

    def detect_platform_gap(self, start_pos, direction, max_distance=100):
        """檢測前方是否有平台間隙（別名，保持兼容性）"""
        return self.detect_platform_gaps(start_pos, direction, max_distance)

    def draw_ray_detection(self, image, start_pos, hits, direction="right", max_distance=150, ray_color=(0, 255, 255), hit_color=(255, 0, 0)):
        """視覺化射線檢測結果"""
        # 複製輸入圖像以避免直接修改原圖
        result = image.copy()
        start_x, start_y = int(start_pos[0]), int(start_pos[1])
        
        # 確定射線方向角度
        angle_dict = {
            "right": 0,
            "up": -90,
            "left": 180,
            "down": 90
        }
        base_angle = angle_dict.get(direction, 0)
        
        # 為了視覺效果，繪製多條射線
        ray_count = 5  # 繪製5條射線
        ray_spread = 30  # 射線扇形範圍
        
        for i in range(ray_count):
            # 計算當前射線角度
            angle_offset = ray_spread * (i / (ray_count - 1) - 0.5) if ray_count > 1 else 0
            angle = base_angle + angle_offset
            radian = math.radians(angle)
            
            # 計算射線終點
            end_x = int(start_x + max_distance * math.cos(radian))
            end_y = int(start_y + max_distance * math.sin(radian))
            
            # 繪製射線
            cv2.line(result, (start_x, start_y), (end_x, end_y), ray_color, 1, cv2.LINE_AA)
        
        # 繪製碰撞點
        for hit in hits:
            hit_x, hit_y = int(hit[0]), int(hit[1])
            cv2.circle(result, (hit_x, hit_y), 5, hit_color, -1)
            # 從起點到碰撞點繪製線段
            cv2.line(result, (start_x, start_y), (hit_x, hit_y), hit_color, 2, cv2.LINE_AA)
        
        return result
