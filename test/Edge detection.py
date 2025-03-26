import cv2
import numpy as np

def detect_platform_edges(gray, lower_threshold, upper_threshold):
    """檢測平台邊緣"""
    # 使用高斯模糊降噪
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 使用 Canny 邊緣檢測
    edges = cv2.Canny(blurred, lower_threshold, upper_threshold)

    # 形態學處理：關閉小間隙，連接橫向邊緣
    horizontal_kernel = np.ones((1, 15), np.uint8)
    horizontal_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, horizontal_kernel)

    # 檢測輪廓
    contours, _ = cv2.findContours(horizontal_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 過濾平台輪廓
    platform_edges = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w > h * 3 and cv2.contourArea(contour) > 100:  # 寬度顯著大於高度
            platform_edges.append((x, y, x + w, y + h))

    return platform_edges

def detect_platform_gaps(platform_edges):
    """檢測平台之間的水平和垂直間隙"""
    platform_edges = sorted(platform_edges, key=lambda edge: edge[1])  # 按 y 軸排序
    gaps = []

    for i in range(len(platform_edges) - 1):
        current = platform_edges[i]
        next = platform_edges[i + 1]

        # 水平間隙
        if current[2] < next[0]:  # 如果當前平台右邊小於下一個平台左邊
            gaps.append({
                "start": (current[2], current[1]),
                "end": (next[0], next[1]),
                "type": "horizontal",
                "size": next[0] - current[2]
            })

        # 垂直間隙
        elif abs(next[1] - current[1]) > 10:  # 平台高度差大於 10
            gaps.append({
                "start": (current[2], current[1]),
                "end": (next[0], next[1]),
                "type": "vertical",
                "size": abs(next[1] - current[1])
            })

    return gaps

def draw_results(image, platform_edges):
    """繪製檢測結果"""
    for edge in platform_edges:
        cv2.rectangle(image, (edge[0], edge[1]), (edge[2], edge[3]), (0, 255, 0), 2)  # 平台用綠色框標記
    return image

def draw_gaps(image, gaps):
    """繪製平台間隙"""
    for gap in gaps:
        color = (0, 0, 255) if gap["type"] == "horizontal" else (255, 0, 0)  # 紅色表示水平間隙，藍色表示垂直間隙
        cv2.line(image, gap["start"], gap["end"], color, 2)
    return image

def update(val):
    """滑桿更新邊緣檢測參數並展示結果"""
    lower = cv2.getTrackbarPos('Lower Threshold', 'Edge Detection')
    upper = cv2.getTrackbarPos('Upper Threshold', 'Edge Detection')
    blur_kernel = cv2.getTrackbarPos('Blur Kernel', 'Edge Detection')  # 新增模糊滑桿

    if blur_kernel % 2 == 0:  # 確保內核大小為奇數
        blur_kernel += 1

    # 平台檢測
    blurred = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)  # 動態模糊大小
    platform_edges = detect_platform_edges(blurred, lower, upper)
    
    # 檢測間隙
    gaps = detect_platform_gaps(platform_edges)

    # 繪製檢測結果
    result_image = draw_results(image.copy(), platform_edges)
    result_image = draw_gaps(result_image, gaps)
    cv2.imshow('Edge Detection', result_image)

if __name__ == "__main__":
    # 載入遊戲截圖
    image_path = "2025-03-11 154930.png"  # 修改為您的圖片路徑
    image = cv2.imread(image_path)
    if image is None:
        print("無法加載圖像，請檢查路徑！")
        exit()

    # 將圖片轉換為灰階
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 創建窗口和滑桿
    cv2.namedWindow('Edge Detection')
    cv2.createTrackbar('Lower Threshold', 'Edge Detection', 50, 255, update)
    cv2.createTrackbar('Upper Threshold', 'Edge Detection', 150, 255, update)
    cv2.createTrackbar('Blur Kernel', 'Edge Detection', 5, 30, update)

    # 初始化結果展示
    update(None)

    # 等待用戶結束
    cv2.waitKey(0)
    cv2.destroyAllWindows()
