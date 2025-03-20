import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import threading
import time
import os
import sys
import numpy as np
from PIL import Image, ImageTk
import win32gui

from window_capture import WindowCapture
from detection import YOLODetector
from coordinate_system import CoordinateTransformer
from quadtree import QuadTree, Rectangle, Point
from action_controller import ActionController
from map_boundary import MapBoundaryManager

class AutoMapleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("遊戲自動移動助手")
        self.root.geometry("1200x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化變數
        self.window_capture = None
        self.detector = None
        self.coordinate_transformer = None
        self.quad_tree = None
        self.action_controller = None
        self.running = False
        self.detection_thread = None
        self.boundary_manager = MapBoundaryManager()
        self.current_image = None
        
        # 創建主框架
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左右分割
        self.left_frame = ttk.Frame(self.main_frame, width=400)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        
        self.right_frame = ttk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 創建控制面板和顯示面板
        self.create_control_panel(self.left_frame)
        self.create_display_panel(self.right_frame)
        
        # 初始化日誌
        self.log("程式已啟動")
    
    def create_control_panel(self, parent):
        # 視窗選擇區
        window_frame = ttk.LabelFrame(parent, text="視窗選擇", padding=5)
        window_frame.pack(fill=tk.X, pady=5)
        
        window_list_frame = ttk.Frame(window_frame)
        window_list_frame.pack(fill=tk.X)
        
        self.window_list = ttk.Combobox(window_list_frame, state="readonly", width=30)
        self.window_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        refresh_btn = ttk.Button(window_list_frame, text="刷新", command=self.refresh_window_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # 初始化時刷新視窗列表
        self.refresh_window_list()
        
        # 模型選擇區
        model_frame = ttk.LabelFrame(parent, text="模型選擇", padding=5)
        model_frame.pack(fill=tk.X, pady=5)
        
        self.model_path = tk.StringVar(value="models/best.pt")
        model_entry = ttk.Entry(model_frame, textvariable=self.model_path, width=30)
        model_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(model_frame, text="瀏覽", command=self.browse_model)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        # 操作按鈕區
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="開始檢測", command=self.start_detection)
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ttk.Button(button_frame, text="停止檢測", command=self.stop_detection, state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=2)
    
    def create_display_panel(self, parent):
        # 圖像顯示區
        display_frame = ttk.LabelFrame(parent, text="檢測顯示", padding=5)
        display_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.canvas = tk.Canvas(display_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 日誌顯示區
        log_frame = ttk.LabelFrame(parent, text="運行日誌", padding=5)
        log_frame.pack(fill=tk.BOTH, pady=5)
        
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=8, yscrollcommand=log_scroll.set)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        log_scroll.config(command=self.log_text.yview)
    
    def get_windows(self):
        """獲取所有可見視窗"""
        windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows
    
    def refresh_window_list(self):
        """刷新視窗列表"""
        try:
            windows = self.get_windows()
            window_titles = []
            
            for hwnd, title in windows:
                # 確保窗口標題不為空
                if title.strip():
                    window_titles.append(f"HWND: {hex(hwnd)}, 標題: {title}")
            
            # 更新下拉選單
            self.window_list['values'] = window_titles
            
            if window_titles:
                self.window_list.current(0)
                self.log(f"找到 {len(window_titles)} 個視窗")
            else:
                self.log("未找到可用視窗")
        except Exception as e:
            self.log(f"刷新視窗列表時出錯: {e}")
    
    def browse_model(self):
        filename = filedialog.askopenfilename(
            title="選擇YOLO模型",
            filetypes=[("PyTorch Models", "*.pt"), ("All Files", "*.*")]
        )
        if filename:
            self.model_path.set(filename)
            self.log(f"已選擇模型: {filename}")
    
    def start_detection(self):
        try:
            # 從下拉選單獲取選中的視窗
            selected_window = self.window_list.get()
            if not selected_window:
                messagebox.showerror("錯誤", "請選擇一個視窗")
                return
            
            # 正確解析視窗句柄 - 從"HWND: 0x260a4a, 標題: 快顯主機"格式
            hwnd_part = selected_window.split("HWND: ")[1].split(",")[0]
            hwnd = int(hwnd_part, 16)
            
            # 驗證視窗句柄有效性
            if not win32gui.IsWindow(hwnd):
                messagebox.showerror("錯誤", f"視窗句柄 {hwnd_part} 無效，請刷新列表重試")
                return
            
            # 初始化視窗捕獲器
            self.window_capture = WindowCapture(hwnd=hwnd)
            self.log(f"選擇視窗: {selected_window}")
            
            # 初始化檢測器
            self.detector = YOLODetector(self.model_path.get(), confidence_threshold=0.5)
            
            minimap_rect = (10, 10, 150, 150)  # 小地圖位置（假設值）
            self.coordinate_transformer = CoordinateTransformer(minimap_rect)
            
            # 初始化四叉樹
            world_bounds = self.boundary_manager.get_current_bounds()
            x_center = (world_bounds[0] + world_bounds[2]) / 2
            y_center = (world_bounds[1] + world_bounds[3]) / 2
            width = world_bounds[2] - world_bounds[0]
            height = world_bounds[3] - world_bounds[1]
            boundary = Rectangle(x_center, y_center, width, height)
            self.quad_tree = QuadTree(boundary, capacity=4)
            
            # 創建動作控制器
            self.action_controller = ActionController(
                self.window_capture,
                self.detector,
                self.coordinate_transformer,
                self.quad_tree
            )
            
            # 更新按鈕狀態
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # 設置運行標誌
            self.running = True
            
            # 啟動檢測線程
            self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
            self.detection_thread.start()
            
            self.log("開始檢測")
        except Exception as e:
            import traceback
            traceback.print_exc()  # 打印詳細錯誤信息
            self.log(f"啟動檢測失敗: {str(e)}")
    
    def detection_loop(self):
        try:
            while self.running:
                # 獲取當前畫面
                screen = self.window_capture.capture()
                if screen is None:
                    self.log("未能捕獲畫面，等待下一次嘗試")
                    time.sleep(0.5)
                    continue
                
                # 進行物體檢測
                detections = self.detector.detect(screen)
                
                # 更新四叉樹
                self.update_quad_tree(detections)
                
                # 繪製檢測結果
                self.draw_detections(screen.copy(), detections)
                
                # 短暫休眠
                time.sleep(0.1)
        except Exception as e:
            self.log(f"檢測循環出錯: {str(e)}")
    
    def update_quad_tree(self, detections):
        try:
            # 清空四叉樹中的暫時物體
            if hasattr(self.quad_tree, "clear"):
                self.quad_tree.clear()
            
            # 將檢測到的物體添加到四叉樹
            for detection in detections:
                try:
                    world_pos = self.coordinate_transformer.screen_to_world(
                        (detection["x_center"], detection["y_center"])
                    )
                    
                    if world_pos:
                        point = Point(world_pos[0], world_pos[1], detection)
                        self.quad_tree.insert(point)
                except Exception as e:
                    self.log(f"添加檢測點到四叉樹時出錯: {e}")
                    
            # 更新邊界管理器
            self.boundary_manager.update_from_detections(detections, self.coordinate_transformer)
        except Exception as e:
            self.log(f"更新四叉樹出錯: {str(e)}")
    
    def draw_detections(self, image, detections):
        try:
            # 繪製檢測框
            for detection in detections:
                x1, y1, x2, y2 = detection["box"]
                label = detection["class"]
                confidence = detection["confidence"]
                
                # 繪製矩形框
                cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                
                # 繪製標籤
                cv2.putText(image, f"{label} {confidence:.2f}",
                            (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (0, 255, 0), 2)
            
            # 繪製動態邊界
            try:
                bounds = self.boundary_manager.get_current_bounds()
                tl = self.coordinate_transformer.world_to_screen((bounds[0], bounds[1]))
                br = self.coordinate_transformer.world_to_screen((bounds[2], bounds[3]))
                
                if tl and br:  # 確保座標有效
                    cv2.rectangle(image, 
                                (int(tl[0]), int(tl[1])), 
                                (int(br[0]), int(br[1])), 
                                (255, 0, 0), 1)
            except:
                pass  # 忽略邊界繪製錯誤
            
            # 調整圖像大小以適應畫布
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                # 保持長寬比縮放
                h, w = image.shape[:2]
                
                # 計算縮放因子
                scale = min(canvas_width / w, canvas_height / h)
                
                # 縮放圖像
                new_width = int(w * scale)
                new_height = int(h * scale)
                
                resized = cv2.resize(image, (new_width, new_height))
                
                # 轉換為PIL格式
                image_rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
                tk_image = ImageTk.PhotoImage(pil_image)
                
                # 在主線程中更新UI
                self.root.after(0, self.update_image, tk_image)
        except Exception as e:
            self.log(f"繪製檢測結果出錯: {str(e)}")
    
    def update_image(self, image):
        # 儲存引用以防垃圾回收
        self.current_image = image
        
        # 在畫布上顯示圖像
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self.current_image,
            anchor=tk.CENTER
        )
    
    def stop_detection(self):
        self.running = False
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=1.0)
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("停止檢測")
    
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # 在主線程中更新UI
        self.root.after(0, self._append_log, log_message)
    
    def _append_log(self, message):
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)  # 自動滾動到底部
    
    def on_closing(self):
        if messagebox.askokcancel("退出", "確定要退出程式嗎?"):
            self.running = False
            self.root.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoMapleGUI(root)
    root.mainloop()
