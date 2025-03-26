import cv2
import numpy as np
from ultralytics import YOLO
import os

class YOLODetector:
    def __init__(self, minimap_model_path=None, terrain_model_path=None, confidence_threshold=0.25):
        """初始化YOLO檢測器，支援兩個不同的模型"""
        self.confidence_threshold = confidence_threshold
        self.last_detections = []
        self.minimap_model = None
        self.terrain_model = None
        
        # 載入小地圖模型
        if minimap_model_path and os.path.exists(minimap_model_path):
            self.minimap_model = self._safe_load_model(minimap_model_path)
            print(f"成功載入小地圖模型: {minimap_model_path}")
            
        # 載入地形模型
        if terrain_model_path and os.path.exists(terrain_model_path):
            self.terrain_model = self._safe_load_model(terrain_model_path)
            print(f"成功載入地形模型: {terrain_model_path}")
    
    def _safe_load_model(self, model_path):
        """安全載入模型，處理可能的異常"""
        try:
            model = YOLO(model_path, task='detect')  # 明確指定任務類型
            return model
        except Exception as e:
            print(f"載入模型時發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def detect(self, image, model_type='terrain'):
        """使用指定的模型類型檢測圖像中的物體"""
        if model_type == 'terrain' and self.terrain_model:
            model = self.terrain_model
        elif model_type == 'minimap' and self.minimap_model:
            model = self.minimap_model
        else:
            print(f"警告: 未找到指定的模型類型 {model_type}")
            return []
        
        try:
            # 使用YOLO模型進行預測
            results = model.predict(source=image, conf=self.confidence_threshold)
            
            # 處理結果
            detections = []
            for result in results:
                boxes = result.boxes
                for i in range(len(boxes)):
                    try:
                        # 獲取邊界框座標
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                        confidence = boxes.conf[i].item()
                        class_id = int(boxes.cls[i].item())
                        class_name = result.names[class_id]
                        
                        detection = {
                            'bbox': (x1, y1, x2, y2),
                            'confidence': confidence,
                            'class_id': class_id,
                            'class_name': class_name
                        }
                        detections.append(detection)
                    except Exception as e:
                        print(f"處理檢測框時發生錯誤: {str(e)}")
            
            self.last_detections = detections
            return detections
        except Exception as e:
            print(f"檢測過程中發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    
    def get_last_detections(self):
        """獲取最近一次的檢測結果"""
        return self.last_detections

# 物體追蹤器類 - 修復 'x_center' 錯誤
class ObjectTracker:
    def __init__(self):
        self.tracked_objects = {}
        self.next_id = 0
    
    def update(self, detections):
        # 儲存當前已檢測到的物體ID
        current_ids = []
        
        for detection in detections:
            try:
                # 計算物體中心點
                x1, y1, x2, y2 = detection['bbox']
                x_center = (x1 + x2) / 2
                y_center = (y1 + y2) / 2
                
                # 檢查是否為已追蹤的物體
                matched = False
                for obj_id, obj in self.tracked_objects.items():
                    # 計算中心點距離
                    dist = np.sqrt((x_center - obj['x_center'])**2 + (y_center - obj['y_center'])**2)
                    if dist < 50:  # 距離閾值，可調整
                        # 更新已有物體
                        obj['bbox'] = (x1, y1, x2, y2)
                        obj['x_center'] = x_center
                        obj['y_center'] = y_center
                        obj['class_name'] = detection['class_name']
                        obj['confidence'] = detection['confidence']
                        obj['last_seen'] = 0
                        matched = True
                        current_ids.append(obj_id)
                        break
                
                if not matched:
                    # 添加新物體
                    self.tracked_objects[self.next_id] = {
                        'bbox': (x1, y1, x2, y2),
                        'x_center': x_center,
                        'y_center': y_center,
                        'class_name': detection['class_name'],
                        'confidence': detection['confidence'],
                        'last_seen': 0
                    }
                    current_ids.append(self.next_id)
                    self.next_id += 1
            except Exception as e:
                print(f"更新物體追蹤時發生錯誤: {str(e)}")
        
        # 更新未檢測到的物體
        for obj_id in list(self.tracked_objects.keys()):
            if obj_id not in current_ids:
                self.tracked_objects[obj_id]['last_seen'] += 1
                # 如果物體超過一定幀數未被檢測到，則移除
                if self.tracked_objects[obj_id]['last_seen'] > 10:  # 可調整
                    del self.tracked_objects[obj_id]
        
        return self.tracked_objects