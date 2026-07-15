"""
格式转换模块 - 将任意格式图片批量转换为 PNG

本模块作为裁剪/矫正流程的内部自动预处理步骤使用。
用户只需将任意格式图片放入 `源文件/` 目录，选择裁剪或矫正后，
工具会自动调用本模块完成格式转换，再进入交互操作。

支持格式：HEIC/HEIF/JPG/JPEG/BMP/TIFF → PNG
也支持直接复制已有的 PNG 文件。

可独立运行：python trans_png.py
"""

import os
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
    收集所有图片 → 按拍摄时间排序 → 转 PNG（或复制已有 PNG）到新文件夹
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

    # 收集所有图片文件（包括 PNG 和需要转换的格式）
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

    # 创建输出子文件夹
    out_dir = Path(output_folder) / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(images_with_time)
    print(f"\n  [{folder_name}]  ({total} 张图片)")

    for idx, (img_path, shoot_time) in enumerate(images_with_time, start=1):
        new_name = f"{idx:03d}_{img_path.stem}.png"
        out_path = out_dir / new_name

        # 断点续传：跳过已转换的文件
        if out_path.exists():
            print(f"  [跳过] [{idx}/{total}]  {new_name} (已存在)")
            continue

        try:
            if img_path.suffix.lower() == '.png':
                # 已是 PNG，直接复制
                import shutil
                shutil.copy2(str(img_path), str(out_path))
            else:
                # 其他格式，用 Pillow 转换为 PNG
                img = Image.open(str(img_path))
                img.save(str(out_path), "PNG")
            stats["converted"] += 1
            print(f"  [完成] [{idx}/{total}]  {img_path.name}  ->  {new_name}")
        except Exception as e:
            stats["failed"] += 1
            stats["failed_files"].append(img_path.name)
            print(f"  [失败] [{idx}/{total}]  {img_path.name}  错误: {e}")

    return stats


def generate_report(all_stats, output_dir):
    """生成汇总报告并保存为 txt"""
    lines = []
    lines.append("=" * 65)
    lines.append("          图片批量转 PNG 转换报告")
    lines.append(f"          生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 65)

    total_images = sum(s["image_count"] for s in all_stats)
    total_converted = sum(s["converted"] for s in all_stats)
    total_failed = sum(s["failed"] for s in all_stats)
    total_folders = len(all_stats)
    skipped_folders = sum(1 for s in all_stats if s["image_count"] == 0)

    lines.append("")
    lines.append("[总览]")
    lines.append(f"  文件夹总数:        {total_folders}")
    lines.append(f"  有效文件夹:        {total_folders - skipped_folders}")
    lines.append(f"  跳过(无图片):      {skipped_folders}")
    lines.append(f"  图片总数:          {total_images}")
    lines.append(f"  成功转换:          {total_converted}")
    lines.append(f"  失败:              {total_failed}")
    lines.append(f"  输出目录:          {output_dir}")
    lines.append("")
    lines.append("-" * 65)

    for s in all_stats:
        lines.append("")
        lines.append(f"  {s['folder_name']}")
        lines.append(f"    文件夹内文件总数:   {s['total_files']}")
        lines.append(f"    图片文件数:         {s['image_count']}")
        lines.append(f"    成功转换:           {s['converted']}")
        lines.append(f"    失败:               {s['failed']}")
        if s["time_range"]:
            lines.append(f"    拍摄时间范围:       {s['time_range']}")
        if s["failed_files"]:
            lines.append(f"    失败文件:")
            for fname in s["failed_files"]:
                lines.append(f"      - {fname}")
        if s["image_count"] == 0:
            lines.append(f"    状态:  跳过 (无图片文件)")
        elif s["failed"] == 0:
            lines.append(f"    状态:  全部成功")
        else:
            lines.append(f"    状态:  部分失败")
        lines.append("    " + "-" * 40)

    lines.append("")
    lines.append("=" * 65)
    lines.append("  报告结束")
    lines.append("=" * 65)

    report_text = "\n".join(lines)

    report_path = Path(config.CONVERT_REPORT)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n" + report_text)
    print(f"\n  报告已保存到: {report_path}")


def convert_to_png(input_dir=None, output_dir=None):
    """
    批量将图片转换为 PNG 格式。

    参数:
        input_dir: 输入目录（默认 config.SOURCE_DIR）
        output_dir: 输出目录（默认 config.PNG_DIR）

    返回:
        bool: 是否有文件被处理（True 表示成功或已有数据，False 表示无图片）
    """
    if input_dir is None:
        input_dir = config.SOURCE_DIR
    if output_dir is None:
        output_dir = config.PNG_DIR

    root = Path(input_dir)
    if not root.exists():
        print(f"  [错误] 源文件路径不存在: {input_dir}")
        return False

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    subfolders = sorted([f for f in root.iterdir() if f.is_dir()])
    all_stats = []

    if not subfolders:
        # 没有子文件夹，直接处理根目录
        stats = convert_folder(root, output_dir)
        all_stats.append(stats)
    else:
        print(f"  共发现 {len(subfolders)} 个文件夹")
        for folder in subfolders:
            stats = convert_folder(str(folder), output_dir)
            all_stats.append(stats)

    generate_report(all_stats, output_dir)
    print("\n  [完成] 格式转换完毕！")
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("  图片格式转换工具 (任意格式 -> PNG)")
    print("=" * 50)
    print(f"  输入目录: {config.SOURCE_DIR}")
    print(f"  输出目录: {config.PNG_DIR}")
    print("=" * 50)
    convert_to_png()
