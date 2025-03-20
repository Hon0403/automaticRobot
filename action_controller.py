import time
import random
import math
import win32api
import win32con
import numpy as np
from path_planner import PathPlanner

class ActionController:
    def __init__(self, window_capture, detector, coordinate_transformer, quad_tree):
        self.window_capture = window_capture
        self.detector = detector
        self.coordinate_transformer = coordinate_transformer
        self.quad_tree = quad_tree
        
        # 按鍵控制
        self.key_press_time = 0.1  # 按鍵按下時間（秒）
        self.direction_keys = {
            "up": 0x26,    # VK_UP
            "down": 0x28,  # VK_DOWN
            "left": 0x25,  # VK_LEFT
            "right": 0x27, # VK_RIGHT
            "jump": 0x41   # 'A' key for jump - 可根據遊戲更改
        }

        # 移動狀態追蹤
        self.last_position = None
        self.stuck_counter = 0
        self.max_stuck_count = 5  # 連續5次位置不變判定為卡住
    
    def move_to(self, target_position):
        """移動角色到目標位置"""
        # 獲取當前位置
        current_position = self._get_current_position()
        if current_position is None:
            print("無法獲取當前位置")
            return False
        
        # 重置卡住計數器
        self.stuck_counter = 0
        self.last_position = current_position
        
        # 創建路徑規劃器
        planner = PathPlanner(self.quad_tree)
        
        # 尋找路徑
        path = planner.find_path(current_position, target_position)
        if not path:
            print("無法找到到目標的路徑")
            return False
        
        print(f"找到路徑，共{len(path)}個點")
        
        # 平滑路徑
        if hasattr(planner, 'smooth_path'):
            path = planner.smooth_path(path)
            print(f"平滑後路徑點數：{len(path)}")
        
        # 遍歷路徑點，執行移動
        for i in range(1, len(path)):
            if not self._move_to_next_point(path[i-1], path[i]):
                return False  # 如果移動失敗，提前返回
                
            # 檢查是否接近目標
            current_position = self._get_current_position()
            if current_position is None:
                print("無法獲取當前位置")
                return False
                
            # 檢查是否已到達最終目標附近
            distance_to_target = self._calculate_distance(current_position, target_position)
            if distance_to_target <= 50:  # 閾值可調整
                print(f"已到達目標位置附近，當前距離: {distance_to_target:.2f}")
                return True
        
        # 檢查最終位置是否接近目標位置
        final_position = self._get_current_position()
        if final_position is None:
            print("無法獲取最終位置")
            return False
            
        distance_to_target = self._calculate_distance(final_position, target_position)
        if distance_to_target <= 50:  # 閾值可調整
            print(f"成功到達目標位置，誤差: {distance_to_target:.2f}")
            return True
        else:
            print(f"未能精確到達目標位置，誤差: {distance_to_target:.2f}")
            return False
    
    def _move_to_next_point(self, current_point, next_point):
        """移動到路徑中的下一個點"""
        # 計算移動方向
        dx = next_point[0] - current_point[0]
        dy = next_point[1] - current_point[1]
        
        # 決定移動方向
        if abs(dx) > abs(dy):
            # 水平移動為主
            direction = "right" if dx > 0 else "left"
        else:
            # 垂直移動為主
            direction = "down" if dy > 0 else "up"
        
        # 執行移動
        self.move_direction(direction)
        
        # 檢查是否需要跳躍（當向上移動且高度變化較大時）
        if direction == "up" and abs(dy) > 50:
            self.jump()
        
        # 等待角色移動
        time.sleep(0.2 + random.random() * 0.1)
        
        # 獲取新位置並檢查是否卡住
        new_position = self._get_current_position()
        if new_position is None:
            print("無法獲取當前位置")
            return False
        
        # 計算移動距離
        move_distance = self._calculate_distance(self.last_position, new_position)
        
        # 檢查是否卡住（如果位置幾乎沒變）
        if move_distance < 10:  # 移動距離閾值
            self.stuck_counter += 1
            print(f"可能卡住了，計數：{self.stuck_counter}，距離：{move_distance:.2f}")
            
            if self.stuck_counter >= self.max_stuck_count:
                print("判定為卡住，嘗試解除")
                # 執行解卡操作
                self._try_unstuck()
                # 重置計數器
                self.stuck_counter = 0
                return False
        else:
            # 正常移動，重置計數器
            self.stuck_counter = 0
        
        # 更新上一次位置
        self.last_position = new_position
        
        return True
    
    def _try_unstuck(self):
        """嘗試解除卡住狀態"""
        print("執行解卡操作...")
        
        # 隨機移動
        directions = ["left", "right", "up", "down"]
        for _ in range(3):  # 嘗試3次不同方向
            direction = random.choice(directions)
            print(f"嘗試向{direction}移動以解卡")
            self.move_direction(direction)
            time.sleep(0.2)
        
        # 嘗試跳躍
        for _ in range(2):
            self.jump()
            time.sleep(0.3)
            
            # 跳躍同時移動
            direction = random.choice(["left", "right"])
            self.move_direction(direction)
            time.sleep(0.2)
    
    def move_direction(self, direction):
        """往特定方向移動一段時間"""
        if direction not in self.direction_keys:
            print(f"未知方向: {direction}")
            return
        
        key_code = self.direction_keys[direction]
        print(f"執行移動: {direction}")
        
        # 添加隨機性以避免被檢測
        press_time = self.key_press_time + random.random() * 0.05
        
        # 按下按鍵
        win32api.keybd_event(key_code, 0, 0, 0)
        
        # 等待一段時間
        time.sleep(press_time)
        
        # 釋放按鍵
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        # 在按鍵操作之間添加短暫的隨機延遲
        time.sleep(0.05 + random.random() * 0.05)
    
    def jump(self):
        """執行跳躍動作"""
        key_code = self.direction_keys["jump"]
        print("執行跳躍")
        
        # 按下跳躍鍵
        win32api.keybd_event(key_code, 0, 0, 0)
        
        # 等待一小段時間
        time.sleep(0.1 + random.random() * 0.05)
        
        # 釋放跳躍鍵
        win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)
        
        # 在動作之後添加短暫的隨機延遲
        time.sleep(0.1 + random.random() * 0.1)
    
    def _get_current_position(self):
        """獲取遊戲角色的當前位置"""
        try:
            # 使用物體檢測器獲取當前畫面
            screen = self.window_capture.capture()
            if screen is None:
                return None
            
            # 使用檢測器檢測小地圖上的玩家位置
            detections = self.detector.detect(screen)
            
            # 尋找"minimap_player"類別的檢測結果
            for detection in detections:
                if detection["class"] == "minimap_player":
                    # 獲取玩家在小地圖上的中心位置
                    x_center = detection["x_center"]
                    y_center = detection["y_center"]
                    
                    # 使用坐標轉換器將小地圖坐標轉換為遊戲世界坐標
                    world_pos = self.coordinate_transformer.screen_to_world((x_center, y_center))
                    return world_pos
            
            # 如果未檢測到玩家，嘗試預測位置
            if self.last_position is not None:
                print("未檢測到玩家，使用上次位置")
                return self.last_position
            
            return None
        except Exception as e:
            print(f"獲取位置時發生錯誤: {e}")
            return None
    
    def _calculate_distance(self, point1, point2):
        """計算兩點之間的距離"""
        return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)
    
    def apply_obstacle_avoidance(self, position, direction, max_force=10):
        """計算避障力"""
        # 查詢附近的障礙物
        x, y = position
        obstacles = self.quad_tree.query_region(x - 100, y - 100, x + 100, y + 100)
        
        # 初始化避障力
        force_x, force_y = 0, 0
        
        for obstacle in obstacles:
            if obstacle["type"] != "obstacle":
                continue
                
            # 計算到障礙物的向量
            dx = position[0] - obstacle["x"]
            dy = position[1] - obstacle["y"]
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 距離過遠的障礙物忽略
            if distance > 80:
                continue
                
            # 計算力的大小，距離越近力越大
            magnitude = max_force * (1.0 - min(1.0, distance/80))
            
            # 計算力的方向（遠離障礙物）
            if distance > 0:
                force_x += dx/distance * magnitude
                force_y += dy/distance * magnitude
        
        # 調整原始方向
        dx, dy = direction
        adjusted_dx = dx + force_x
        adjusted_dy = dy + force_y
        
        # 標準化方向向量
        length = math.sqrt(adjusted_dx**2 + adjusted_dy**2)
        if length > 0:
            adjusted_dx /= length
            adjusted_dy /= length
        
        return (adjusted_dx, adjusted_dy)
