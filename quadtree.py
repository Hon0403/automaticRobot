class Point:
    """表示二維空間中的一個點"""
    def __init__(self, x, y, data=None):
        self.x = x
        self.y = y
        self.data = data  # 可選的附加數據

class QuadTreeNode:
    """四叉樹節點實現"""
    def __init__(self, boundary, capacity=4, max_level=10, level=0):
        self.boundary = boundary
        self.capacity = capacity
        self.points = []
        self.divided = False
        self.level = level
        self.max_level = max_level
        self.top_left_node = None  # northwest
        self.top_right_node = None  # northeast
        self.bottom_left_node = None  # southwest
        self.bottom_right_node = None  # southeast
        
    def insert(self, point):
        """將點插入到四叉樹節點"""
        if not self.boundary.contains(point):
            return False
            
        if len(self.points) < self.capacity and not self.divided:
            self.points.append(point)
            return True
            
        if not self.divided:
            self.subdivide()
            
        if self.top_left_node.insert(point) or \
           self.top_right_node.insert(point) or \
           self.bottom_left_node.insert(point) or \
           self.bottom_right_node.insert(point):
            return True
        
        return False
        
    def subdivide(self):
        """將節點分為四個子節點"""
        x = self.boundary.x
        y = self.boundary.y
        w = self.boundary.width / 2
        h = self.boundary.height / 2
        
        nw = Rectangle(x - w/2, y - h/2, w, h)
        ne = Rectangle(x + w/2, y - h/2, w, h)
        sw = Rectangle(x - w/2, y + h/2, w, h)
        se = Rectangle(x + w/2, y + h/2, w, h)
        
        self.top_left_node = QuadTreeNode(nw, self.capacity, self.max_level, self.level + 1)
        self.top_right_node = QuadTreeNode(ne, self.capacity, self.max_level, self.level + 1)
        self.bottom_left_node = QuadTreeNode(sw, self.capacity, self.max_level, self.level + 1)
        self.bottom_right_node = QuadTreeNode(se, self.capacity, self.max_level, self.level + 1)
        
        self.divided = True
        
    def query_range(self, range_rect):
        """查詢指定範圍內的所有點"""
        found = []
        
        if not self.boundary.intersects(range_rect):
            return found
            
        for point in self.points:
            if range_rect.contains(point):
                found.append(point)
                
        if self.divided:
            found.extend(self.top_left_node.query_range(range_rect))
            found.extend(self.top_right_node.query_range(range_rect))
            found.extend(self.bottom_left_node.query_range(range_rect))
            found.extend(self.bottom_right_node.query_range(range_rect))
            
        return found
        
    def clear(self):
        """清空四叉樹"""
        self.points = []
        self.divided = False
        self.top_left_node = None
        self.top_right_node = None
        self.bottom_left_node = None
        self.bottom_right_node = None


class Rectangle:
    """表示二維空間中的矩形邊界"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def contains(self, point):
        """判斷某點是否在矩形內"""
        return (self.x - self.width / 2 <= point.x <= self.x + self.width / 2 and
                self.y - self.height / 2 <= point.y <= self.y + self.height / 2)

    def intersects(self, range_rect):
        """判斷矩形是否與另一個矩形相交"""
        return not (range_rect.x - range_rect.width / 2 > self.x + self.width / 2 or
                    range_rect.x + range_rect.width / 2 < self.x - self.width / 2 or
                    range_rect.y - range_rect.height / 2 > self.y + self.height / 2 or
                    range_rect.y + range_rect.height / 2 < self.y - self.height / 2)

class QuadTree:
    """四叉樹實現，用於管理二維空間中的點"""
    def __init__(self, boundary, capacity):
        """
        初始化四叉樹節點
        :param boundary: Rectangle 類型，表示此節點的邊界
        :param capacity: int，節點中能容納的最大點數量
        """
        self.boundary = boundary
        self.capacity = capacity
        self.points = []  # 此節點中的點列表
        self.divided = False  # 是否已分割為子區域

    def subdivide(self):
        """將當前節點分為四個子區域"""
        x = self.boundary.x
        y = self.boundary.y
        w = self.boundary.width / 2
        h = self.boundary.height / 2

        nw = Rectangle(x - w / 2, y - h / 2, w, h)
        ne = Rectangle(x + w / 2, y - h / 2, w, h)
        sw = Rectangle(x - w / 2, y + h / 2, w, h)
        se = Rectangle(x + w / 2, y + h / 2, w, h)

        # 創建四個子四叉樹節點
        self.northwest = QuadTree(nw, self.capacity)
        self.northeast = QuadTree(ne, self.capacity)
        self.southwest = QuadTree(sw, self.capacity)
        self.southeast = QuadTree(se, self.capacity)

        # 標記為已分割
        self.divided = True

    def insert(self, point):
        """
        將一個點插入到四叉樹中
        :param point: Point 類型，要插入的點
        :return: bool，插入成功返回 True，否則返回 False
        """
        if not self.boundary.contains(point):
            return False

        if len(self.points) < self.capacity:
            # 如果當前節點未滿，直接添加到此節點中
            self.points.append(point)
            return True

        if not self.divided:
            # 如果已滿且未分割，則進行分割
            self.subdivide()

        # 嘗試將點插入到子區域中
        if (self.northwest.insert(point) or 
            self.northeast.insert(point) or 
            self.southwest.insert(point) or 
            self.southeast.insert(point)):
            return True

    def query(self, range_rect, found=None):
        """
        查詢指定範圍內的所有點
        :param range_rect: Rectangle 類型，指定查詢範圍
        :param found: list，用於存儲查詢結果（默認為空列表）
        :return: list，範圍內的所有點列表
        """
        if found is None:
            found = []

        if not self.boundary.intersects(range_rect):
            # 如果查詢範圍與當前節點無交集，直接返回空結果
            return found

        for point in self.points:
            if range_rect.contains(point):
                found.append(point)

        if self.divided:
            # 遞歸查詢子區域
            self.northwest.query(range_rect, found)
            self.northeast.query(range_rect, found)
            self.southwest.query(range_rect, found)
            self.southeast.query(range_rect, found)

        return found

# 測試代碼示例：
if __name__ == "__main__":
    # 定義空間邊界和四叉樹容量
    boundary = Rectangle(0, 0, 200, 200)
    qt = QuadTree(boundary, capacity=4)

    # 插入一些測試點
    points = [Point(50, 50), Point(-50, -50), Point(100, 100), Point(-100, -100)]
    for p in points:
        qt.insert(p)

    # 查詢某個範圍內的所有點
    query_range = Rectangle(0, 0, 100, 100)
    found_points = qt.query(query_range)

    print(f"Found {len(found_points)} points in the query range.")
    for p in found_points:
        print(f"Point({p.x}, {p.y})")
