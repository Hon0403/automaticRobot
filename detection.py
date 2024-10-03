# detection.py
import os
import cv2
import numpy as np
import onnxruntime as ort
import pygetwindow as gw
import pyautogui
import time

pyautogui.FAILSAFE = False  # 禁用安全機制

def preprocess_image(image, target_size=(640, 640)):
    resized_image = cv2.resize(image, target_size, interpolation=cv2.INTER_CUBIC)
    normalized_image = resized_image.astype(np.float32) / 255.0
    input_image = np.transpose(normalized_image, (2, 0, 1))  # 轉換為 (channels, height, width)
    input_image = np.expand_dims(input_image, axis=0)  # 添加 batch 維度
    print("Preprocessed Image Shape:", input_image.shape)  # 應該是 (1, 3, 640, 640)
    return input_image

def enhance_image(image):
    alpha = 1.5  # 對比度控制 (1.0-3.0)
    beta = 20    # 亮度控制 (0-100)
    
    # 移除 batch 維度，從 (1, 3, 640, 640) 變為 (3, 640, 640)
    enhanced_image = np.squeeze(image, axis=0)
    
    # 轉換圖像的 shape 從 (channels, height, width) 變回 (height, width, channels)
    enhanced_image = np.transpose(enhanced_image, (1, 2, 0))  # (640, 640, 3)
    
    # 對比度和亮度調整，但不改變顏色
    enhanced_image = cv2.convertScaleAbs(enhanced_image, alpha=alpha, beta=beta)
    
    # 確保顏色保持不變
    enhanced_image = cv2.cvtColor(enhanced_image, cv2.COLOR_BGR2RGB)
    
    # 將圖像轉回 (channels, height, width) 的順序，並添加 batch 維度
    enhanced_image = enhanced_image.astype(np.float32) / 255.0
    enhanced_image = np.transpose(enhanced_image, (2, 0, 1))  # (3, 640, 640)
    return np.expand_dims(enhanced_image, axis=0)  # (1, 3, 640, 640)

def start_detection(folder_path, model_file, window_title, resolution, wait_time, show_detection):
    model_path = os.path.join(folder_path, model_file)
    ort_session = ort.InferenceSession(model_path)

    while True:
        image = capture_game_window(window_title)
        if image is None:
            print(f"Error: Unable to capture window with title '{window_title}'")
            break

        original_shape = image.shape
        image_resized = preprocess_image(image)
        image_resized = enhance_image(image_resized)

        if image_resized is None:
            print("Error: Image preprocessing failed.")
            break

        ort_inputs = {ort_session.get_inputs()[0].name: image_resized}
        detections = ort_session.run(None, ort_inputs)

        for detection in detections[0][0]:
            confidence = detection[2]
            if confidence > 0.5:
                x1, y1, x2, y2 = detection[3:7]
                x1, y1, x2, y2 = max(0, min(1, x1)), max(0, min(1, y1)), max(0, min(1, x2)), max(0, min(1, y2))
                x1, y1, x2, y2 = int(x1 * original_shape[1]), int(y1 * original_shape[0]), int(x2 * original_shape[1]), int(y2 * original_shape[0])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(original_shape[1], x2), min(original_shape[0], y2)
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

                click_x, click_y = (x1 + x2) // 2, (y1 + y2) // 2
                click_resource(window_title, click_x, click_y)
                time.sleep(wait_time)

        if show_detection:
            cv2.imshow("Real-time Detection", image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            cv2.destroyAllWindows()

    cv2.destroyAllWindows()

def show_detection(folder_path, model_file, window_title, resolution, stop_event):
    model_path = os.path.join(folder_path, model_file)
    ort_session = ort.InferenceSession(model_path)

    while not stop_event.is_set():
        image = capture_game_window(window_title)
        if image is None:
            print(f"Error: Unable to capture window with title '{window_title}'")
            break

        original_shape = image.shape
        image_resized = preprocess_image(image)
        image_resized = enhance_image(image_resized)

        if image_resized is None:
            print("Error: Image preprocessing failed.")
            break

        ort_inputs = {ort_session.get_inputs()[0].name: image_resized}
        detections = ort_session.run(None, ort_inputs)

        for detection in detections[0][0]:
            confidence = detection[2]
            if confidence > 0.5:
                x1, y1, x2, y2 = detection[3:7]
                x1, y1, x2, y2 = max(0, min(1, x1)), max(0, min(1, y1)), max(0, min(1, x2)), max(0, min(1, y2))
                x1, y1, x2, y2 = int(x1 * original_shape[1]), int(y1 * original_shape[0]), int(x2 * original_shape[1]), int(y2 * original_shape[0])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(original_shape[1], x2), min(original_shape[0], y2)
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow("Real-time Detection", image)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

def detect_windows():
    windows = gw.getAllTitles()
    return [window for window in windows if window]

def click_resource(window_title, x, y):
    window = gw.getWindowsWithTitle(window_title)
    if not window:
        print(f"Error: No window found with title '{window_title}'")
        return
    window = window[0]
    screen_x = window.left + x
    screen_y = window.top + y
    pyautogui.click(screen_x, screen_y)

def capture_game_window(window_title):
    window = gw.getWindowsWithTitle(window_title)
    if not window:
        print(f"Error: No window found with title '{window_title}'")
        return None
    window = window[0]
    screenshot = pyautogui.screenshot(region=(window.left, window.top, window.width, window.height))
    image = np.array(screenshot)
    print("Captured Image Shape:", image.shape)
    return image
