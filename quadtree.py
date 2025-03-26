import numpy as np
import math

class Point:
    """二維空間中的點"""
    def __init__(self, x, y, data=None):
        self.x = x
        self.y = y
        self.data = data
        
    def __str__(self):
        return f"Point({self.x}, {self.y})"
        
    def distance_to(self, other):
        """計算與另一個點的距離"""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

class Rectangle:
    """二維空間中的矩形"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def contains(self, point):
        """檢查矩形是否包含點"""
        return (point.x >= self.x and 
                point.x <= self.x + self.width and
                point.y >= self.y and
                point.y <= self.y + self.height)
                
    def intersects(self, other):
        """檢查是否與另一個矩形相交"""
        return not (other.x > self.x + self.width or
                   other.x + other.width < self.x or
                   other.y > self.y + self.height or
                   other.y + other.height < self.y)
                   
    def intersects_circle(self, center, radius):
        """檢查是否與圓形相交"""
        # 計算矩形到圓心的最近點
        closest_x = max(self.x, min(center.x, self.x + self.width))
        closest_y = max(self.y, min(center.y, self.y + self.height))
        
        # 計算距離
        dx = center.x - closest_x
        dy = center.y - closest_y
        
        # 檢查距離是否小於等於半徑
        return (dx * dx + dy * dy) <= (radius * radius)
        
    def __str__(self):
        return f"Rectangle({self.x}, {self.y}, {self.width}, {self.height})"

class QuadTree:
    """四叉樹數據結構"""
    def __init__(self, boundary, capacity=4, max_depth=10, depth=0):
        if isinstance(boundary, list) or isinstance(boundary, tuple):
            # 如果提供的是列表或元組，轉換為Rectangle對象
            x, y, width, height = boundary
            self.boundary = Rectangle(x, y, width, height)
        else:
            self.boundary = boundary
            
        self.capacity = capacity  # 每個節點的最大容量
        self.points = []          # 保存點
        self.divided = False      # 是否已分裂
        self.children = []        # 子節點
        self.max_depth = max_depth  # 最大深度
        self.depth = depth        # 當前深度
        
    def insert(self, point):
        """插入點到四叉樹"""
        # 如果點不在邊界內，則不插入
        if not self.boundary.contains(point):
            return False
        
        # 如果達到最大深度，則直接添加到當前節點
        if self.depth >= self.max_depth:
            self.points.append(point)
            return True
            
        # 如果容量未滿且尚未分裂，則添加到當前節點
        if len(self.points) < self.capacity and not self.divided:
            self.points.append(point)
            return True
        
        # 如果容量已滿但尚未分裂，則進行分裂
        if not self.divided:
            self._subdivide()
            
            # 將當前節點的點重新分配到子節點
            for p in self.points:
                self._insert_to_children(p)
            self.points = []  # 清空當前節點
        
        # 嘗試將點插入到子節點
        return self._insert_to_children(point)
    
    def _insert_to_children(self, point):
        """嘗試將點插入到所有子節點"""
        for child in self.children:
            if child.insert(point):
                return True
        return False
    
    def _subdivide(self):
        """將當前節點分裂為四個子節點"""
        x = self.boundary.x
        y = self.boundary.y
        w = self.boundary.width / 2
        h = self.boundary.height / 2
        
        # 創建四個子節點
        ne = QuadTree(Rectangle(x + w, y, w, h), self.capacity, self.max_depth, self.depth + 1)
        nw = QuadTree(Rectangle(x, y, w, h), self.capacity, self.max_depth, self.depth + 1)
        se = QuadTree(Rectangle(x + w, y + h, w, h), self.capacity, self.max_depth, self.depth + 1)
        sw = QuadTree(Rectangle(x, y + h, w, h), self.capacity, self.max_depth, self.depth + 1)
        
        self.children = [ne, nw, se, sw]
        self.divided = True
    
    def query_range(self, range_rect):
        """查詢範圍內的所有點"""
        # 如果範圍矩形是列表或元組，轉換為Rectangle對象
        if isinstance(range_rect, list) or isinstance(range_rect, tuple):
            x, y, width, height = range_rect
            range_rect = Rectangle(x, y, width, height)
            
        found_points = []
        
        # 如果範圍與當前節點邊界不相交，則返回空
        if not self.boundary.intersects(range_rect):
            return found_points
        
        # 檢查當前節點的點
        for point in self.points:
            if range_rect.contains(point):
                found_points.append(point)
        
        # 如果已分裂，則遞歸查詢子節點
        if self.divided:
            for child in self.children:
                found_points.extend(child.query_range(range_rect))
        
        return found_points
    
    def query_circle(self, center, radius):
        """查詢圓形範圍內的所有點"""
        found_points = []
        
        # 如果圓形與當前節點邊界不相交，則返回空
        if not self.boundary.intersects_circle(center, radius):
            return found_points
        
        # 檢查當前節點的點
        for point in self.points:
            dx = point.x - center.x
            dy = point.y - center.y
            distance_squared = dx * dx + dy * dy
            if distance_squared <= radius * radius:
                found_points.append(point)
        
        # 如果已分裂，則遞歸查詢子節點
        if self.divided:
            for child in self.children:
                found_points.extend(child.query_circle(center, radius))
        
        return found_points
    
    def get_all_points(self):
        """獲取四叉樹中的所有點"""
        all_points = self.points.copy()
        
        if self.divided:
            for child in self.children:
                all_points.extend(child.get_all_points())
        
        return all_points
    
    def clear(self):
        """清空四叉樹"""
        self.points = []
        self.divided = False
        self.children = []
        
    def __str__(self):
        """字符串表示"""
        return f"QuadTree({self.boundary}, {len(self.points)} points, {len(self.children)} children)"
