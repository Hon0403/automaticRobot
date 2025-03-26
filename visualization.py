# visualization.py
import cv2
import numpy as np

def draw_fan_shape(image, center, radius, start_angle, end_angle, color, thickness):
    """在圖像上繪製扇形"""
    # 創建蒙版
    mask = np.zeros_like(image, dtype=np.uint8)
    
    # 定義扇形的點
    points = []
    for angle in range(start_angle, end_angle + 1):
        radian = np.deg2rad(angle)
        x = int(center[0] + radius * np.cos(radian))
        y = int(center[1] + radius * np.sin(radian))
        points.append((x, y))
    
    # 添加中心點以閉合扇形
    points.append(center)
    
    # 轉換為numpy數組
    points = np.array(points, dtype=np.int32)
    
    # 在蒙版上繪製扇形
    cv2.fillPoly(mask, [points], color)
    
    # 將蒙版與原圖疊加
    alpha = 0.5  # 設置透明度
    result = cv2.addWeighted(image, 1, mask, alpha, 0)
    
    return result
