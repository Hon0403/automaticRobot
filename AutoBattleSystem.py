import os
import threading
import time
import random
import math
import cv2
import numpy as np
from pynput.keyboard import Key, Controller as KeyboardController
import traceback


class AutoBattleSystem:
    def __init__(self, window_capture, detector, monster_detector=None, coordinate_transformer=None, controller=None):
        self.window_capture = window_capture
        self.detector = detector
        self.monster_detector = monster_detector
        self.coordinate_transformer = coordinate_transformer
        self.last_frame_hash = None
        self.cache_result = None
        self.cache_timeout = time.time()
        self.running = True
        self.controller = controller

        # 初始化鍵盤控制器
        self.keyboard = KeyboardController()

        # 添加小地圖分析器
        self.minimap_analyzer = MinimapAnalyzer()

        # 角色狀態
        self.player_position = None
        self.facing_right = True
        self.last_target = None

        # 小地圖相關變數
        self.last_minimap_region = None
        self.minimap_player_position = None
        self.minimap_monster_positions = []

    def start(self):
        """開始自動打怪"""
        print("自動打怪系統已啟動")
        try:
            # 創建新執行緒運行戰鬥循環
            self.battle_thread = threading.Thread(target=self._battle_loop)
            self.battle_thread.daemon = True  # 設為守護執行緒，主程式結束時自動終止
            self.battle_thread.start()
        except Exception as e:
            print(f"自動打怪循環出錯: {e}")

    def _battle_loop(self):
        while self.running:
            try:
                # 獲取當前角色朝向
                current_direction = self.controller.facing_direction
                
                # 根據朝向選擇不同的攻擊策略
                if current_direction == "right" or current_direction == "left":
                    # 水平方向攻擊邏輯
                    self._horizontal_attack(current_direction)
                else:
                    # 垂直方向攻擊邏輯
                    self._vertical_attack(current_direction)
                    
                time.sleep(0.2)
            except Exception as e:
                print(f"戰鬥循環錯誤: {e}")
                time.sleep(1)

    def _horizontal_attack(self, direction):
        """處理水平方向(左/右)的攻擊邏輯"""
        try:
            # 獲取畫面
            frame = self.window_capture.capture()
            if frame is None:
                return
                
            # 選擇目標怪物
            target = self._select_target()
            if not target:
                # 無目標，隨機移動
                self._random_move()
                return
                
            # 計算移動方向
            monster_pos = target["position"]
            screen_center = (frame.shape[1] / 2, frame.shape[0] / 2)
            
            # 調整角色朝向目標
            if monster_pos[0] > screen_center[0] and direction == "left":
                # 目標在右側但角色面向左側，需要轉向
                self.keyboard.press(Key.right)
                time.sleep(0.1)
                self.keyboard.release(Key.right)
            elif monster_pos[0] < screen_center[0] and direction == "right":
                # 目標在左側但角色面向右側，需要轉向
                self.keyboard.press(Key.left)
                time.sleep(0.1)
                self.keyboard.release(Key.left)
                
            # 判斷距離
            distance = self._calculate_distance(screen_center, monster_pos)
            if distance < 150:
                # 足夠近，進行攻擊
                self._attack()
            else:
                # 靠近目標
                self._move_towards_monster(target["detection"])
                
        except Exception as e:
            print(f"水平攻擊錯誤: {str(e)}")

    def _vertical_attack(self, direction):
        """處理垂直方向(上/下)的攻擊邏輯"""
        try:
            # 獲取畫面
            frame = self.window_capture.capture()
            if frame is None:
                return
                
            # 選擇目標
            target = self._select_target()
            if not target:
                # 無目標，隨機移動
                self._random_move()
                return
                
            # 計算垂直距離
            monster_pos = target["position"]
            screen_center = (frame.shape[1] / 2, frame.shape[0] / 2)
            vertical_distance = abs(monster_pos[1] - screen_center[1])
            
            if vertical_distance < 100:
                # 垂直距離較小，直接攻擊
                self._attack()
            else:
                # 移動到合適位置
                key = Key.up if direction == "up" else Key.down
                self.keyboard.press(key)
                time.sleep(0.2)
                self.keyboard.release(key)
                
        except Exception as e:
            print(f"垂直攻擊錯誤: {str(e)}")


    def _move_towards_monster(self, monster):
        # 計算怪物中心點
        x1, y1, x2, y2 = monster["bbox"]
        monster_x = (x1 + x2) / 2

        # 獲取畫面中心作為玩家位置參考
        frame = self.window_capture.capture()
        if frame is None:
            return

        player_x = frame.shape[1] / 2

        # 決定移動方向
        if monster_x > player_x + 50:  # 怪物在右邊
            self.keyboard.press(Key.right)
            time.sleep(0.3)
            self.keyboard.release(Key.right)
        elif monster_x < player_x - 50:  # 怪物在左邊
            self.keyboard.press(Key.left)
            time.sleep(0.3)
            self.keyboard.release(Key.left)
        else:  # 已經接近怪物
            self._attack()


    def _determine_minimap_region(self, frame):
        """從檢測結果中確定小地圖的位置和大小"""
        detections = self.detector.detect(frame)
        minimap_elements = [d for d in detections if d["class"] in ["minimap_player", "minimap_portal"]]
        
        if not minimap_elements:
            return (0, 0, 100, 100)  # 返回預設區域
        
        x_min = min(int(d["box"][0]) for d in minimap_elements)
        y_min = min(int(d["box"][1]) for d in minimap_elements)
        x_max = max(int(d["box"][2]) for d in minimap_elements)
        y_max = max(int(d["box"][3]) for d in minimap_elements)

        return (x_min, y_min, x_max - x_min, y_max - y_min)

    def analyze_minimap(self, minimap_image):
        current_time = time.time()
        frame_hash = hash(minimap_image.tobytes()[:1000])
        
        if frame_hash == self.last_frame_hash and current_time - self.cache_timeout < 0.5:
            return self.cache_result
        
        self.last_frame_hash = frame_hash
        self.cache_timeout = current_time

        hsv = cv2.cvtColor(minimap_image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(minimap_image, cv2.COLOR_BGR2GRAY)
        
        # 玩家位置檢測
        player_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        player_contours, _ = cv2.findContours(player_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if player_contours:
            largest_contour = max(player_contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            if M["m00"] > 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                self.player_position = (cx, cy)
                self._update_explored_area(cx, cy)
        
        # 怪物位置檢測
        monster_mask = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        monster_contours, _ = cv2.findContours(monster_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.minimap_monster_positions = []
        for contour in monster_contours:
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                self.minimap_monster_positions.append((cx, cy))
        
        # 平台邊緣檢測
        edges = cv2.Canny(gray, 50, 150)
        horizontal_kernel = np.ones((1, 7), np.uint8)
        horizontal_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horizontal_kernel)
        
        contours, _ = cv2.findContours(horizontal_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 50]
        
        self.platform_edges = []
        for contour in filtered_contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > h*3 and w > 20:
                self.platform_edges.append((x, y, x+w, y+h))
        
        self.cache_result = (self.player_position, self.platform_edges)
        return self.cache_result

    def _select_target(self):
        """選擇主畫面中檢測到的最近的怪物作為目標"""
        if not self.detector:
            return None
        
        # 獲取當前畫面
        frame = self.window_capture.capture()
        if frame is None:
            return None
        
        # 使用地形檢測器檢測怪物
        detections = self.detector.detect(frame, model_type='terrain')
        
        # 過濾出怪物檢測結果
        monster_detections = [d for d in detections if d.get("class_name", "") == "monster"]
        
        if not monster_detections:
            return None  # 如果沒有檢測到怪物,返回None
        
        # 找出最近的怪物
        if not self.player_position:
            # 如果不知道玩家位置,假設在畫面中央
            screen_center = (frame.shape[1] // 2, frame.shape[0] // 2)
            self.player_position = screen_center
            
        # 選擇距離玩家最近的怪物
        closest_monster = min(monster_detections, 
                             key=lambda d: self._calculate_distance(self.player_position, 
                                                                   self._get_center(d)))
        
        # 獲取怪物位置
        monster_pos = self._get_center(closest_monster)
        
        return {"type": "monster", "position": monster_pos, "detection": closest_monster}

    def _get_center(self, detection):
        """獲取檢測框的中心點"""
        if "bbox" in detection:
            x1, y1, x2, y2 = detection["bbox"]
        elif "box" in detection:
            x1, y1, x2, y2 = detection["box"]
        else:
            return (0, 0)
        return ((x1 + x2) / 2, (y1 + y2) / 2)
    
    def _calculate_distance(self, pos1, pos2):
        """計算兩點之間的距離"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

    def _move_towards_target(self, target_pos):
        """控制角色向目標位置移動，並處理平台間隙問題"""

        # 1. 計算移動方向
        dx = target_pos[0] - self.player_position[0]
        direction = "right" if dx > 0 else "left"
        direction_key = Key.right if direction == "right" else Key.left

        # 2. 檢測前方是否有平台間隙
        gap_detected = self.collision_system.detect_platform_gap(
            start_pos=self.player_position,
            direction=direction,
            max_distance=100  # 檢測前方100像素
        )

        # 3. 根據檢測結果決定行動
        if gap_detected["gap"]:
            gap_distance = gap_detected["distance"]
            gap_width = gap_detected["width"]  # 假設檢測函數會返回間隙寬度

            # 3.1 如果間隙太近且可跳過
            if gap_distance < 50 and gap_width < self.player_jump_distance:
                print(f"發現間隙，距離:{gap_distance}，寬度:{gap_width}，嘗試跳躍")
                # 執行跳躍動作
                self.keyboard.press(Key.alt)  # 假設Alt鍵是跳躍
                time.sleep(0.1)
                self.keyboard.press(direction_key)
                time.sleep(0.3)  # 跳躍時間
                self.keyboard.release(Key.alt)
                self.keyboard.release(direction_key)
                return True, target_pos

            # 3.2 無法跳過的間隙
            else:
                print(f"發現無法跨越的間隙，尋找其他路徑")
                # 這裡可以調用路徑規劃模組尋找替代路徑
                return False, target_pos

        # 4. 沒有間隙，正常移動
        else:
            # 檢查是否有障礙物
            obstacle = self.collision_system.predict_obstacle_collision(
                self.player_position,
                direction,
                distance=30
            )

            if obstacle["collision"]:
                # 有障礙物，嘗試跳躍
                self.keyboard.press(Key.alt)
                time.sleep(0.1)
                self.keyboard.press(direction_key)
                time.sleep(0.2)
                self.keyboard.release(Key.alt)
                time.sleep(0.1)
                self.keyboard.release(direction_key)
            else:
                # 無障礙物，正常移動
                self.keyboard.press(direction_key)
                time.sleep(0.2)  # 移動時間
                self.keyboard.release(direction_key)

        return True, target_pos


    def _is_near_ladder(self, ladders):
        """檢查玩家是否靠近梯子/繩索"""
        if not self.player_position or not ladders:
            return False
            
        px, py = self.player_position
        
        for ladder in ladders:
            if "bbox" in ladder:
                x1, y1, x2, y2 = ladder["bbox"]
            elif "box" in ladder:
                x1, y1, x2, y2 = ladder["box"]
            else:
                continue
                
            # 計算梯子中心
            lx = (x1 + x2) / 2
            ly = (y1 + y2) / 2
            
            # 檢查玩家是否靠近梯子
            if abs(px - lx) < 50 and abs(py - ly) < 100:
                return True
                
        return False


    def _check_obstacles_ahead(self, direction, distance=100):
        """檢測前方是否有障礙物"""
        start_x, start_y = self.player_position
        end_x = start_x + distance if direction == "right" else start_x - distance
        
        # 使用射線檢測或像素分析來檢測障礙物
        # 這裡可以添加具體的檢測邏輯

        return False  # 假設沒有障礙物

    def _attack(self):
        """執行攻擊"""
        try:
            print("執行攻擊")
            # 使用字元代碼而非Key枚舉
            self.keyboard.press('z')
            time.sleep(0.1)
            self.keyboard.release('z')
        except Exception as e:
            print(f"攻擊時發生錯誤: {str(e)}")

    def _random_move(self):
        """隨機移動"""
        direction_key = random.choice([Key.left, Key.right])
        print(f"隨機移動方向: {direction_key}")

    def stop(self):
        """停止自動打怪"""
        self.running = False
        print("自動打怪系統已停止")
        # 釋放所有按鍵
        self.keyboard.release(Key.ctrl)
        self.keyboard.release(Key.alt)
        self.keyboard.release(Key.left)
        self.keyboard.release(Key.right)
        self.keyboard.release(Key.up)
        self.keyboard.release(Key.down)

    def _update_player_position(self, frame):
        # 使用小地圖玩家位置估算遊戲世界中的位置
        if self.minimap_player_position:
            # 將小地圖座標轉換為遊戲世界座標
            self.player_position = (
                frame.shape[1] / 2,  # 使用畫面中心X座標
                frame.shape[0] / 2   # 使用畫面中心Y座標
            )
            print(f"使用小地圖推斷玩家位置: {self.player_position}")
            return
        
        # 默認位置
        self.player_position = (400, 300)
        print("無法檢測到玩家,使用預設位置: {self.player_position}")

    
    def _check_platform_edge(self, direction):
        """檢查是否接近平台邊緣"""
        if hasattr(self, 'auto_battle') and self.auto_battle:
            minimap_analyzer = MinimapAnalyzer()
            minimap_analyzer.start_analysis_thread()
            self.auto_battle.minimap_analyzer = minimap_analyzer
        
        if not self.minimap_player_position:
            print("無玩家位置數據")
            return False
        
        player_x, player_y = self.minimap_player_position
        print(f"檢查平台邊緣 - 玩家位置: ({player_x}, {player_y}), 方向: {direction}")
        
        for edge in self.platform_edges:
            if direction == "right" and edge[0] <= player_x + 10 <= edge[2] and abs(edge[1] - player_y) < 10:
                print(f"檢測到右側平台邊緣: {edge}")
                return True
            elif direction == "left" and edge[0] <= player_x - 10 <= edge[2] and abs(edge[3] - player_y) < 10:
                print(f"檢測到左側平台邊緣: {edge}")
                return True
        
        return False


class MinimapAnalyzer:
    def __init__(self):
        self.minimap_region = None
        self.player_position = None
        self.platform_edges = []
        self.explored_areas = {}
        self.world_map = {}
        self.scale_factor = 1.5
        self.last_frame_hash = None
        self.cache_result = None
        self.cache_timeout = time.time()
        self.minimap_monster_positions = []
        self.latest_minimap_image = None
        self.analysis_thread = None

    def extract_minimap(self, frame):
        height, width = frame.shape[:2]
        roi_height = min(200, height // 3)
        roi_width = min(200, width // 3)
        roi = frame[0:roi_height, 0:roi_width]
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower_bound = np.array([0, 0, 200])
        upper_bound = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            self.minimap_region = (x, y, w, h)
            return roi[y:y+h, x:x+w]
        
        if self.minimap_region:
            x, y, w, h = self.minimap_region
            return roi[y:y+h, x:x+w]
        
        return roi[10:150, 10:150]

    def analyze_minimap(self, minimap_image):
        current_time = time.time()
        frame_hash = hash(minimap_image.tobytes()[:1000])
        
        if frame_hash == self.last_frame_hash and current_time - self.cache_timeout < 0.5:
            return self.cache_result
        
        self.last_frame_hash = frame_hash
        self.cache_timeout = current_time

        hsv = cv2.cvtColor(minimap_image, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(minimap_image, cv2.COLOR_BGR2GRAY)
        
        # 玩家位置檢測
        player_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 30, 255]))
        player_contours, _ = cv2.findContours(player_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if player_contours:
            largest_contour = max(player_contours, key=cv2.contourArea)
            M = cv2.moments(largest_contour)
            if M["m00"] > 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                self.player_position = (cx, cy)
                self._update_explored_area(cx, cy)
        
        # 怪物位置檢測
        monster_mask = cv2.inRange(hsv, np.array([0, 100, 100]), np.array([10, 255, 255]))
        monster_contours, _ = cv2.findContours(monster_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.minimap_monster_positions = []
        for contour in monster_contours:
            M = cv2.moments(contour)
            if M["m00"] > 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                self.minimap_monster_positions.append((cx, cy))
        
        # 平台邊緣檢測
        edges = cv2.Canny(gray, 50, 150)
        horizontal_kernel = np.ones((1, 7), np.uint8)
        horizontal_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horizontal_kernel)
        
        contours, _ = cv2.findContours(horizontal_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 50]
        
        self.platform_edges = []
        for contour in filtered_contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > h*3 and w > 20:
                self.platform_edges.append((x, y, x+w, y+h))
        
        self.cache_result = (self.player_position, self.platform_edges)
        return self.cache_result

    def _update_explored_area(self, x, y):
        grid_x, grid_y = x // 10, y // 10
        key = f"{grid_x},{grid_y}"
        self.explored_areas[key] = {"position": (x, y), "time": time.time()}

    def minimap_to_world(self, minimap_pos):
        if not self.player_position or not minimap_pos:
            return None
        screen_center_x, screen_center_y = 400, 300
    
        if isinstance(minimap_pos, tuple) and len(minimap_pos) == 2:
            # 正確處理元組中的x和y坐標
            world_x = screen_center_x + (minimap_pos[0] - self.player_position[0]) * self.scale_factor
            world_y = screen_center_y + (minimap_pos[1] - self.player_position[1]) * self.scale_factor
            return (int(world_x), int(world_y))
        return None

    def world_to_minimap(self, world_pos, screen_center=(400, 300)):
        if not self.player_position:
            return None
    
        if isinstance(world_pos, tuple) and len(world_pos) == 2:
            # 正確處理元組中的x和y坐標
            dx = world_pos[0] - screen_center[0]
            dy = world_pos[1] - screen_center[1]
        
            minimap_dx = dx / self.scale_factor
            minimap_dy = dy / self.scale_factor
        
            minimap_x = self.player_position[0] + minimap_dx
            minimap_y = self.player_position[1] + minimap_dy
        
            return (int(minimap_x), int(minimap_y))
        return None
    
    def locate_minimap(self, frame):
        """自適應定位小地圖區域"""
        try:
            print("進入locate_minimap方法")
            # 1. 轉換顏色空間以便於處理
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 2. 尋找小地圖常見的顏色範圍（需根據遊戲調整）
            lower_bound = np.array([0, 0, 200])  # 高亮度低飽和度（常見小地圖背景）
            upper_bound = np.array([180, 30, 255])
            mask = cv2.inRange(hsv, lower_bound, upper_bound)

            # 保存中間結果以便檢查
            cv2.imwrite("debug_hsv.png", hsv)
            cv2.imwrite("debug_mask.png", mask)

            # 3. 尋找輪廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            print(f"找到 {len(contours)} 個輪廓")
            
            # 4. 篩選可能的小地圖區域（通常是較大的矩形區域）
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                self.minimap_region = (x, y, w, h)
                return (x, y, w, h)

            # 5. 如果無法找到，則使用預設區域
            if self.minimap_region:
                return self.minimap_region
            return (0, 0, 200, 200)
        except Exception as e:
            print(f"定位小地圖時發生錯誤: {str(e)}")
            return (0, 0, 200, 200)

    def locate_minimap_by_template(self, screen):
        """使用多尺度模板匹配定位小地圖"""
        try:
            # 轉換為灰度圖
            gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
            
            # 載入上下邊框模板
            top_template = cv2.imread('templates/top.png', 0)
            bottom_template = cv2.imread('templates/down.png', 0)
            
            if top_template is None or bottom_template is None:
                print("無法載入模板圖像")
                return (0, 0, 200, 200)
                
            # 匹配上邊框
            top_result = cv2.matchTemplate(gray_screen, top_template, cv2.TM_CCOEFF_NORMED)
            _, top_max_val, _, top_max_loc = cv2.minMaxLoc(top_result)
            
            # 匹配下邊框
            bottom_result = cv2.matchTemplate(gray_screen, bottom_template, cv2.TM_CCOEFF_NORMED)
            _, bottom_max_val, _, bottom_max_loc = cv2.minMaxLoc(bottom_result)
            
            # 檢查匹配質量
            if top_max_val < 0.5 or bottom_max_val < 0.5:
                print(f"匹配質量不佳: 上={top_max_val:.2f}, 下={bottom_max_val:.2f}")
                return (0, 0, 200, 200)
                
            # 計算小地圖區域
            x = top_max_loc[0]
            y = top_max_loc[1]
            width = top_template.shape[1]
            height = bottom_max_loc[1] + bottom_template.shape[0] - top_max_loc[1]
            
            # 確保高度和寬度至少為1像素
            width = max(1, width)
            height = max(1, height)
            
            return (x, y, width, height)
        except Exception as e:
            print(f"模板匹配小地圖時出錯: {str(e)}")
            return (0, 0, 200, 200)
