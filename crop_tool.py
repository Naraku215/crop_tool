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
        target_size: 输出尺寸 (w, h)，默认 config.TARGET_SIZE

    返回:
        cv2 BGR numpy array (target_size)
    """
    if target_size is None:
        target_size = config.TARGET_SIZE

    pts = np.array(points, dtype="float32")
    rect = order_points(pts)
    dst = np.array([
        [0, 0],
        [target_size[0] - 1, 0],
        [target_size[0] - 1, target_size[1] - 1],
        [0, target_size[1] - 1]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(img, M, target_size, flags=cv2.INTER_LANCZOS4)
    return warped
