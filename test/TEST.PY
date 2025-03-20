import cv2
import numpy as np
from ultralytics import YOLO
import torch

# 加載模型
model_path = "MODELS/best.pt"
model = YOLO(model_path)

# 設定類別名稱和顏色 (可以根據您的模型類別進行修改)
CLASS_NAMES = {
    0: "climbable_object",
    1: "game_portal",
    2: "minimap_player",
    3: "minimap_portal",
    # 根據您的模型添加更多類別
}

# 為不同類別定義不同顏色 (BGR格式)
CLASS_COLORS = {
    0: (0, 255, 0),    # 綠色
    1: (255, 0, 0),    # 藍色
    2: (0, 0, 255),    # 紅色
    3: (255, 255, 0),  # 青色
    4: (0, 255, 255),  # 黃色
    # 可以添加更多顏色
}

# 繪製檢測結果
def draw_detections(image, detections):
    detection_image = image.copy()
    height, width = image.shape[:2]
    
    # 檢測到的物體數量
    num_detected = len(detections)
    print(f"成功檢測到 {num_detected} 個物體")
    
    # 在圖像上繪製每個檢測框
    for detection in detections:
        x1, y1, x2, y2, confidence, cls_id = detection
        
        # 確保座標在圖像範圍內並轉換為整數
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        x1, x2 = max(0, min(x1, width-1)), max(0, min(x2, width-1))
        y1, y2 = max(0, min(y1, height-1)), max(0, min(y2, height-1))
        
        # 獲取類別名稱
        cls_id = int(cls_id)
        cls_name = CLASS_NAMES.get(cls_id, f"類別{cls_id}")
        
        # 獲取類別顏色，如果沒有預定義則使用綠色
        color = CLASS_COLORS.get(cls_id, (0, 255, 0))
        
        # 根據置信度調整線條粗細
        thickness = max(1, int(confidence * 4))  # 置信度越高，線條越粗
        
        # 繪製矩形框
        cv2.rectangle(detection_image, (x1, y1), (x2, y2), color, thickness)
        
        # 準備標籤文字
        label = f"{cls_name}: {confidence:.2f}"
        
        # 計算文字大小
        (text_width, text_height), baseline = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
        )
        
        # 確保標籤在圖像範圍內
        y_label = max(y1 - 10, text_height + 5)
        
        # 繪製標籤背景區域
        cv2.rectangle(
            detection_image, 
            (x1, y_label - text_height - 5), 
            (min(x1 + text_width, width-1), y_label + baseline - 5), 
            color, 
            -1  # 填充矩形
        )
        
        # 繪製標籤文字
        cv2.putText(
            detection_image, 
            label, 
            (x1, y_label - 5), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (255, 255, 255),  # 白色文字
            1, 
            cv2.LINE_AA
        )
        
        # 顯示檢測物體的信息在控制台
        print(f"檢測到: {cls_name}, 置信度: {confidence:.4f}, 位置: ({x1},{y1})-({x2},{y2})")
    
    return detection_image

# 預測函數
def predict(image_path, confidence_threshold=0.3):
    # 載入原始圖像用於繪製
    original_image = cv2.imread(image_path)
    if original_image is None:
        raise ValueError(f"無法加載圖片: {image_path}")
    
    print(f"原始圖片尺寸: {original_image.shape[:2]}")
    
    # 使用YOLO模型進行預測
    results = model(image_path, conf=confidence_threshold)
    
    # 獲取檢測框資訊
    if len(results) > 0:
        # 將結果轉換為numpy數組
        boxes = results[0].boxes
        detections = []
        
        # 獲取所有檢測結果
        if len(boxes) > 0:
            # 轉換為numpy數組
            if torch.is_tensor(boxes.xyxy):
                xyxy = boxes.xyxy.cpu().numpy()
            else:
                xyxy = boxes.xyxy
            
            if torch.is_tensor(boxes.conf):
                conf = boxes.conf.cpu().numpy()
            else:
                conf = boxes.conf
            
            if torch.is_tensor(boxes.cls):
                cls = boxes.cls.cpu().numpy()
            else:
                cls = boxes.cls
            
            # 組合檢測結果
            for i in range(len(boxes)):
                x1, y1, x2, y2 = xyxy[i]
                confidence = conf[i]
                class_id = cls[i]
                detections.append([x1, y1, x2, y2, confidence, class_id])
    else:
        detections = []
    
    print(f"檢測結果數量: {len(detections)}")
    
    # 繪製檢測結果
    detection_image = draw_detections(original_image, detections)
    
    return detection_image, detections

# 主程式
if __name__ == "__main__":
    image_path = "D:\\label-studio-develop\\Object Detection\\2025-03-11 154930.png"
    confidence_threshold = 0.3  # 可調整置信度閾值
    
    try:
        output_image, detections = predict(image_path, confidence_threshold)
        if output_image is not None:
            cv2.imshow("YOLOv8 物體檢測", output_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            cv2.imwrite("output_detection.jpg", output_image)  # 儲存輸出圖片
            print(f"檢測結果已保存為 output_detection.jpg")
            
            # 輸出檢測到的各類物體數量統計
            class_counts = {}
            for _, _, _, _, _, cls_id in detections:
                cls_name = CLASS_NAMES.get(int(cls_id), f"類別{int(cls_id)}")
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                
            print("\n檢測結果統計:")
            for cls_name, count in class_counts.items():
                print(f"- {cls_name}: {count} 個")
    except Exception as e:
        print(f"錯誤: {e}")
        import traceback
        traceback.print_exc()
