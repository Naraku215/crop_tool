"""
文件夹对账检查工具

对比原始源文件目录与裁剪后目录的图片数量和顺序，
检测是否有遗漏、跳过或顺序错乱的情况，生成检查报告。

可独立运行：python check_folders.py
"""

import os
import re
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


def check_folders():
    """对比源文件和裁剪后的文件夹，检查数量和顺序是否一致"""
    orig_path = Path(config.SOURCE_DIR)
    crop_path = Path(config.CROPPED_DIR)

    def log(msg="", file_obj=None):
        print(msg)
        if file_obj:
            file_obj.write(msg + '\n')

    if not orig_path.exists() or not crop_path.exists():
        print("  [错误] 路径不存在，请检查 config.py 中的 SOURCE_DIR 和 CROPPED_DIR 配置！")
        return

    report_file = Path(config.CHECK_REPORT)
    report_file.parent.mkdir(parents=True, exist_ok=True)

    with open(report_file, 'w', encoding='utf-8') as f:
        log("=" * 50, f)
        log("  开始进行文件夹图片对账与顺序检查...", f)
        log("=" * 50, f)

        total_folders = 0
        perfect_folders = 0
        warning_folders = 0
        error_folders = 0

        total_orig_images = 0
        total_crop_images = 0

        for root, dirs, files in os.walk(orig_path):
            # 收集所有图片文件（不仅限于 HEIC）
            image_files = [
                file for file in files
                if file.lower().endswith(('.heic', '.heif', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'))
            ]

            if not image_files:
                continue

            total_folders += 1
            rel_path = os.path.relpath(root, orig_path)
            current_crop_dir = crop_path / rel_path

            log(f"\n  检查文件夹: [{rel_path}]", f)

            # 获取源文件夹数量与顺序
            img_full_paths = [os.path.join(root, file) for file in image_files]
            img_full_paths.sort(key=lambda x: os.path.getmtime(x))
            orig_sequence = [Path(file).stem.lower() for file in img_full_paths]
            orig_count = len(orig_sequence)

            total_orig_images += orig_count

            # 获取裁剪后文件夹数量与顺序
            if not current_crop_dir.exists():
                log(f"   [错误] 找不到对应的裁剪后文件夹！", f)
                error_folders += 1
                continue

            png_files = [file for file in os.listdir(current_crop_dir) if file.lower().endswith('.png')]
            png_files.sort()
            crop_sequence = [get_original_stem_from_png(file).lower() for file in png_files]
            crop_count = len(crop_sequence)

            total_crop_images += crop_count

            log(f"   -> 源文件数: {orig_count} 张 | 裁剪后数: {crop_count} 张", f)

            if orig_count == crop_count:
                if orig_sequence == crop_sequence:
                    log("   [完美] 数量完全一致，且顺序 100% 对应。", f)
                    perfect_folders += 1
                else:
                    log("   [错误] 数量虽然一致，但顺序不匹配。", f)
                    error_folders += 1
                    for i in range(orig_count):
                        if orig_sequence[i] != crop_sequence[i]:
                            log(f"      第 {i + 1} 张不匹配: 原图为 {orig_sequence[i]}, 裁剪图为 {crop_sequence[i]}", f)
                            break
            else:
                log(f"   [警告] 数量不一致 (裁剪图少了 {orig_count - crop_count} 张)。", f)
                warning_folders += 1

                is_subsequence = True
                orig_idx = 0
                for crop_name in crop_sequence:
                    while orig_idx < orig_count and orig_sequence[orig_idx] != crop_name:
                        orig_idx += 1
                    if orig_idx >= orig_count:
                        is_subsequence = False
                        break
                    orig_idx += 1

                if is_subsequence:
                    log("      -> 补充说明: 现有裁剪图的先后顺序依然正确。", f)
                else:
                    log("      [严重错误] 数量不一致，且现存图片的顺序乱了！", f)
                    error_folders += 1
                    warning_folders -= 1

        # 最终报告
        log("\n" + "=" * 50, f)
        log("  最终对账总结报告", f)
        log("-" * 50, f)
        log("  [文件夹统计]", f)
        log(f"   总计检查文件夹: {total_folders} 个", f)
        log(f"   完美对应: {perfect_folders} 个", f)
        log(f"   包含跳过项: {warning_folders} 个 (顺序正常)", f)
        log(f"   异常文件夹: {error_folders} 个", f)
        log("-" * 50, f)
        log("  [图片总数统计]", f)
        log(f"   原始照片总数: {total_orig_images} 张", f)
        log(f"   最终输出 PNG 总数: {total_crop_images} 张", f)
        log(f"   剔除/跳过的废片总数: {total_orig_images - total_crop_images} 张", f)
        log("=" * 50, f)

        print(f"\n  报告已保存至: {report_file}")


if __name__ == "__main__":
    check_folders()
