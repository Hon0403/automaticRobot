import time
import random
import win32api
import math
from action_controller import ActionController

def auto_move_task(window_capture, detector, coordinate_transformer, quad_tree, target_positions):
    """自動移動任務循環"""
    # 創建動作控制器
    controller = ActionController(window_capture, detector, coordinate_transformer, quad_tree)
    
    # 循環訪問所有目標位置
    current_target_index = 0
    
    while True:
        # 獲取當前目標位置
        if current_target_index >= len(target_positions):
            current_target_index = 0  # 迴圈回第一個目標
        
        target_position = target_positions[current_target_index]
        print(f"移動到目標位置 {current_target_index+1}/{len(target_positions)}: {target_position}")
        
        # 更新四叉樹
        update_quad_tree(window_capture, detector, coordinate_transformer, quad_tree)
        
        # 移動到目標位置
        success = controller.move_to(target_position)
        
        if success:
            print(f"成功到達目標位置 {current_target_index+1}")
            current_target_index += 1
            
            # 在目標位置等待一段時間（例如收集資源或執行其他操作）
            time.sleep(1 + random.random() * 2)
        else:
            print(f"無法到達目標位置 {current_target_index+1}，嘗試下一個目標")
            current_target_index += 1
            time.sleep(1)
        
        # 檢查是否需要結束程序
        if check_exit_condition():
            break

def update_quad_tree(window_capture, detector, coordinate_transformer, quad_tree):
    """更新四叉樹中的障礙物信息"""
    # 捕獲當前畫面
    screen = window_capture.capture()
    if screen is None:
        return
    
    # 使用YOLO檢測障礙物
    detections = detector.detect(screen)
    
    # 清空四叉樹中的暫時物體
    quad_tree.clear_temp_objects()
    
    # 將檢測到的障礙物添加到四叉樹
    for detection in detections:
        if detection["class"] in ["wall", "obstacle", "platform"]:
            # 將屏幕座標轉換為世界座標
            world_pos = coordinate_transformer.screen_to_world(
                (detection["x_center"], detection["y_center"])
            )
            
            # 添加到四叉樹
            quad_tree.insert(
                world_pos[0], world_pos[1], 
                detection["width"], detection["height"], 
                detection["class"], 
                is_temp=True  # 標記為臨時物體，以便下次更新時清除
            )

def check_exit_condition():
    """檢查是否需要結束程序"""
    # 檢查是否按下了Esc鍵
    return win32api.GetAsyncKeyState(0x1B) & 0x8000 != 0

def load_target_positions_from_csv(csv_file):
    """從CSV文件中載入目標位置"""
    import csv
    target_positions = []
    
    try:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # 跳過標題行
            for row in reader:
                if len(row) >= 2:
                    try:
                        x = float(row[0])
                        y = float(row[1])
                        target_positions.append((x, y))
                    except ValueError:
                        print(f"無法解析座標: {row}")
    except Exception as e:
        print(f"載入CSV文件時出錯: {e}")
    
    return target_positions
