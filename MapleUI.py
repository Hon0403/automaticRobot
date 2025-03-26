import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import cv2
import time
import numpy as np
from PIL import Image, ImageTk

class MapleUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller  # 控制器引用，用於連接UI與邏輯
        
        # UI元素變數
        self.current_image = None
        self.canvas = None
        self.log_text = None
        self.window_list = None
        self.model_path = None
        self.start_btn = None
        self.stop_btn = None
        self.start_battle_btn = None
        self.stop_battle_btn = None
        
        # 圈選相關變數
        self.selection_mode = False
        self.selection_start = None
        self.selection_rect = None
        
        # 初始化UI佈局
        self._setup_ui()
        
    def _setup_ui(self):
        """設置整體UI佈局"""
        self.root.title("楓之谷自動打怪助手")
        self.root.geometry("1200x700")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
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
        """創建控制面板"""
        # 視窗選擇區
        window_frame = ttk.LabelFrame(parent, text="視窗選擇", padding=5)
        window_frame.pack(fill=tk.X, pady=5)
        
        window_list_frame = ttk.Frame(window_frame)
        window_list_frame.pack(fill=tk.X)
        
        self.window_list = ttk.Combobox(window_list_frame, state="readonly", width=30)
        self.window_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        refresh_btn = ttk.Button(window_list_frame, text="刷新", 
                                command=self.controller.refresh_window_list)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        # 檢測按鈕區
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="開始檢測", 
                                   command=self.controller.start_detection)
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ttk.Button(button_frame, text="停止檢測", 
                                  command=self.controller.stop_detection, 
                                  state=tk.DISABLED)
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        # 自動打怪控制區
        battle_frame = ttk.LabelFrame(parent, text="自動打怪控制", padding=5)
        battle_frame.pack(fill=tk.X, pady=5)
        
        self.start_battle_btn = ttk.Button(battle_frame, text="開始自動打怪", 
                                         command=self.controller.start_auto_battle)
        self.start_battle_btn.pack(fill=tk.X, pady=2)
        
        self.stop_battle_btn = ttk.Button(battle_frame, text="停止自動打怪", 
                                        command=self.controller.stop_auto_battle, 
                                        state=tk.DISABLED)
        self.stop_battle_btn.pack(fill=tk.X, pady=2)
        
        # 怪物辨識控制區
        monster_frame = ttk.LabelFrame(parent, text="怪物模板匹配", padding=5)
        monster_frame.pack(fill=tk.X, pady=5)
        
        add_template_btn = ttk.Button(monster_frame, text="添加怪物模板",
                                    command=self.controller.add_monster_template)
        add_template_btn.pack(fill=tk.X, pady=2)
        
        load_template_btn = ttk.Button(monster_frame, text="載入怪物模板",
                               command=self.controller.load_monster_template)
        load_template_btn.pack(fill=tk.X, pady=2)

        self.enable_monster_detection = tk.BooleanVar(value=False)
        monster_check = ttk.Checkbutton(monster_frame, text="啟用怪物偵測",
                                      variable=self.enable_monster_detection,
                                      command=self.controller.toggle_monster_detection)
        monster_check.pack(fill=tk.X, pady=2)
    
    def create_display_panel(self, parent):
        """創建顯示面板"""
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
    
    def update_window_list(self, windows):
        """更新視窗選單內容"""
        self.window_list['values'] = windows
        if windows:
            self.window_list.current(0)
            self.log(f"找到 {len(windows)} 個視窗")
        else:
            self.log("未找到可用視窗")
    
    def get_selected_window(self):
        """獲取選中的視窗"""
        return self.window_list.get()
    
    def get_model_path(self):
        """獲取模型路徑"""
        return self.model_path.get()
    
    def update_detection_buttons(self, is_detecting):
        """更新檢測按鈕狀態"""
        if is_detecting:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def update_battle_buttons(self, is_battling):
        """更新自動打怪按鈕狀態"""
        if is_battling:
            self.start_battle_btn.config(state=tk.DISABLED)
            self.stop_battle_btn.config(state=tk.NORMAL)
        else:
            self.start_battle_btn.config(state=tk.NORMAL)
            self.stop_battle_btn.config(state=tk.DISABLED)
    
    def update_image(self, image):
        """更新畫面上顯示的圖像"""
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
    
    def log(self, message):
        """添加日誌訊息"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        # 在主線程中更新UI
        self.root.after(0, self._append_log, log_message)
    
    def _append_log(self, message):
        """實際添加日誌到文本框"""
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)  # 自動滾動到底部
    
    def is_monster_detection_enabled(self):
        """檢查怪物偵測是否啟用"""
        return self.enable_monster_detection.get()
    
    def setup_template_selection(self):
        """設置模板選擇模式"""
        self.selection_mode = True
        self.selection_start = None
        self.selection_rect = None
        
        # 綁定滑鼠事件
        self.canvas.bind("<ButtonPress-1>", self.on_selection_start)
        self.canvas.bind("<B1-Motion>", self.on_selection_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_selection_end)
        
        self.log("請在畫面上圈選怪物")

    def on_selection_start(self, event):
        """開始選擇區域"""
        if not self.selection_mode:
            return
        self.selection_start = (event.x, event.y)
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)

    def on_selection_move(self, event):
        """更新選擇區域"""
        if not self.selection_mode or not self.selection_start:
            return
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        
        x1, y1 = self.selection_start
        x2, y2 = event.x, event.y
        self.selection_rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

    def on_selection_end(self, event):
        """完成選擇區域"""
        if not self.selection_mode or not self.selection_start:
            return
        
        x1, y1 = self.selection_start
        x2, y2 = event.x, event.y
        
        # 確保x1 < x2, y1 < y2
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1
        
        # 清除選擇框
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None

        # 如果選擇區域過小，忽略
        if x2 - x1 < 10 or y2 - y1 < 10:
            # 退出選擇模式
            self.selection_mode = False
            self.canvas.unbind("<ButtonPress-1>")
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")
            return
        
        # 通知控制器處理選擇區域
        self.controller.process_selection((x1, y1, x2, y2))
        
        # 退出選擇模式
        self.selection_mode = False
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

    def get_template_name(self):
        """獲取模板名稱"""
        name = simpledialog.askstring("模板名稱", "請輸入怪物模板名稱:")
        if name is None:  # 用戶點擊取消
            return None
        return name or f"monster_{int(time.time())}"
    
    def on_closing(self):
        """視窗關閉處理"""
        if messagebox.askokcancel("退出", "確定要退出程式嗎?"):
            try:
                self.controller.shutdown()
            except Exception as e:
                print(f"關閉時發生錯誤: {e}")
            finally:
                self.root.destroy()

    def shutdown(self):
        """處理程式關閉時的清理工作"""
        try:
            # 停止所有運行中的線程或進程
            if hasattr(self, 'detection_running') and self.detection_running:
                self.stop_detection()
            if hasattr(self, 'auto_battle') and self.auto_battle:
                self.stop_auto_battle()
        except Exception as e:
            print(f"關閉時發生錯誤: {e}")

    def show_image(self, image):
        try:
            # 獲取畫布尺寸
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 獲取圖像尺寸
            img_height, img_width = image.shape[:2]
            
            # 計算縮放比例
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            # 縮放圖像
            if scale < 1:
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # 將 OpenCV 格式的圖像轉換為 Tkinter 可用的格式
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
            tk_image = ImageTk.PhotoImage(image=pil_image)
            
            # 儲存引用以防垃圾回收
            self.current_image = tk_image
            
            # 檢查是否已經創建了圖像項目
            if not hasattr(self, 'image_id'):
                # 首次創建圖像
                self.image_id = self.canvas.create_image(
                    self.canvas.winfo_width() // 2,
                    self.canvas.winfo_height() // 2,
                    image=self.current_image,
                    anchor=tk.CENTER
                )
            else:
                # 更新現有圖像
                self.canvas.itemconfig(self.image_id, image=self.current_image)
                # 更新位置
                self.canvas.coords(self.image_id, 
                                  self.canvas.winfo_width() // 2,
                                  self.canvas.winfo_height() // 2)
        except Exception as e:
            self.log(f"顯示圖像時發生錯誤: {str(e)}")

