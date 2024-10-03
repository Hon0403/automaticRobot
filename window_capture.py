# window_capture.py
import pygetwindow as gw
import pyautogui
import numpy as np
import cv2

def capture_window(window_title, target_size=(640, 640)):
    window = gw.getWindowsWithTitle(window_title)[0]
    if window:
        width, height = window.width, window.height
        left, top = window.left, window.top
        bbox = (left, top, width, height)
        screenshot = pyautogui.screenshot(region=bbox)
        img = np.array(screenshot)
        
        # 調整圖像大小
        resized_img = cv2.resize(img, target_size)
        return resized_img
    else:
        print("無法獲取選定的視窗")
        return None

def show_selected_window(window_title):
    screenshot = capture_window(window_title)
    if screenshot is not None:
        # 保持原始顏色，不轉換為灰度圖像
        cv2.imwrite(f'{window_title}.png', cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))  # 保存圖像
        print(f"圖像已保存為 '{window_title}.png'")
    else:
        print("無法捕獲選定的視窗")