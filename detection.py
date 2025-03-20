import os
import cv2
import numpy as np
from ultralytics import YOLO

class YOLODetector:
    def __init__(self, model_path=None, confidence_threshold=0.25):
        """初始化YOLO檢測器"""
        if model_path is None or not os.path.exists(model_path):
            raise ValueError(f"模型路徑無效: {model_path}")
        
        # 安全載入模型
        self.model = self._safe_load_model(model_path)
        self.confidence_threshold = confidence_threshold
        print(f"成功載入模型: {model_path}")
        
        # 定義類別映射
        self.class_mapping = {
            0: "minimap_player",
            1: "climbable_object",
            2: "game_portal",
            3: "minimap_portal",
        }
    
    def _safe_load_model(self, model_path):
        """安全載入模型"""
        try:
            # 使用YOLO類載入模型
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                model = YOLO(model_path, task='detect')
            return model
        except Exception as e:
            raise Exception(f"載入模型失敗: {e}")
        
    def detect(self, image):
        """
        執行物體檢測
    
        參數:
            image: 輸入圖像(numpy數組)
        
        返回:
            檢測結果列表，每個結果包含位置、類別和置信度信息
        """
        if image is None or not isinstance(image, np.ndarray):
            print("無效的圖像輸入")
            return []
    
        try:
            # 使用YOLO模型進行預測
            results = self.model(image)
        
            # 解析結果
            detections = []
        
            for result in results:
                # 處理檢測框
                boxes = result.boxes
                for box in boxes:
                    # 獲取邊界框座標
                    xyxy = box.xyxy.cpu().numpy()[0]  # 轉換為numpy數組
                    x1, y1, x2, y2 = xyxy
                
                    # 計算中心點和寬高
                    x_center = (x1 + x2) / 2
                    y_center = (y1 + y2) / 2
                    width = x2 - x1
                    height = y2 - y1
                
                    # 獲取置信度和類別
                    confidence = float(box.conf.cpu().numpy()[0])
                    class_id = int(box.cls.cpu().numpy()[0])
                
                    # 只保留高於閾值的結果
                    if confidence >= self.confidence_threshold:
                        class_name = self.class_mapping.get(class_id, f"class_{class_id}")
                    
                        detections.append({
                            "box": (x1, y1, x2, y2),
                            "x_center": x_center,
                            "y_center": y_center,
                            "width": width,
                            "height": height,
                            "confidence": confidence,
                            "class": class_name,
                            "class_id": class_id
                        })
        
            return detections
        
        except Exception as e:
            print(f"檢測過程出錯: {e}")
            return []
    
