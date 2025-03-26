import cv2
import numpy as np
import os
import json

class TemplateMonsterDetector:
    def __init__(self, templates_dir="monster_templates"):
        self.templates_dir = templates_dir
        self.templates = []
        self.template_info = {}
        
        # 確保模板目錄存在
        os.makedirs(templates_dir, exist_ok=True)
        
        # 載入現有模板
        self.load_templates()
    
    def add_template(self, template_path=None, template_img=None, name=None):
        """添加模板，可以是圖片路徑或直接提供圖像數據"""
        if template_path and os.path.exists(template_path):
            template = cv2.imread(template_path)
            template_name = name or os.path.basename(template_path).split('.')[0]
        elif template_img is not None:
            template = template_img
            template_name = name or f"template_{len(self.templates)}"
        else:
            print("需要提供有效的模板路徑或圖像數據")
            return False
        
        # 儲存模板圖像
        if not template_path:
            template_path = os.path.join(self.templates_dir, f"{template_name}.png")
            cv2.imwrite(template_path, template)
        
        # 將模板添加到列表
        template_info = {
            "name": template_name,
            "path": template_path,
            "width": template.shape[1],
            "height": template.shape[0]
        }
        
        self.templates.append(template)
        self.template_info[len(self.templates)-1] = template_info
        
        # 更新模板信息文件
        self._save_template_info()
        
        print(f"已添加模板: {template_name}")
        return True
    
    def detect(self, image, threshold=0.7):
        """在圖像中檢測所有模板"""
        detections = []
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 原始圖像檢測
        for idx, template in enumerate(self.templates):
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) > 2 else template
            result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            for pt in zip(*locations[::-1]):
                info = self.template_info[str(idx)]
                w, h = info["width"], info["height"]
                detections.append({
                    "class": "monster",
                    "name": info["name"],
                    "confidence": float(result[pt[1], pt[0]]),
                    "box": [pt[0], pt[1], pt[0] + w, pt[1] + h],
                    "x_center": pt[0] + w/2,
                    "y_center": pt[1] + h/2,
                    "width": w,
                    "height": h
                })
        
        # 水平翻轉圖像檢測
        flipped_image = cv2.flip(image, 1)
        flipped_gray = cv2.cvtColor(flipped_image, cv2.COLOR_BGR2GRAY)
        for idx, template in enumerate(self.templates):
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) > 2 else template
            result = cv2.matchTemplate(flipped_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= threshold)
            for pt in zip(*locations[::-1]):
                info = self.template_info[str(idx)]
                w, h = info["width"], info["height"]
                x = image.shape[1] - pt[0] - w  # 調整x坐標
                detections.append({
                    "class": "monster",
                    "name": info["name"],
                    "confidence": float(result[pt[1], pt[0]]),
                    "box": [x, pt[1], x + w, pt[1] + h],
                    "x_center": x + w/2,
                    "y_center": pt[1] + h/2,
                    "width": w,
                    "height": h
                })
        self.last_detections = detections
        # 在返回結果前應用非極大值抑制
        detections = self.non_max_suppression(detections)
        return detections

    
    def load_templates(self):
        """載入所有保存的模板"""
        info_file = os.path.join(self.templates_dir, "templates_info.json")
        
        # 載入模板信息
        if os.path.exists(info_file):
            with open(info_file, 'r') as f:
                self.template_info = json.load(f)
        else:
        # 如果JSON檔案不存在，創建一個空的並保存
            self.template_info = {}
            self._save_template_info()

        # 載入模板圖像
        self.templates = []
        for idx in sorted([int(k) for k in self.template_info.keys()]):
            idx_str = str(idx)
            if idx_str in self.template_info:
                path = self.template_info[idx_str]["path"]
                if os.path.exists(path):
                    template = cv2.imread(path)
                    self.templates.append(template)
                else:
                    print(f"警告: 模板文件不存在 {path}")
    
    def clear_templates(self):
        """清除所有模板"""
        self.templates = []
        self.template_info = {}
        self._save_template_info()
        print("已清除所有模板")


    def _save_template_info(self):
        """保存模板信息到JSON文件"""
        # 重新整理索引
        new_template_info = {}
        for i, idx in enumerate(sorted([int(k) for k in self.template_info.keys()])):
            new_template_info[str(i)] = self.template_info[str(idx)]
    
        self.template_info = new_template_info
    
        info_file = os.path.join(self.templates_dir, "templates_info.json")
        with open(info_file, 'w') as f:
            json.dump(self.template_info, f, indent=2)
        
    def add_template(self, template_path=None, template_img=None, name=None):
        """添加模板，可以是圖片路徑或直接提供圖像數據"""
        if template_path and os.path.exists(template_path):
            template = cv2.imread(template_path)
            template_name = name or os.path.basename(template_path).split('.')[0]
        elif template_img is not None:
            template = template_img
            template_name = name or f"template_{len(self.templates)}"
        else:
            print("需要提供有效的模板路徑或圖像數據")
            return False
    
        # 儲存模板圖像
        if not template_path:
            template_path = os.path.join(self.templates_dir, f"{template_name}.png")
            cv2.imwrite(template_path, template)
    
        # 將模板添加到列表
        template_info = {
            "name": template_name,
            "path": template_path,
            "width": template.shape[1],
            "height": template.shape[0]
        }
    
        self.templates.append(template)
        new_idx = str(len(self.template_info))  # 使用新的索引
        self.template_info[new_idx] = template_info
    
        # 更新模板信息文件
        self._save_template_info()
    
        print(f"已添加模板: {template_name}")
        return True      

    def non_max_suppression(self, detections, overlap_thresh=0.3):
        """應用非極大值抑制來減少重複檢測"""
        if len(detections) == 0:
            return []
    
        # 轉換為numpy數組以便處理
        boxes = np.array([d["box"] for d in detections])
        scores = np.array([d["confidence"] for d in detections])
    
        # 計算每個框的面積
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
    
        # 按照置信度排序
        idxs = np.argsort(scores)
    
        # 保留的檢測結果
        pick = []
    
        while len(idxs) > 0:
            # 取最高置信度的框
            last = len(idxs) - 1
            i = idxs[last]
            pick.append(i)
        
            # 找出與當前框重疊的所有框
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            yy2 = np.minimum(y2[i], y2[idxs[:last]])
        
            # 計算重疊區域的寬高
            w = np.maximum(0, xx2 - xx1 + 1)
            h = np.maximum(0, yy2 - yy1 + 1)
        
            # 計算重疊比例
            overlap = (w * h) / area[idxs[:last]]
        
            # 刪除重疊比例大於閾值的框
            idxs = np.delete(idxs, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
    
        # 返回保留的檢測結果
        return [detections[i] for i in pick]  