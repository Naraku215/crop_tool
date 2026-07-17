"""
crop_tool - 格式转换模块

将任意格式图片批量转换为 PNG。
作为 CLI 工具保留，GUI 直接用 PIL 读取任意格式，不再依赖此模块。

支持格式：HEIC/HEIF/JPG/JPEG/BMP/TIFF -> PNG

可独立运行：python trans_png.py <input_dir> <output_dir>
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

from PIL import Image
from pillow_heif import register_heif_opener

import config

# 注册 HEIF 格式支持
register_heif_opener()


def get_shoot_time(filepath):
    """获取拍摄时间：优先 EXIF，兜底用文件修改时间"""
    try:
        img = Image.open(filepath)
        exif_data = img._getexif()
        if exif_data:
            for tag_id in [36867, 36868, 306]:
                if tag_id in exif_data:
                    time_str = exif_data[tag_id]
                    return datetime.strptime(time_str, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return datetime.fromtimestamp(os.path.getmtime(filepath))


def convert_folder(folder_path, output_folder):
    """
    处理单个文件夹：
    收集所有图片 -> 按拍摄时间排序 -> 转 PNG 到新文件夹
    返回该文件夹的统计信息 dict
    """
    folder_name = Path(folder_path).name

    stats = {
        "folder_name": folder_name,
        "total_files": 0,
        "image_count": 0,
        "converted": 0,
        "failed": 0,
        "failed_files": [],
        "time_range": "",
    }

    all_files = list(Path(folder_path).iterdir())
    stats["total_files"] = len([f for f in all_files if f.is_file()])

    image_files = [
        f for f in all_files
        if f.is_file() and f.suffix.lower() in config.IMAGE_EXTS
    ]
    stats["image_count"] = len(image_files)

    if not image_files:
        print(f"  [跳过] {folder_name}: 没有找到图片文件")
        return stats

    # 按拍摄时间排序
    images_with_time = []
    for f in image_files:
        t = get_shoot_time(str(f))
        images_with_time.append((f, t))
    images_with_time.sort(key=lambda x: x[1])

    earliest = images_with_time[0][1].strftime("%Y-%m-%d %H:%M:%S")
    latest = images_with_time[-1][1].strftime("%Y-%m-%d %H:%M:%S")
    stats["time_range"] = f"{earliest}  ->  {latest}"

    out_dir = Path(output_folder) / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(images_with_time)
    print(f"\n  [{folder_name}]  ({total} 张图片)")

    for idx, (img_path, shoot_time) in enumerate(images_with_time, start=1):
        new_name = f"{idx:03d}_{img_path.stem}.png"
        out_path = out_dir / new_name

        if out_path.exists():
            print(f"  [跳过] [{idx}/{total}]  {new_name} (已存在)")
            continue

        try:
            if img_path.suffix.lower() == '.png':
                shutil.copy2(str(img_path), str(out_path))
            else:
                img = Image.open(str(img_path))
                img.save(str(out_path), "PNG")
            stats["converted"] += 1
            print(f"  [完成] [{idx}/{total}]  {img_path.name}  ->  {new_name}")
        except Exception as e:
            stats["failed"] += 1
            stats["failed_files"].append(img_path.name)
            print(f"  [失败] [{idx}/{total}]  {img_path.name}  错误: {e}")

    return stats


def convert_to_png(input_dir, output_dir):
    """
    批量将图片转换为 PNG 格式。

    参数:
        input_dir: 输入目录
        output_dir: 输出目录

    返回:
        bool: 是否有文件被处理
    """
    root = Path(input_dir)
    if not root.exists():
        print(f"  [错误] 输入路径不存在: {input_dir}")
        return False

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    subfolders = sorted([f for f in root.iterdir() if f.is_dir()])

    if not subfolders:
        stats = convert_folder(root, output_dir)
    else:
        print(f"  共发现 {len(subfolders)} 个文件夹")
        for folder in subfolders:
            convert_folder(str(folder), output_dir)

    print("\n  [完成] 格式转换完毕！")
    return True


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_dir = sys.argv[1]
        output_dir = sys.argv[2]
    else:
        print("用法: python trans_png.py <input_dir> <output_dir>")
        sys.exit(1)

    print("=" * 50)
    print("  图片格式转换工具 (任意格式 -> PNG)")
    print("=" * 50)
    print(f"  输入目录: {input_dir}")
    print(f"  输出目录: {output_dir}")
    print("=" * 50)
    convert_to_png(input_dir, output_dir)
