import cv2
import numpy as np
import random

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class Rect:
    def __init__(self, x, y, width, height):
        self.x = x        # 中心点X坐标
        self.y = y        # 中心点Y坐标
        self.width = width
        self.height = height

    def contains(self, point):
        """检查点是否在矩形内"""
        return (self.x - self.width/2 <= point.x <= self.x + self.width/2 and 
                self.y - self.height/2 <= point.y <= self.y + self.height/2)

    def intersects(self, other):
        """检查两个矩形是否相交"""
        return not (other.x - other.width/2 > self.x + self.width/2 or
                   other.x + other.width/2 < self.x - self.width/2 or
                   other.y - other.height/2 > self.y + self.height/2 or
                   other.y + other.height/2 < self.y - self.height/2)

class QuadTree:
    def __init__(self, boundary, capacity=4, max_level=5, level=1):
        self.boundary = boundary    # 节点边界
        self.capacity = capacity    # 节点最大容量
        self.max_level = max_level  # 最大分割层级
        self.level = level          # 当前层级
        self.points = []            # 存储的点
        self.divided = False        # 是否已分割
        self.children = []          # 四个子节点

    def subdivide(self):
        """将当前节点分割为四个子节点"""
        x = self.boundary.x
        y = self.boundary.y
        w = self.boundary.width / 2
        h = self.boundary.height / 2

        # 创建四个子区域
        ne = Rect(x + w/2, y - h/2, w, h)  # 东北
        nw = Rect(x - w/2, y - h/2, w, h)  # 西北
        se = Rect(x + w/2, y + h/2, w, h)  # 东南
        sw = Rect(x - w/2, y + h/2, w, h)  # 西南

        self.children = [
            QuadTree(ne, self.capacity, self.max_level, self.level + 1),
            QuadTree(nw, self.capacity, self.max_level, self.level + 1),
            QuadTree(se, self.capacity, self.max_level, self.level + 1),
            QuadTree(sw, self.capacity, self.max_level, self.level + 1)
        ]
        self.divided = True

    def insert(self, point):
        """插入点到四叉树"""
        if not self.boundary.contains(point):
            return False

        if len(self.points) < self.capacity or self.level >= self.max_level:
            self.points.append(point)
            return True

        if not self.divided:
            self.subdivide()

        for child in self.children:
            if child.insert(point):
                return True
        
        self.points.append(point)
        return True

    def query_range(self, range_rect):
        """查询指定区域内的所有点"""
        found = []
        if not self.boundary.intersects(range_rect):
            return found

        for p in self.points:
            if range_rect.contains(p):
                found.append(p)

        if self.divided:
            for child in self.children:
                found.extend(child.query_range(range_rect))

        return found

    def draw(self, image):
        """可视化四叉树结构"""
        # 绘制当前节点边界
        x = int(self.boundary.x - self.boundary.width/2)
        y = int(self.boundary.y - self.boundary.height/2)
        w = int(self.boundary.width)
        h = int(self.boundary.height)
        cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 1)

        # 绘制点
        for p in self.points:
            cv2.circle(image, (int(p.x), int(p.y)), 3, (0, 0, 255), -1)

        # 递归绘制子节点
        if self.divided:
            for child in self.children:
                child.draw(image)

# 可视化测试程序 ---------------------------------------------------
class QuadTreeVisualizer:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.qt = QuadTree(Rect(width/2, height/2, width, height))
        self.query_rect = None
        self.img = np.zeros((height, width, 3), dtype=np.uint8)

    def update_display(self):
        self.img.fill(0)
        self.qt.draw(self.img)
        
        # 绘制查询范围
        if self.query_rect:
            x = int(self.query_rect.x - self.query_rect.width/2)
            y = int(self.query_rect.y - self.query_rect.height/2)
            w = int(self.query_rect.width)
            h = int(self.query_rect.height)
            cv2.rectangle(self.img, (x, y), (x+w, y+h), (255, 0, 0), 2)
            
            # 显示查询结果
            results = self.qt.query_range(self.query_rect)
            for p in results:
                cv2.circle(self.img, (int(p.x), int(p.y)), 5, (255, 255, 0), -1)

        cv2.imshow("QuadTree Demo", self.img)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # 插入随机点
            for _ in range(10):
                px = x + random.randint(-20, 20)
                py = y + random.randint(-20, 20)
                if 0 <= px < self.width and 0 <= py < self.height:
                    self.qt.insert(Point(px, py))
            self.update_display()

        elif event == cv2.EVENT_RBUTTONDOWN:
            # 设置查询范围
            self.query_rect = Rect(x, y, 100, 80)
            self.update_display()

    def run(self):
        cv2.namedWindow("QuadTree Demo")
        cv2.setMouseCallback("QuadTree Demo", self.mouse_callback)
        self.update_display()
        
        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.qt = QuadTree(Rect(self.width/2, self.height/2, self.width, self.height))
                self.query_rect = None
                self.update_display()

        cv2.destroyAllWindows()

# 运行测试程序
if __name__ == "__main__":
    visualizer = QuadTreeVisualizer()
    visualizer.run()
