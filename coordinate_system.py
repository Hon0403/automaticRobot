class CoordinateTransformer:
    def __init__(self, minimap_rect=(1920, 1080)):
        self.minimap_x, self.minimap_y, self.map_w, self.map_h = minimap_rect
        self.map_scale = 0.2
        
    def screen_to_world(self, screen_pos):
        """將屏幕坐標轉換為遊戲世界坐標"""
        x_scale = 1.0  # 調整為合適的值
        y_scale = 1.0  # 調整為合適的值
        world_x = screen_pos[0] * x_scale
        world_y = screen_pos[1] * y_scale
        return (world_x, world_y)
        
    def world_to_screen(self, world_pos):
        """將遊戲世界坐標轉換為屏幕坐標"""
        return (
            int(world_pos[0] / self.map_scale),
            int(world_pos[1] / self.map_scale)
        )
