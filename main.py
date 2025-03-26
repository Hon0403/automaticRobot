import math
import os
import tkinter as tk
import threading
import time
import sys
import cv2
from pynput import keyboard
import numpy as np
import win32gui
from PIL import Image, ImageTk
from tkinter import messagebox
from visualization import draw_fan_shape

# 自動戰鬥
from MapleUI import MapleUI

# 自動尋路系統
from window_capture import WindowCapture
from detection import YOLODetector
from coordinate_system import CoordinateTransformer
from quadtree import QuadTree, Rectangle, Point
from MapMemory import MapMemory
from CollisionSystem import CollisionSystem
from AutoBattleSystem import AutoBattleSystem, MinimapAnalyzer
from MonsterDetection import TemplateMonsterDetector
from path_planner import PathPlanner

class MapleController:
    def __init__(self, root):
        """初始化主控制器"""
        # 系統組件
        self.window_capture = None
        self.detector = None
        self.coordinate_transformer = None
        self.quad_tree = None
        self.map_memory = MapMemory()
        self.collision_system = CollisionSystem(self.map_memory)
        self.auto_battle = None
        self.monster_detector = None
        self.facing_direction = "right" 

        # 直接指定模型路徑
        self.minimap_model_path = "MODELS/SmallObjects.pt"
        self.terrain_model_path = "MODELS/QuadRecognizer.pt"
        
        # 新增：設置按鍵監聽
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.keyboard_listener.start()

        # 控制變量
        self.running = False
        self.detection_thread = None
        self.monster_detection_enabled = False
        
        # 初始化UI
        self.ui = MapleUI(root, self)
        
        # 儲存視窗句柄和標題的字典
        self.window_info = {}
        
        # 首次更新可用視窗列表
        self.refresh_window_list()
        
        self.path_planner = PathPlanner()
    
    def refresh_window_list(self):
        """更新可用視窗列表"""
        try:
            windows = WindowCapture.list_window_names()
            window_titles = []
            self.window_info.clear()
            
            for hwnd, title in windows:
                if title.strip():
                    window_titles.append(title)
                    self.window_info[title] = hwnd
            
            # 更新UI
            self.ui.update_window_list(window_titles)
        except Exception as e:
            self.ui.log(f"更新可用視窗列表時發生錯誤: {e}")
    
    def get_windows(self):
        """獲取所有可見的視窗"""
        windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows
    
    def start_detection(self):
        """開始檢測過程"""
        try:
            # 從UI獲取選擇的目標視窗
            selected_window = self.ui.get_selected_window()
            if not selected_window:
                messagebox.showerror("錯誤", "請選擇一個目標視窗")
                return
            
            # 初始化路徑規劃器的網格和連接點
            self.path_planner.initialize_grid(self.map_memory)
            self.path_planner.identify_connection_points(self.map_memory)
            
            # 從儲存的句柄中獲取視窗句柄
            hwnd = self.window_info.get(selected_window)
            if not hwnd:
                messagebox.showerror("錯誤", "無法獲取選擇的視窗")
                return
            
            # 初始化視窗捕獲器
            self.window_capture = WindowCapture(hwnd=hwnd)
            self.ui.log(f"選擇的視窗: {selected_window}")
            
            # 檢查模型文件是否存在
            if not os.path.exists(self.terrain_model_path):
                self.ui.log(f"警告: 找不到地形模型文件 {self.terrain_model_path}")
            
            # 初始化座標轉換器
            minimap_rect = (10, 10, 150, 150)  # 小地圖的預設位置和大小，可能需要調整
            self.coordinate_transformer = CoordinateTransformer(minimap_rect)
            
            # 初始化小地圖分析器
            if hasattr(self, 'auto_battle') and self.auto_battle:
                self.auto_battle.minimap_analyzer = MinimapAnalyzer()
            
            # 初始化四叉樹
            screen_size = self.window_capture.get_window_rect()
            if screen_size:
                width, height = screen_size[2], screen_size[3]
                boundary = Rectangle(0, 0, width, height)
                self.quad_tree = QuadTree(boundary, 4)  # 創建四叉樹，參數根據需要調整
            
            # 初始化檢測器 - 自動載入指定模型
            self.detector = YOLODetector(
                minimap_model_path=self.minimap_model_path,
                terrain_model_path=self.terrain_model_path,
                confidence_threshold=0.5
            )
            
            # 更新檢測按鈕狀態
            self.ui.update_detection_buttons(True)
            
            # 設置運行標誌
            self.running = True
            
            # 初始化小地圖分析器
            self.ui.log("初始化小地圖分析器")
            minimap_analyzer = MinimapAnalyzer()
            if hasattr(self, 'auto_battle') and self.auto_battle:
                self.auto_battle.minimap_analyzer = minimap_analyzer
            else:
                self.auto_battle = AutoBattleSystem(
                    window_capture=self.window_capture,
                    detector=self.detector,
                    monster_detector=self.monster_detector,
                    coordinate_transformer=self.coordinate_transformer
                )
                self.auto_battle.minimap_analyzer = minimap_analyzer
            
            # 啟動檢測線程
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            self.ui.log("開始檢測過程")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.ui.log(f"啟動檢測過程時發生錯誤: {str(e)}")
    
    def stop_detection(self):
        """停止檢測過程"""
        self.running = False
        
        # 停止自動戰鬥系統
        if self.auto_battle:
            self.stop_auto_battle()
        
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        
        self.ui.update_detection_buttons(False)
        self.ui.log("停止檢測過程")
    
    def detection_loop(self):
        """檢測主循環"""
        try:
            while self.running:
                # 捕獲視窗畫面
                screen = self.window_capture.capture()
                if screen is None:
                    self.ui.log("無法捕獲視窗畫面，將在0.5秒後重試")
                    time.sleep(0.5)
                    continue

                # 保存原始畫面以便展示
                visualization_img = screen.copy()

                # 執行檢測
                all_detections = self.detector.detect(screen)

                # 更新物體追蹤系統
                self.update_object_tracking(all_detections)

                # 檢測並繪製小地圖區域 - 使用模板匹配方法
                if hasattr(self, 'auto_battle') and self.auto_battle and hasattr(self.auto_battle, 'minimap_analyzer'):
                    # 使用模板匹配方法而非顏色檢測
                    minimap_rect = self.auto_battle.minimap_analyzer.locate_minimap_by_template(screen)
                    if minimap_rect != (0, 0, 200, 200):  # 檢查是否成功找到小地圖
                        x, y, w, h = minimap_rect
                        cv2.rectangle(visualization_img, (x, y), (x+w, y+h), (0, 255, 0), 2)

                        # 裁剪小地圖區域
                        minimap_region = screen[y:y+h, x:x+w]

                        # 對小地圖區域使用小物體模型進行檢測
                        minimap_detections = self.detector.detect(minimap_region, model_type='minimap')

                        # 調整檢測結果的座標（相對於整個畫面）
                        for detection in minimap_detections:
                            bbox = detection.get("bbox", [])
                            if len(bbox) == 4:
                                x1, y1, x2, y2 = bbox
                                detection["bbox"] = [x1+x, y1+y, x2+x, y2+y]
                                # 標記為小地圖元素
                                detection["is_minimap"] = True

                        # 將小地圖元素檢測結果添加到所有檢測結果中
                        all_detections.extend(minimap_detections)

                # 一次性繪製所有檢測結果
                self.draw_detections(visualization_img, all_detections)

                # 尋找主遊戲畫面中的角色位置（而非小地圖角色）
                main_player_pos = None
                minimap_player_pos = None

                print("開始檢測角色位置...")

                # 獲取主畫面角色和小地圖角色
                for detection in all_detections:
                    # 尋找主畫面中的玩家
                    if detection.get("class_name") == "Player" and not detection.get("is_minimap", False):
                        bbox = detection.get("bbox", detection.get("box", []))
                        if len(bbox) == 4:
                            x1, y1, x2, y2 = bbox
                            main_player_pos = ((x1 + x2) / 2, (y1 + y2) / 2)
                            self.ui.log(f"找到主畫面角色，位置：{main_player_pos}")

                    # 記錄小地圖玩家位置（不再用於射線檢測）
                    elif detection.get("class_name") == "minimap_player" or (detection.get("class_name") == "Player" and detection.get("is_minimap", False)):
                        bbox = detection.get("bbox", detection.get("box", []))
                        if len(bbox) == 4:
                            x1, y1, x2, y2 = bbox
                            minimap_player_pos = ((x1 + x2) / 2, (y1 + y2) / 2)
                            print(f"找到小地圖角色! 位置: {minimap_player_pos}")

                # 提取地形物件（用於碰撞檢測）
                terrain_objects = []
                for detection in all_detections:
                    if detection.get("class_name") in ["Ground", "ground", "platform"] and not detection.get("is_minimap", False):
                        terrain_objects.append(detection)

                # 僅使用主畫面角色進行射線檢測
                if main_player_pos:  # 只在找到主畫面角色時執行
                    print(f"使用主畫面角色位置進行射線檢測: {main_player_pos}")
                    # 根據當前朝向設定扇形角度
                    fan_radius = 100  # 扇形半徑

                    # 根據角色朝向決定扇形方向
                    if self.facing_direction == "right":
                        start_angle, end_angle = -30, 30
                    elif self.facing_direction == "left":
                        start_angle, end_angle = 150, 210
                    elif self.facing_direction == "up":
                        start_angle, end_angle = 60, 120
                    elif self.facing_direction == "down":
                        start_angle, end_angle = -120, -60

                    # 使用主畫面角色位置繪製扇形
                    visualization_img = draw_fan_shape(
                        visualization_img,
                        (int(main_player_pos[0]), int(main_player_pos[1])),
                        fan_radius,
                        start_angle,
                        end_angle,
                        (0, 255, 255),  # 黃色
                        0.3  # 透明度
                    )

                    # 執行並視覺化射線檢測（使用地形物件）
                    gap_info = self.collision_system.detect_platform_gaps(
                        start_pos=main_player_pos,
                        direction=self.facing_direction,
                        max_distance=150,
                        visualization_img=visualization_img,
                        terrain_objects=terrain_objects
                    )

                    # 添加檢測狀態與角色來源資訊
                    status = "檢測到平台間隙!" if gap_info.get("gap", False) else "未檢測到平台間隙"
                    cv2.putText(visualization_img,
                                status,
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                elif minimap_player_pos:
                    print("警告: 未找到主畫面角色，射線檢測未執行")
                    # 顯示提示信息，找不到主畫面角色
                    cv2.putText(visualization_img,
                                "未找到主畫面角色，請檢查檢測模型",
                                (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # 顯示標記後的圖像
                self.ui.show_image(visualization_img)

                # 控制循環速度
                time.sleep(0.1)

        except Exception as e:
            self.ui.log(f"檢測循環發生錯誤: {str(e)}")

    
    def _continue_detection_loop(self):
        """繼續檢測循環"""
        if self.running:
            self.detection_loop()
    
    def update_object_tracking(self, detections):
        try:
            # 檢查四叉樹是否已初始化
            if self.quad_tree is None:
                # 初始化四叉樹
                screen_size = self.window_capture.get_window_rect()
                if screen_size:
                    width, height = screen_size[2], screen_size[3]
                    boundary = Rectangle(0, 0, width, height)
                    self.quad_tree = QuadTree(boundary, 4)
                else:
                    return  # 如果無法獲取視窗大小，直接返回
            
            # 清空四叉樹
            if hasattr(self.quad_tree, "clear"):
                self.quad_tree.clear()
            
            # 將檢測到的物體添加到四叉樹和地圖記憶中
            for detection in detections:
                try:
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
                    
                    # 為後續處理添加中心點
                    detection["x_center"] = x_center
                    detection["y_center"] = y_center
                    
                    # 檢查是使用 'class_name' 還是 'class' 鍵
                    obj_class = detection.get("class_name", detection.get("class", "unknown"))
                    
                    world_pos = self.coordinate_transformer.screen_to_world(
                        (x_center, y_center)
                    )
                    
                    if world_pos:
                        # 插入到四叉樹
                        point = Point(world_pos[0], world_pos[1], detection)
                        self.quad_tree.insert(point)
                        
                        # 更新地圖記憶
                        if obj_class == "minimap_player":
                            self.map_memory.update_player_position(world_pos)
                        elif obj_class in ["game_portal", "minimap_portal"]:
                            self.map_memory.add_object("portal", world_pos, detection)
                        elif obj_class == "climbable_object":
                            self.map_memory.add_object("rope", world_pos, detection)
                except Exception as e:
                    self.ui.log(f"處理單個檢測結果時發生錯誤: {str(e)}")
            
            # 更新碰撞系統
            self.collision_system.update_from_detections(detections, self.coordinate_transformer)
        except Exception as e:
            self.ui.log(f"更新物體追蹤時發生錯誤: {str(e)}")
    
    def draw_detections(self, image, detections):
        """在圖像上繪製檢測結果"""
        for detection in detections:
            bbox = detection.get("bbox", [])
            if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
                continue  # 避免錯誤的 bbox 數據
                
            x1, y1, x2, y2 = map(int, bbox)
            class_name = detection.get("class_name", "unknown")
            confidence = detection.get("confidence", None)
            
            # 選擇顏色
            color = (0, 255, 0)  # 默認綠色
            if detection.get("is_minimap", False):
                color = (0, 0, 255)  # 小地圖元素使用紅色
            
            # 繪製邊界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # 構造標籤文字
            label = f"{class_name}"
            if confidence is not None:
                label += f" {confidence:.2f}"
            
            # 添加標籤
            cv2.putText(image, label, (x1, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    def start_auto_battle(self):
        """啟動自動戰鬥系統"""
        if not all([self.detector, self.window_capture, self.coordinate_transformer]):
            self.ui.log("錯誤: 請先啟動檢測過程")
            return
        
        try:
            # 初始化自動戰鬥系統
            self.auto_battle = AutoBattleSystem(
                window_capture=self.window_capture,
                detector=self.detector,
                monster_detector=self.monster_detector,
                coordinate_transformer=self.coordinate_transformer,
                controller=self
            )
            
            # 啟動自動戰鬥
            self.auto_battle.start()
            
            # 更新按鈕狀態
            self.ui.update_battle_buttons(True)
            self.ui.log("自動戰鬥系統已啟動 - 辨識怪物並接近攻擊")
        except Exception as e:
            self.ui.log(f"啟動自動戰鬥系統時發生錯誤: {str(e)}")
            self.ui.update_battle_buttons(False)
    
    def stop_auto_battle(self):
        """停止自動戰鬥系統"""
        if self.auto_battle:
            self.auto_battle.stop()
            self.ui.update_battle_buttons(False)
            self.ui.log("自動戰鬥系統已停止")
    
    def add_monster_template(self):
        """新增怪物模板"""
        # 檢查是否已經有截取的畫面
        if not hasattr(self, 'last_frame') or self.last_frame is None:
            self.ui.log("錯誤: 請先啟動檢測以取得畫面")
            return
        
        # 創建選擇區域功能
        self.ui.setup_template_selection()
    
    def process_selection(self, rect):
        """處理選擇區域的函數"""
        try:
            x1, y1, x2, y2 = rect
            
            # 獲取原始畫面的尺寸
            h, w = self.last_frame.shape[:2]
            
            # 獲取畫布尺寸
            canvas_width = self.ui.canvas.winfo_width()
            canvas_height = self.ui.canvas.winfo_height()
            
            # 輸出調試信息
            self.ui.log(f"畫布尺寸: {canvas_width}x{canvas_height}")
            self.ui.log(f"原始畫面尺寸: {w}x{h}")
            self.ui.log(f"選擇區域: ({x1},{y1}) -> ({x2},{y2})")
            
            # 確保 x1 < x2, y1 < y2
            if x1 > x2: x1, x2 = x2, x1
            if y1 > y2: y1, y2 = y2, y1
            
            # 計算原始畫面在畫布上的位置和尺寸
            # 根據畫布的大小，計算縮放比例
            scale = min(canvas_width / w, canvas_height / h)
            display_w = int(w * scale)
            display_h = int(h * scale)
            
            # 計算原始畫面在畫布上的偏移量
            offset_x = (canvas_width - display_w) // 2
            offset_y = (canvas_height - display_h) // 2
            
            # 確保選擇區域相對於偏移量
            x1 = max(0, x1 - offset_x)
            y1 = max(0, y1 - offset_y)
            x2 = max(0, x2 - offset_x)
            y2 = max(0, y2 - offset_y)
            
            # 將畫布坐標轉換為原始畫面坐標
            img_x1 = int(x1 / scale)
            img_y1 = int(y1 / scale)
            img_x2 = int(x2 / scale)
            img_y2 = int(y2 / scale)
            
            # 確保坐標在原始畫面範圍內
            img_x1 = max(0, min(img_x1, w-1))
            img_y1 = max(0, min(img_y1, h-1))
            img_x2 = max(0, min(img_x2, w-1))
            img_y2 = max(0, min(img_y2, h-1))
            
            # 確保選擇區域有效
            if img_x1 >= img_x2 or img_y1 >= img_y2:
                self.ui.log(f"錯誤: 選擇區域無效 ({img_x1},{img_y1}) -> ({img_x2},{img_y2})")
                return
            
            # 輸出轉換後的坐標
            self.ui.log(f"轉換後的區域: ({img_x1},{img_y1}) -> ({img_x2},{img_y2})")
            
            # 裁剪選擇的區域
            template = self.last_frame[img_y1:img_y2, img_x1:img_x2]
            
            if template.size == 0:
                self.ui.log("錯誤: 選擇區域無效 (模板大小為0)")
                return
            
            # 請求模板名稱
            template_name = self.ui.get_template_name()
            if not template_name:
                self.ui.log("用戶取消了添加模板")
                # 確保清除選擇
                if hasattr(self.ui, 'selection_rect') and self.ui.selection_rect:
                    self.ui.canvas.delete(self.ui.selection_rect)
                    self.ui.selection_rect = None
                return
            
            # 初始化怪物檢測器（如果尚未初始化）
            if not hasattr(self, 'monster_detector') or self.monster_detector is None:
                from MonsterDetection import TemplateMonsterDetector
                self.monster_detector = TemplateMonsterDetector()
            
            # 添加模板
            success = self.monster_detector.add_template(template_img=template, name=template_name)
            if success:
                self.ui.log(f"成功添加模板: {template_name}")
            else:
                self.ui.log("添加模板失敗")
        
        except Exception as e:
            import traceback
            self.ui.log(f"處理選擇區域時發生錯誤: {str(e)}")
            traceback.print_exc()
    
    def load_monster_template(self):
        """從檔案載入怪物模板"""
        try:
            # 開啟檔案選擇對話框
            filename = tk.filedialog.askopenfilename(
                title="選擇怪物模板檔案",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg"), ("All Files", "*.*")]
            )
            
            if not filename:
                self.ui.log("用戶取消了載入模板")
                return
            
            # 檢查檔案是否存在
            if not os.path.exists(filename):
                self.ui.log(f"錯誤: 檔案不存在 {filename}")
                return
            
            # 初始化怪物檢測器（如果尚未初始化）
            if not hasattr(self, 'monster_detector') or self.monster_detector is None:
                from MonsterDetection import TemplateMonsterDetector
                self.monster_detector = TemplateMonsterDetector()
            
            # 從檔案名稱獲取模板名稱，預設使用檔案名（不含副檔名）
            template_name = os.path.basename(filename).split('.')[0]
            
            # 添加模板
            success = self.monster_detector.add_template(template_path=filename, name=template_name)
            if success:
                self.ui.log(f"成功載入模板: {template_name}")
            else:
                self.ui.log("載入模板失敗")
                
        except Exception as e:
            self.ui.log(f"載入模板時發生錯誤: {str(e)}")
    
    def toggle_monster_detection(self):
        """切換怪物檢測狀態"""
        try:
            # 獲取UI中的怪物檢測狀態
            enabled = self.ui.is_monster_detection_enabled()
            
            # 設置控制器中的狀態變量
            self.monster_detection_enabled = enabled
            
            if enabled:
                self.ui.log("已啟用怪物檢測")
            else:
                self.ui.log("已停用怪物檢測")
                
        except Exception as e:
            self.ui.log(f"切換怪物檢測狀態時發生錯誤: {str(e)}")

    def on_key_press(self, key):
        """處理按鍵輸入，更新角色朝向"""
        try:
            if key == keyboard.Key.left:
                self.facing_direction = "left"
                print("角色朝向: 左")
            elif key == keyboard.Key.right:
                self.facing_direction = "right"
                print("角色朝向: 右")
            elif key == keyboard.Key.up:
                self.facing_direction = "up"
                print("角色朝向: 上")
            elif key == keyboard.Key.down:
                self.facing_direction = "down"
                print("角色朝向: 下")
        except AttributeError:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = MapleController(root)
    root.mainloop()
