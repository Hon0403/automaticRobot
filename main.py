# main.py
import os
import customtkinter as ctk
import cv2
import numpy as np
import onnxruntime as ort
import keyboard
import pygetwindow as gw
import threading

from detection import start_detection, show_detection, detect_windows
from window_capture import show_selected_window

# 指定模型檔案所在的資料夾路徑
folder_path = "./models"

# 讀取資料夾中的模型檔案
model_files = [f for f in os.listdir(folder_path) if f.endswith('.onnx')]

# 建立主窗口
window = ctk.CTk()
window.title("阿爾比恩機器人")
window.geometry("250x500")
window.resizable(width=False, height=False)

# 建立 Frame
def create_frame(parent, text, values, variable):
    frame = ctk.CTkFrame(parent)
    frame.pack(padx=10, pady=10, fill="x")
    label = ctk.CTkLabel(frame, text=text)
    label.pack(pady=5)
    combo = ctk.CTkComboBox(frame, variable=variable, values=values)
    combo.pack(pady=10, padx=10, fill="x")
    return combo

selected_model = ctk.StringVar()
combo_model = create_frame(window, "選擇模型", model_files, selected_model)

selected_window = ctk.StringVar()
combo_window = create_frame(window, "選擇視窗", [], selected_window)

# 設置預設選項
if model_files:
    combo_model.set(model_files[0])

# 添加等待時間設置
wait_time_var = ctk.DoubleVar(value=0.5)
wait_time_frame = ctk.CTkFrame(window)
wait_time_frame.pack(padx=10, pady=10, fill="x")
wait_time_label = ctk.CTkLabel(wait_time_frame, text="設置等待時間 (秒)")
wait_time_label.pack(anchor="w", padx=10, pady=5)
wait_time_entry = ctk.CTkEntry(wait_time_frame, textvariable=wait_time_var)
wait_time_entry.pack(anchor="w", padx=10, pady=5)

# 定義關閉程式的函數
def close_program():
    print("程式已關閉")
    window.destroy()

# 設置快捷鍵來關閉程式
keyboard.add_hotkey('ctrl+q', close_program)

# 添加顯示檢測畫面的開關
show_detection_var = ctk.BooleanVar(value=False)
stop_event = threading.Event()
detection_thread = None

def toggle_detection():
    global detection_thread
    if show_detection_var.get():
        print("顯示檢測畫面")
        stop_event.clear()
        selected_window_title = selected_window.get()
        bring_window_to_front(selected_window_title)
        detection_thread = threading.Thread(target=show_detection, args=(folder_path, selected_model.get(), selected_window_title, "640x640", stop_event))
        detection_thread.start()
    else:
        print("隱藏檢測畫面")
        stop_event.set()
        if detection_thread and detection_thread.is_alive():
            detection_thread.join()
        cv2.destroyAllWindows()
    
    # 確保主視窗保持在前台並且不會被最小化
    window.deiconify()
    window.lift()
    window.attributes('-topmost', True)
    window.attributes('-topmost', False)

toggle_switch = ctk.CTkSwitch(window, text="顯示檢測畫面", variable=show_detection_var, command=toggle_detection)
toggle_switch.pack(pady=10, padx=10, fill="x")

def bring_window_to_front(window_title):
    window_list = gw.getWindowsWithTitle(window_title)
    if window_list:
        window_list[0].activate()
    else:
        print(f"錯誤: 找不到標題為 '{window_title}' 的視窗")

def start():
    wait_time = wait_time_var.get()
    selected_window_title = selected_window.get()
    bring_window_to_front(selected_window_title)
    print("運行視覺檢測")
    start_detection(folder_path, selected_model.get(), selected_window_title, "640x640", wait_time, show_detection_var.get())

start_button = ctk.CTkButton(window, text="開始檢測", command=start)
start_button.pack(pady=10, padx=10, fill="x")

def stop_detection():
    global detection_thread
    print("檢測已停止")
    stop_event.set()
    if detection_thread and detection_thread.is_alive():
        detection_thread.join()
    cv2.destroyAllWindows()

stop_button = ctk.CTkButton(window, text="停止檢測", command=stop_detection)
stop_button.pack(pady=10, padx=10, fill="x")

capture_button = ctk.CTkButton(window, text="顯示選定視窗", command=lambda: show_selected_window(selected_window.get()))
capture_button.pack(pady=10, padx=10, fill="x")

def update_dropdown():
    windows = detect_windows()
    combo_window.configure(values=windows)
    if windows:
        selected_window.set(windows[0])
    else:
        selected_window.set("")

# 手動觸發一次事件來檢查是否能夠正確顯示視窗
update_dropdown()  # 自動選擇第一個視窗

window.mainloop()
