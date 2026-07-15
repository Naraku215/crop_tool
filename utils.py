"""
图片裁剪矫正与导出工具 - 共享工具函数

提取各脚本重复的逻辑，统一管理。
"""

import os
import re
from pathlib import Path

import cv2
import numpy as np


def get_sort_key(file_path):
    """
    文件排序键：优先按文件名前缀数字排序（001_、002_...），
    无数字前缀则按文件修改时间排序。
    """
    name = Path(file_path).stem
    parts = name.split('_', 1)
    if parts[0].isdigit():
        return (0, int(parts[0]), name)
    return (1, 0, os.path.getmtime(file_path))


def scan_speaker_dirs(input_dir):
    """
    扫描输入目录下的所有子文件夹，返回每个子文件夹的图片列表。
    返回格式：[(speaker_name, [img_path1, img_path2, ...]), ...]
    图片按 get_sort_key 排序。
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        print(f"  [错误] 路径不存在: {input_dir}")
        return []

    speaker_dirs = sorted(
        [d for d in input_path.iterdir() if d.is_dir()],
        key=lambda x: x.name
    )

    result = []
    for speaker_dir in speaker_dirs:
        images = [
            f for f in speaker_dir.iterdir()
            if f.is_file() and f.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        ]
        if not images:
            continue
        images.sort(key=get_sort_key)
        result.append((speaker_dir.name, images))

    return result


def scan_all_tasks(input_dir, output_dir, ext='.png'):
    """
    递归扫描输入目录，生成线性任务清单。
    每个任务包含原图路径、文件夹名、文件名、输出路径。
    用于 crop_tool.py 和 level.py 的断点续传。
    """
    tasks = []
    input_path = Path(input_dir)

    for root, dirs, files in os.walk(input_path):
        img_files = sorted([f for f in files if f.lower().endswith(ext)])
        for file in img_files:
            rel_path = os.path.relpath(root, input_path)
            out_dir = Path(output_dir) / rel_path
            out_dir.mkdir(parents=True, exist_ok=True)
            tasks.append({
                'img_path': os.path.join(root, file),
                'folder_name': rel_path,
                'file_name': file,
                'out_file_path': out_dir / file
            })
    return tasks


def read_image_cv2(path):
    """
    用 OpenCV 读取图片，支持中文路径。
    cv2.imread 不支持中文路径，需用 np.fromfile + cv2.imdecode 替代。
    """
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def save_image_cv2(img, path):
    """
    用 OpenCV 保存图片，支持中文路径。
    cv2.imwrite 不支持中文路径，需用 cv2.imencode + tofile 替代。
    """
    ext = Path(path).suffix or '.png'
    return cv2.imencode(ext, img)[1].tofile(str(path))
