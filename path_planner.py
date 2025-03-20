import math

class PathPlanner:
    def __init__(self, quad_tree):
        self.quad_tree = quad_tree

    def find_path(self, start, goal):
        """使用 A* 演算法尋找從起點到目標的最短路徑"""
        open_set = [start]
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}

        while open_set:
            # 找到 f_score 最小的節點
            current = min(open_set, key=lambda x: f_score.get(x, float('inf')))
            if current == goal:
                return self.reconstruct_path(came_from, current)

            open_set.remove(current)
            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + self.distance(current, neighbor)
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + self.heuristic(neighbor, goal)
                    if neighbor not in open_set:
                        open_set.append(neighbor)

        return []

    def heuristic(self, a, b):
        """計算啟發函數（曼哈頓距離）"""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def distance(self, a, b):
        """計算兩點之間的歐幾里得距離"""
        return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)

    def get_neighbors(self, node):
        """獲取當前節點的鄰居節點"""
        x, y = node
        step_size = 50  # 每次移動的步長
        neighbors = [
            (x + step_size, y),
            (x - step_size, y),
            (x, y + step_size),
            (x, y - step_size)
        ]
        # 過濾掉被障礙物阻擋的節點
        return [n for n in neighbors if not self._is_obstacle(n)]

    def _is_obstacle(self, point):
        """判斷某點是否為障礙物"""
        x, y = point
        obstacles = self.quad_tree.query_region(x - 20, y - 20, x + 20, y + 20)
        return any(obj["type"] == "obstacle" for obj in obstacles)

    def reconstruct_path(self, came_from, current):
        """重建從起點到目標的路徑"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def smooth_path(self, path):
        """使用視線法簡化路徑點"""
        if len(path) < 3:
            return path

        result = [path[0]]
        current_index = 0

        while current_index < len(path) - 1:
            for i in range(len(path) - 1, current_index, -1):
                if self.has_clear_line(path[current_index], path[i]):
                    result.append(path[i])
                    current_index = i
                    break
            else:
                current_index += 1
                result.append(path[current_index])

        return result

    def has_clear_line(self, start, end):
        """檢查兩點之間是否有清晰的直線視線"""
        x1, y1 = start
        x2, y2 = end
        steps = max(abs(x2 - x1), abs(y2 - y1))
        
        for i in range(steps):
            t = i / steps
            x = int(x1 + t * (x2 - x1))
            y = int(y1 + t * (y2 - y1))
            if self._is_obstacle((x, y)):
                return False
                
        return True
