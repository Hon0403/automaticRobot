import time
import random
import threading
from pynput.keyboard import Key, Controller

class ActionController:
    def __init__(self, window_capture=None, detector=None, 
                coordinate_transformer=None, quad_tree=None):
        """初始化動作控制器"""
        self.window_capture = window_capture
        self.detector = detector
        self.coordinate_transformer = coordinate_transformer
        self.quad_tree = quad_tree
        self.keyboard = Controller()
        
    def press_key(self, key, duration=0.1):
        """按下按鍵並釋放"""
        self.keyboard.press(key)
        time.sleep(duration)
        self.keyboard.release(key)
        
    def move_direction(self, direction, duration=0.5):
        """向指定方向移動"""
        key_map = {
            "left": Key.left,
            "right": Key.right,
            "up": Key.up,
            "down": Key.down
        }
        if direction in key_map:
            self.keyboard.press(key_map[direction])
            time.sleep(duration)
            self.keyboard.release(key_map[direction])

class AutoBattleSystem:
    def __init__(self, detector, window_capture, coordinate_transformer, map_memory, collision_system):
        """
        初始化自動打怪系統
        
        參數：
            detector: YOLO檢測器
            window_capture: 視窗捕獲器
            coordinate_transformer: 座標轉換器
            map_memory: 地圖記憶系統
            collision_system: 碰撞系統
        """
        self.detector = detector
        self.window_capture = window_capture
        self.coordinate_transformer = coordinate_transformer
        self.map_memory = map_memory
        self.collision_system = collision_system
        self.keyboard = Controller()
        
        # 狀態控制
        self.running = False
        self.thread = None
        self.player_position = None
        self.last_move_time = 0
        self.move_cooldown = 2.0
        self.last_attack_time = 0
        self.attack_cooldown = 0.5
        self.is_climbing = False
        self.using_portal = False
        
        # 自動打怪參數
        self.movement_range = 100  # 移動範圍（像素）
        self.attack_range = 200    # 攻擊範圍
        self.attack_key = 'z'      # 攻擊按鍵
        self.interact_key = 'e'    # 互動按鍵
        
        # 防卡死計時器
        self.last_position_change = time.time()
        self.stuck_threshold = 10.0  # 10秒未移動視為卡住
        
        # 目標選擇參數
        self.current_target = None
        self.target_refresh_cooldown = 5.0
        self.last_target_refresh = 0
    
    def start(self):
        """開始自動打怪"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._battle_loop)
        self.thread.daemon = True
        self.thread.start()
        print("自動打怪系統已啟動")
    
    def stop(self):
        """停止自動打怪"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("自動打怪系統已停止")
    
    def _battle_loop(self):
        """打怪主循環"""
        while self.running:
            try:
                # 獲取當前畫面
                frame = self.window_capture.capture()
                if frame is None:
                    time.sleep(0.2)
                    continue
                
                # 進行物體檢測
                detections = self.detector.detect(frame)
                
                # 更新碰撞系統
                self.collision_system.update_from_detections(detections, self.coordinate_transformer)
                
                # 獲取玩家位置
                if self.collision_system.player_box:
                    new_position = self.collision_system.player_box.get_center()
                    
                    # 檢查是否移動
                    if self.player_position:
                        if self._distance(self.player_position, new_position) > 10:
                            self.last_position_change = time.time()
                    
                    self.player_position = new_position
                
                # 檢查是否卡住
                if (time.time() - self.last_position_change > self.stuck_threshold 
                    and not self.is_climbing and not self.using_portal):
                    self._unstuck()
                    self.last_position_change = time.time()
                
                # 處理碰撞事件
                collisions = self.collision_system.check_player_collisions()
                for collision in collisions:
                    if collision["type"] == "portal" and not self.using_portal:
                        # 自動使用傳送點
                        self._use_portal()
                    elif collision["type"] == "rope" and not self.is_climbing:
                        # 自動攀爬繩索
                        self._climb_rope()
                
                # 執行自動打怪行為
                self._perform_battle_actions()
                
                # 控制循環頻率
                time.sleep(0.1)
            
            except Exception as e:
                print(f"自動打怪循環出錯: {e}")
                time.sleep(1.0)
    
    def _perform_battle_actions(self):
        """執行打怪行為"""
        current_time = time.time()
        
        # 更新目標
        if current_time - self.last_target_refresh > self.target_refresh_cooldown:
            self.current_target = self._select_target()
            self.last_target_refresh = current_time
        
        # 定期執行攻擊
        if current_time - self.last_attack_time > self.attack_cooldown:
            self._attack()
            self.last_attack_time = current_time
        
        # 定期移動（尋找怪物）
        if current_time - self.last_move_time > self.move_cooldown:
            self._move_intelligently()
            self.last_move_time = current_time
    
    def _select_target(self):
        """選擇移動目標"""
        possible_targets = []
        
        # 獲取附近物體（調整參數為像素距離）
        try:
            nearby_objects = self.map_memory.get_nearby_objects(
                self.player_position, 
                radius=int(500 / self.map_memory.cell_size)  # 500像素範圍
            )
            
            # 過濾出未探索的目標
            for obj in nearby_objects:
                if not self.map_memory.is_position_explored(obj["position"]):
                    if "priority" not in obj:
                        if obj["type"] == "portal":
                            obj["priority"] = 90
                        elif obj["type"] == "rope":
                            obj["priority"] = 80
                        else:
                            obj["priority"] = 60
                    possible_targets.append(obj)
        except Exception as e:
            print(f"目標選擇出錯: {e}")
        
        # 如果沒有其他目標，添加隨機探索點
        if not possible_targets:
            random_point = self._get_random_exploration_point()
            possible_targets.append({"type": "random", "position": random_point, "priority": 50})
        
        # 計算權重並排序
        for target in possible_targets:
            target["weight"] = self._calculate_weight(target)
        
        possible_targets.sort(key=lambda x: (-x["priority"], x["weight"]))
        
        return possible_targets[0] if possible_targets else None
    
    def _calculate_weight(self, target):
        """計算目標權重（數值越小越優先）"""
        weight = 0
        
        # 距離因素 - 近的目標優先
        distance = self._distance(self.player_position, target["position"])
        weight += distance * 0.5  # 距離權重係數
        
        # 探索價值
        try:
            if not self.map_memory.is_position_explored(target["position"]):
                weight -= 100  # 未探索區域獎勵
        except:
            pass
        
        return weight
    
    def _move_intelligently(self):
        """智能移動到選定目標"""
        # 如果正在攀爬或使用傳送點，則不移動
        if self.is_climbing or self.using_portal:
            return
            
        # 如果沒有目標，執行隨機移動
        if not self.current_target:
            self._random_move()
            return
        
        # 提取目標信息
        target_pos = self.current_target["position"]
        target_type = self.current_target["type"]
        
        # 計算與目標的相對位置
        dx = target_pos[0] - self.player_position[0]
        dy = target_pos[1] - self.player_position[1]
        
        # 根據目標類型選擇移動策略
        if target_type == "portal":
            self._approach_portal(target_pos)
        elif target_type == "rope":
            self._approach_rope(target_pos)
        else:
            # 一般移動
            direction = Key.right if dx > 0 else Key.left
            move_duration = min(abs(dx) / 200, 1.0)  # 根據距離調整移動時間
            
            # 執行移動
            self.keyboard.press(direction)
            time.sleep(move_duration)
            self.keyboard.release(direction)
            
            # 如果目標在高處，可能需要跳躍
            if dy < -50:  # 目標在上方
                self._jump()
    
    def _approach_portal(self, portal_pos):
        """接近傳送點"""
        dx = portal_pos[0] - self.player_position[0]
        direction = Key.right if dx > 0 else Key.left
        
        # 移動接近傳送點
        self.keyboard.press(direction)
        time.sleep(min(abs(dx) / 100, 0.5))
        self.keyboard.release(direction)
        
        # 如果足夠接近，則使用互動鍵
        if abs(dx) < 20:
            self.keyboard.press(self.interact_key)
            time.sleep(0.1)
            self.keyboard.release(self.interact_key)
    
    def _approach_rope(self, rope_pos):
        """改進版繩索接近方法"""
        # 計算水平距離和垂直高度差
        dx = rope_pos[0] - self.player_position[0]
        dy = rope_pos[1] - self.player_position[1]
        
        # 水平移動對齊繩索
        if abs(dx) > 20:  # 需要水平移動
            direction = Key.right if dx > 0 else Key.left
            self.keyboard.press(direction)
            move_time = min(abs(dx)/150, 1.0)  # 根據距離調整移動時間
            time.sleep(move_time)
            self.keyboard.release(direction)
        
        # 垂直對齊處理
        if dy < -30:  # 繩索在角色上方
            self._jump_to_reach()  # 加入跳躍機制
        elif dy > 50:  # 繩索在角色下方（可能需要向下移動）
            self._descend_to_reach()
        
        # 最終攀爬觸發
        if abs(dx) <= 20 and abs(dy) <= 50:
            self._climb_rope()
    
    def _jump_to_reach(self):
        """跳躍觸發機制"""
        # 短按跳躍鍵嘗試接觸繩索
        self.keyboard.press(Key.alt)  # 楓之谷通常使用Alt鍵跳躍
        time.sleep(0.1)
        self.keyboard.release(Key.alt)
        time.sleep(0.2)  # 等待跳躍動畫
    
    def _descend_to_reach(self):
        """下降到繩索位置"""
        # 按下向下鍵尋找繩索
        self.keyboard.press(Key.down)
        time.sleep(0.5)
        self.keyboard.release(Key.down)
    
    def _random_move(self):
        """隨機移動以尋找怪物"""
        # 隨機選擇方向
        direction = random.choice([Key.left, Key.right])
        
        # 按下按鍵
        self.keyboard.press(direction)
        time.sleep(0.3 + random.random() * 0.4)  # 隨機移動時間
        self.keyboard.release(direction)
    
    def _attack(self):
        """執行攻擊動作"""
        # 按下攻擊鍵
        self.keyboard.press(self.attack_key)
        time.sleep(0.05)
        self.keyboard.release(self.attack_key)
    
    def _jump(self):
        """執行跳躍動作"""
        self.keyboard.press(Key.alt)  # 使用Alt鍵跳躍
        time.sleep(0.1)
        self.keyboard.release(Key.alt)
    
    def _unstuck(self):
        """嘗試解除卡住狀態"""
        print("檢測到卡住，嘗試解除...")
        
        # 跳躍
        self._jump()
        
        # 隨機移動
        direction = random.choice([Key.left, Key.right, Key.up, Key.down])
        self.keyboard.press(direction)
        time.sleep(1.0)  # 長時間移動
        self.keyboard.release(direction)
        
        # 重設卡住計時器
        self.last_position_change = time.time()
    
    def _use_portal(self):
        """使用傳送點"""
        self.using_portal = True
        
        # 按下互動鍵
        self.keyboard.press(self.interact_key)
        time.sleep(0.1)
        self.keyboard.release(self.interact_key)
        
        # 等待傳送完成
        time.sleep(2.0)
        self.using_portal = False
        
        # 重設卡住計時器
        self.last_position_change = time.time()
    
    def _climb_rope(self):
        """改進版攀爬邏輯"""
        self.is_climbing = True
        try:
            # 持續攀爬檢測（最多3秒）
            start_time = time.time()
            while time.time() - start_time < 3 and self.is_climbing:
                self.keyboard.press(Key.up)
                time.sleep(0.3)  # 分段攀爬
                self.keyboard.release(Key.up)
                time.sleep(0.1)
                
                # 實時更新位置檢測
                current_pos = self._get_updated_position()
                if current_pos[1] < self.player_position[1] - 100:
                    break  # 已爬升足夠高度
        finally:
            self.is_climbing = False
            self.keyboard.release(Key.up)  # 確保釋放按鍵
            self.last_position_change = time.time()
    
    def _get_updated_position(self):
        """獲取角色的最新位置"""
        if self.collision_system and self.collision_system.player_box:
            return self.collision_system.player_box.get_center()
        return self.player_position
    
    def _distance(self, pos1, pos2):
        """計算兩點之間的距離"""
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
    
    def _get_edge_exploration_points(self):
        """獲取地圖邊緣探索點"""
        # 這裡需要實現獲取地圖邊緣探索點的邏輯
        # 可以根據已探索區域的邊界來確定
        return []
    
    def _get_random_exploration_point(self):
        """在已知區域附近隨機選擇一個點"""
        # 在當前位置附近隨機選擇一個點
        x = self.player_position[0] + random.randint(-500, 500)
        y = self.player_position[1] + random.randint(-300, 300)
        return (x, y)
