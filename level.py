"""
crop_tool - 水平矫正

通过在图片上找一条应该是水平的线（点左端和右端），
自动计算倾斜角度并旋转矫正，去除黑边后恢复标准尺寸。
核心算法提取为可被 GUI 调用的函数，不再管理 cv2 窗口。
"""

import math

import cv2
import numpy as np


def get_max_inscribed_rect(w, h, angle_degrees):
    """
    计算图片旋转后，为了不出现黑边，能保留的最大矩形框大小
    """
    angle_rad = abs(math.radians(angle_degrees))
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)

    new_w = w / (cos_a + (h / w) * sin_a)
    new_h = h / (cos_a + (w / h) * sin_a)
    return int(new_w), int(new_h)


def apply_level(img, point_a, point_b):
    """
    给定原图和2个点(水平线两端)，返回旋转矫正后的图片。

    参数:
        img: cv2 BGR numpy array
        point_a: (x, y) 水平线左端，原图坐标
        point_b: (x, y) 水平线右端，原图坐标

    返回:
        cv2 BGR numpy array (与原图同尺寸)
    """
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    angle = math.degrees(math.atan2(dy, dx))

    h, w = img.shape[:2]
    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LANCZOS4)

    in_w, in_h = get_max_inscribed_rect(w, h, angle)
    x_start = center[0] - in_w // 2
    y_start = center[1] - in_h // 2
    cropped = rotated[y_start:y_start + in_h, x_start:x_start + in_w]

    final_img = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)
    return final_img


def get_angle(point_a, point_b):
    """计算两点连线的倾斜角度（度）"""
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return math.degrees(math.atan2(dy, dx))
