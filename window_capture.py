import pygetwindow as gw
import pyautogui
import numpy as np
import cv2
import win32gui

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
    
    def capture(self):
        """捕獲視窗畫面"""
        try:
            # 優先使用視窗標題查找
            if self.window_title:
                windows = gw.getWindowsWithTitle(self.window_title)
                if windows:
                    window = windows[0]
                    
                    # 獲取視窗位置和大小
                    left, top = window.left, window.top
                    width, height = window.width, window.height
                    
                    # 使用 pyautogui 截圖
                    screenshot = pyautogui.screenshot(region=(left, top, width, height))
                    
                    # 轉換為 numpy 數組
                    img = np.array(screenshot)
                    
                    # 轉換顏色空間 (RGB 轉 BGR)
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    
                    return img
            
            return None
        except Exception as e:
            print(f"捕獲視窗時出錯: {e}")
            return None
    
    def get_window_rect(self):
        """獲取視窗矩形位置"""
        try:
            if self.window_title:
                windows = gw.getWindowsWithTitle(self.window_title)
                if windows:
                    window = windows[0]
                    return (window.left, window.top, window.width, window.height)
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
                windows.append((hwnd, win32gui.GetWindowText(hwnd)))
            return True
        
        win32gui.EnumWindows(callback, windows)
        return windows
