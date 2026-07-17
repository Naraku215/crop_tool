"""
crop_tool - 文件夹对账检查工具

对比原始输入目录与处理后目录的图片数量和顺序，
检测是否有遗漏、跳过或顺序错乱的情况。

可独立运行：python check_folders.py <input_dir> <processed_dir>
"""

import os
import re
import sys
from pathlib import Path

import config


def get_original_stem_from_png(png_filename):
    """
    从转换后的文件名(如 001_IMG_1234.png) 中提取出原始的名字 (IMG_1234)
    """
    match = re.match(r'^\d{3}_(.+)\.png$', png_filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return Path(png_filename).stem


def check_folders(input_dir, processed_dir):
    """
    对比输入目录和处理后目录，检查数量和顺序是否一致

    参数:
        input_dir: 原始图片目录
        processed_dir: 处理后图片目录
    """
    orig_path = Path(input_dir)
    crop_path = Path(processed_dir)

    if not orig_path.exists() or not crop_path.exists():
        print("  [错误] 路径不存在，请检查输入目录和处理后目录！")
        return

    total_folders = 0
    perfect_folders = 0
    warning_folders = 0
    error_folders = 0
    total_orig_images = 0
    total_crop_images = 0

    for root, dirs, files in os.walk(orig_path):
        image_files = [
            file for file in files
            if file.lower().endswith(('.heic', '.heif', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'))
        ]

        if not image_files:
            continue

        total_folders += 1
        rel_path = os.path.relpath(root, orig_path)
        current_crop_dir = crop_path / rel_path

        print(f"\n  检查文件夹: [{rel_path}]")

        img_full_paths = [os.path.join(root, file) for file in image_files]
        img_full_paths.sort(key=lambda x: os.path.getmtime(x))
        orig_sequence = [Path(file).stem.lower() for file in img_full_paths]
        orig_count = len(orig_sequence)
        total_orig_images += orig_count

        if not current_crop_dir.exists():
            print(f"   [错误] 找不到对应的处理后文件夹！")
            error_folders += 1
            continue

        png_files = [file for file in os.listdir(current_crop_dir) if file.lower().endswith('.png')]
        png_files.sort()
        crop_sequence = [get_original_stem_from_png(file).lower() for file in png_files]
        crop_count = len(crop_sequence)
        total_crop_images += crop_count

        print(f"   -> 源文件数: {orig_count} 张 | 处理后数: {crop_count} 张")

        if orig_count == crop_count:
            if orig_sequence == crop_sequence:
                print("   [完美] 数量完全一致，且顺序 100% 对应。")
                perfect_folders += 1
            else:
                print("   [错误] 数量虽然一致，但顺序不匹配。")
                error_folders += 1
        else:
            print(f"   [警告] 数量不一致 (处理图少了 {orig_count - crop_count} 张)。")
            warning_folders += 1

    # 最终报告
    print("\n" + "=" * 50)
    print("  最终对账总结报告")
    print("-" * 50)
    print(f"   总计检查文件夹: {total_folders} 个")
    print(f"   完美对应: {perfect_folders} 个")
    print(f"   包含跳过项: {warning_folders} 个")
    print(f"   异常文件夹: {error_folders} 个")
    print("-" * 50)
    print(f"   原始照片总数: {total_orig_images} 张")
    print(f"   处理后总数: {total_crop_images} 张")
    print(f"   剔除/跳过: {total_orig_images - total_crop_images} 张")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        input_dir = sys.argv[1]
        processed_dir = sys.argv[2]
    else:
        print("用法: python check_folders.py <input_dir> <processed_dir>")
        sys.exit(1)

    print("=" * 50)
    print("  文件夹对账检查工具")
    print("=" * 50)
    check_folders(input_dir, processed_dir)
