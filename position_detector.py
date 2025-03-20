def _get_current_position(self):
    """獲取遊戲角色的當前位置"""
    # 使用物體檢測器獲取當前畫面
    screen = self.window_capture.capture()
    if screen is None:
        return None
    
    # 使用YOLODetector檢測小地圖上的玩家位置
    detections = self.detector.detect(screen)
    
    # 尋找"minimap_player"類別的檢測結果
    for detection in detections:
        if detection["class"] == "minimap_player":
            # 獲取玩家在小地圖上的中心位置
            x_center = detection["x_center"]
            y_center = detection["y_center"]
            
            # 使用坐標轉換器將小地圖坐標轉換為遊戲世界坐標
            world_pos = self.coordinate_transformer.screen_to_world((x_center, y_center))
            return world_pos
    
    # 如果未檢測到玩家，返回None
    return None
