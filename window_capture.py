import win32gui
import numpy as np
import cv2
import dxcam  # 需要先安裝：pip install dxcam

class WindowCapture:
    def __init__(self, window_title=None, hwnd=None):
        """初始化視窗捕獲器
        
        參數:
            window_title: 視窗標題
            hwnd: 視窗句柄（如果提供，則優先使用）
        """
        self.window_title = window_title
        self.hwnd = hwnd
        
        # 如果提供了句柄，則嘗試獲取視窗標題
        if hwnd and not window_title:
            self.window_title = win32gui.GetWindowText(hwnd)
        
        # 初始化DXGI捕獲器
        try:
            self.camera = dxcam.create(output_idx=0)  # 通常0是主顯示器
        except Exception as e:
            print(f"初始化DXGI捕獲器時出錯: {e}")
            self.camera = None
    
    def capture(self):
        """捕獲視窗畫面"""
        try:
            if self.camera is None:
                print("DXGI捕獲器未初始化")
                return None
                
            # 獲取視窗位置
            window_rect = self.get_window_rect()
            if not window_rect:
                return None
                
            # 擷取視窗區域
            left, top, width, height = window_rect
            frame = self.camera.grab(region=(left, top, left+width, top+height))
            
            # 確保捕獲成功
            if frame is None:
                return None
                
            # dxcam返回的已經是numpy陣列，需要轉換顏色空間
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
            
        except Exception as e:
            print(f"捕獲視窗時出錯: {e}")
            return None
    
    def get_window_rect(self):
        """獲取視窗矩形位置"""
        try:
            if self.hwnd:
                # 使用win32gui獲取窗口位置
                rect = win32gui.GetWindowRect(self.hwnd)
                left, top, right, bottom = rect
                width = right - left
                height = bottom - top
                return (left, top, width, height)
            elif self.window_title:
                # 通過標題查找窗口
                hwnd = win32gui.FindWindow(None, self.window_title)
                if hwnd:
                    rect = win32gui.GetWindowRect(hwnd)
                    left, top, right, bottom = rect
                    width = right - left
                    height = bottom - top
                    return (left, top, width, height)
            return None
        except Exception as e:
            print(f"獲取視窗位置時出錯: {e}")
            return None
    
    @staticmethod
    def list_window_names():
        """列出所有可見視窗名稱和句柄"""
        windows = []
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                title = win32gui.GetWindowText(hwnd)
                windows.append((hwnd, title))
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows

    def capture_region(self, region=None):
        """
        截取螢幕特定區域的圖像
    
        參數:
            region: 四元組 (left, top, width, height) 表示要截取的區域
        
        返回:
            特定區域的截圖，格式為numpy數組
        """
        try:
            if self.camera is None:
                print("DXGI捕獲器未初始化")
                return None
                
            # 如果沒有指定區域，則截取整個視窗
            if region is None:
                return self.capture()
            
            # 解析區域參數
            left, top, width, height = region
            
            # 使用DXGI捕獲指定區域
            frame = self.camera.grab(region=(left, top, left+width, top+height))
            
            # 確保捕獲成功
            if frame is None:
                return None
                
            # 轉換顏色空間
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
            
        except Exception as e:
            print(f"捕獲區域時出錯: {e}")
            return None
    
    def capture(self):
        try:
            if self.camera is None:
                print("DXGI捕獲器未初始化")
                return None

            import pyautogui
            frame = pyautogui.screenshot()
            frame = np.array(frame)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # 獲取視窗位置
            window_rect = self.get_window_rect()
            if not window_rect:
                return None

            # 擷取視窗區域，考慮視窗邊框
            left, top, width, height = window_rect

            # 調整捕捉範圍以確保完整捕捉（可能需要增加邊距）
            # 嘗試捕捉稍大區域以確保完整內容
            padding = 10  # 嘗試增加10像素邊距
            frame = self.camera.grab(region=(left - padding, top - padding, 
                                             left + width + padding, top + height + padding))

            # 確保捕獲成功
            if frame is None:
                return None

            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
        except Exception as e:
            print(f"捕獲視窗時出錯: {e}")
            return None
