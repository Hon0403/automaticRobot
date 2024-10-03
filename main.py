import os
import customtkinter as ctk
import cv2
import pyautogui
import numpy as np
import onnxruntime as ort
import keyboard
import pygetwindow as gw
import threading

from detection import start_detection, show_detection, detect_windows  # 刪除 capture_window 的導入
from window_capture import show_selected_window

# 指定模型檔案所在的資料夾路徑
folder_path = "./models"

# 讀取資料夾中的模型檔案
model_files = [f for f in os.listdir(folder_path) if f.endswith('.onnx')]  # 假設模型檔案是 .onnx 格式

# 建立主窗口
window = ctk.CTk()
window.title("阿爾比恩機器人")
window.geometry("250x650")  # 設置窗口大小
window.resizable(width=False, height=False)

# 建立 Frame
frame_model = ctk.CTkFrame(window)
frame_model.pack(padx=10, pady=10, fill="x")

# 在 Frame 中加入 Label 和模型下拉選單
label_model = ctk.CTkLabel(frame_model, text="選擇模型")
label_model.pack(pady=5)
selected_model = ctk.StringVar()
combo_model = ctk.CTkComboBox(frame_model, variable=selected_model, values=model_files)
combo_model.pack(pady=10, padx=10, fill="x")

# 設置預設選項
if model_files:
    combo_model.set(model_files[0])  # 設置第一個選項為預設選項

# 建立 Frame 來顯示視窗
frame_window = ctk.CTkFrame(window)
frame_window.pack(padx=10, pady=10, fill="x")

# 在 Frame 中加入 Label 和視窗下拉選單
label_window = ctk.CTkLabel(frame_window, text="選擇視窗")
label_window.pack(pady=5)
selected_window = ctk.StringVar()
combo_window = ctk.CTkComboBox(frame_window, variable=selected_window)
combo_window.pack(pady=10, padx=10, fill="x")

# 添加等待時間設置
wait_time_var = ctk.DoubleVar(value=0.5)
wait_time_frame = ctk.CTkFrame(window)
wait_time_frame.pack(padx=10, pady=10, fill="x")
wait_time_label = ctk.CTkLabel(wait_time_frame, text="設置等待時間 (秒)")
wait_time_label.pack(anchor="w", padx=10, pady=5)
wait_time_entry = ctk.CTkEntry(wait_time_frame, textvariable=wait_time_var)
wait_time_entry.pack(anchor="w", padx=10, pady=5)

# 添加顯示解析度的文字方塊
resolution_text = ctk.CTkTextbox(window, height=2, width=40)
resolution_text.pack(pady=10, padx=10, fill="x")

# 定義關閉程式的函數
def close_program():
    print("程式已關閉")
    window.destroy()

# 設置快捷鍵來關閉程式
keyboard.add_hotkey('ctrl+q', close_program)

# 添加顯示檢測畫面的開關
show_detection_var = ctk.BooleanVar(value=False)
stop_event = threading.Event()

def toggle_detection():
    if show_detection_var.get():
        print("顯示檢測畫面")
        stop_event.clear()
        selected_window_title = selected_window.get()  # 獲取選定的視窗標題
        bring_window_to_front(selected_window_title)
        detection_thread = threading.Thread(target=show_detection, args=(folder_path, selected_model.get(), selected_window_title, "640x640", stop_event))
        detection_thread.start()
    else:
        print("隱藏檢測畫面")
        stop_event.set()
        cv2.destroyAllWindows()  # 隱藏檢測畫面

# 使用 CustomTkinter 的 Switch 作為切換拉桿
toggle_switch = ctk.CTkSwitch(window, text="顯示檢測畫面", variable=show_detection_var, command=toggle_detection)
toggle_switch.pack(pady=10, padx=10, fill="x")

# 將目標視窗設置為前台的函數
def bring_window_to_front(window_title):
    window = gw.getWindowsWithTitle(window_title)
    if window:
        window[0].activate()
    else:
        print(f"Error: No window found with title '{window_title}'")

# 修改開始檢測按鈕的命令
def start():
    wait_time = wait_time_var.get()
    selected_window_title = selected_window.get()  # 獲取選定的視窗標題
    
    # 將目標視窗設置為前台
    bring_window_to_front(selected_window_title)
    
    print("運行視覺檢測")
    start_detection(folder_path, selected_model.get(), selected_window_title, "640x640", wait_time, show_detection_var.get())

start_button = ctk.CTkButton(window, text="開始檢測", command=start)
start_button.pack(pady=10, padx=10, fill="x")

# 定義停止檢測的函數
def stop_detection():
    print("檢測已停止")
    # 在這裡添加停止檢測的邏輯
    # 例如，設置一個標誌來停止檢測循環

# 新增停止檢測按鈕
stop_button = ctk.CTkButton(window, text="停止檢測", command=stop_detection)
stop_button.pack(pady=10, padx=10, fill="x")

# 在主窗口中加入按鈕來顯示選定的視窗
capture_button = ctk.CTkButton(window, text="顯示選定視窗", command=lambda: show_selected_window(selected_window.get()))
capture_button.pack(pady=10, padx=10, fill="x")

# 更新下拉選單的函數
def update_dropdown():
    windows = detect_windows()
    combo_window.configure(values=windows)
    if windows:
        selected_window.set(windows[0])

    # 更新選擇視窗的事件處理
    combo_window.bind("<<ComboboxSelected>>", update_resolution_text)

# 更新文字方塊的函數
def update_resolution_text(event):
    window = gw.getWindowsWithTitle(selected_window.get())[0]
    resolution = f"解析度: {window.width}x{window.height}"
    
    # 更新文字方塊內容
    resolution_text.delete(1.0, "end")
    resolution_text.insert("end", resolution)

# 初始化時更新下拉選單
update_dropdown()

window.mainloop()
