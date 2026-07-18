"""
crop_tool - 四点透视裁剪

通过鼠标点击4个点，将倾斜拍摄的图片裁剪矫正为标准尺寸。
核心算法提取为可被 GUI 调用的函数，不再管理 cv2 窗口。
"""

import cv2
import numpy as np

import config


def order_points(pts):
    """
    将4个点按 左上、右上、右下、左下 排序
    pts: np.array, shape (4, 2), dtype float32
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def apply_crop(img, points, target_size=None):
    """
    给定原图(cv2 BGR)和4个点(原图坐标)，返回透视矫正后的图片。

    参数:
        img: cv2 BGR numpy array
        points: 4个点 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] 或 np.array (4,2)
        target_size: 输出尺寸 (w, h)。默认为 None，此时按所选四边形的真实
                     边长自动计算输出宽高，保留原始比例、不拉伸；显式传入
                     时仍输出固定尺寸（向后兼容）。

    返回:
        cv2 BGR numpy array
    """
    pts = np.array(points, dtype="float32")
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    if target_size is None:
        # 按四边形真实边长计算输出尺寸，保留所选区域比例
        width_bottom = np.linalg.norm(br - bl)
        width_top = np.linalg.norm(tr - tl)
        height_right = np.linalg.norm(tr - br)
        height_left = np.linalg.norm(tl - bl)
        max_width = max(int(round(width_bottom)), int(round(width_top)), 1)
        max_height = max(int(round(height_right)), int(round(height_left)), 1)
        target_size = (max_width, max_height)

    dst = np.array([
        [0, 0],
        [target_size[0] - 1, 0],
        [target_size[0] - 1, target_size[1] - 1],
        [0, target_size[1] - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, target_size, flags=cv2.INTER_LANCZOS4)
    return warped


def snap_corner(img, x, y, radius):
    """
    磁性吸附：在以 (x, y) 为中心、边长 2*radius 的局部窗口内，寻找最
    明显的角点，把落点轻轻贴到真实角上。附近无明显角则原样返回。

    参数:
        img: cv2 BGR numpy array
        x, y: 原图坐标（可为 float）
        radius: 搜索半径（原图像素）

    返回:
        (nx, ny) 吸附后的原图坐标（float）
    """
    h, w = img.shape[:2]
    r = max(4, int(round(radius)))
    cx, cy = float(x), float(y)
    x0 = int(round(cx)) - r
    y0 = int(round(cy)) - r
    x1 = x0 + 2 * r
    y1 = y0 + 2 * r
    # 裁剪到图内
    x0 = max(0, min(x0, w - 1))
    y0 = max(0, min(y0, h - 1))
    x1 = max(x0 + 1, min(x1, w))
    y1 = max(y0 + 1, min(y1, h))
    patch = img[y0:y1, x0:x1]
    if patch.size == 0 or patch.shape[0] < 3 or patch.shape[1] < 3:
        return (cx, cy)

    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    corners = cv2.goodFeaturesToTrack(gray, maxCorners=20, qualityLevel=0.05,
                                      minDistance=5)
    if corners is None or len(corners) == 0:
        return (cx, cy)

    # 选距中心（原落点）最近的角点
    best = None
    best_d = float('inf')
    for c in corners:
        px, py = c.ravel()
        gx, gy = x0 + float(px), y0 + float(py)
        d = (gx - cx) ** 2 + (gy - cy) ** 2
        if d < best_d:
            best_d = d
            best = (gx, gy)
    if best is None:
        return (cx, cy)
    # 仅当在搜索半径内才吸附
    if best_d <= float(r) ** 2:
        return best
    return (cx, cy)


def detect_quad(img):
    """
    一键建议四角：自动检测图中最明显的四边形，返回排序后的 4 个角点。
    未检测到明显四边形时返回 None。仅作为手动调整的起点。

    返回:
        [(x,y) x4] 或 None
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    # 轻微膨胀，连接断开的边
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    img_area = img.shape[0] * img.shape[1]
    for cnt in sorted(contours, key=cv2.contourArea, reverse=True):
        area = cv2.contourArea(cnt)
        if area < img_area * 0.02:   # 过小的轮廓忽略
            break
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
            rect = order_points(pts)
            return [(float(px), float(py)) for px, py in rect]
    return None
