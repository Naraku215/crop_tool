"""
crop_tool - 共享工具函数

提取各脚本重复的逻辑，统一管理。
"""

import os
import re
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pillow_heif import register_heif_opener

# 注册 HEIF 格式支持
register_heif_opener()

import config


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


def scan_images(folder):
    """
    扫描文件夹中的所有图片文件（递归子文件夹）。
    返回 [{path, name, subfolder}, ...]
    subfolder 为相对输入目录的路径（如 "张三" 或 "."）
    图片按 get_sort_key 排序。
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        return []

    results = []
    for root, dirs, files in os.walk(folder_path):
        img_files = [
            f for f in files
            if Path(f).suffix.lower() in config.IMAGE_EXTS
        ]
        img_files_full = [os.path.join(root, f) for f in img_files]
        img_files_full.sort(key=get_sort_key)

        rel_path = os.path.relpath(root, folder_path)
        for f in img_files_full:
            results.append({
                'path': f,
                'name': Path(f).name,
                'subfolder': rel_path,
            })

    return results


def scan_speaker_dirs(input_dir):
    """
    扫描输入目录下的所有子文件夹，返回每个子文件夹的图片列表。
    返回格式：[(speaker_name, [img_path1, img_path2, ...]), ...]
    图片按 get_sort_key 排序。
    如果没有子文件夹，则将根目录视为一个整体返回。
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        return []

    # 检查是否有子文件夹
    subdirs = sorted(
        [d for d in input_path.iterdir() if d.is_dir()],
        key=lambda x: x.name
    )

    if not subdirs:
        # 没有子文件夹，直接处理根目录
        images = [
            f for f in input_path.iterdir()
            if f.is_file() and f.suffix.lower() in config.IMAGE_EXTS
        ]
        if images:
            images.sort(key=get_sort_key)
            return [(input_path.name, images)]
        return []

    result = []
    for speaker_dir in subdirs:
        images = [
            f for f in speaker_dir.iterdir()
            if f.is_file() and f.suffix.lower() in config.IMAGE_EXTS
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


def read_image_pil(path):
    """
    用 PIL 读取任意格式图片（含 HEIC），返回 PIL Image (RGB)。
    """
    return Image.open(str(path)).convert("RGB")


def pil_to_cv2(pil_img):
    """
    PIL Image (RGB) -> cv2 BGR numpy array
    """
    arr = np.array(pil_img)
    return arr[:, :, ::-1].copy()


def cv2_to_pil(cv2_img):
    """
    cv2 BGR numpy array -> PIL Image (RGB)
    """
    return Image.fromarray(cv2_img[:, :, ::-1])


def read_image_cv2(path):
    """
    用 OpenCV 读取图片，支持中文路径。
    对于 HEIC 格式，先通过 PIL 读取再转为 cv2 格式。
    """
    ext = Path(path).suffix.lower()
    if ext in config.HEIC_EXTS:
        pil_img = read_image_pil(path)
        return pil_to_cv2(pil_img)
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def save_image_cv2(img, path):
    """
    用 OpenCV 保存图片，支持中文路径。
    """
    ext = Path(path).suffix or '.png'
    return cv2.imencode(ext, img)[1].tofile(str(path))
