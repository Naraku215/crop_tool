"""
图片水平矫正工具 - 两点拉平矫正

通过在图片上找一条应该是水平的线（点左端和右端），
自动计算倾斜角度并旋转矫正，去除黑边后恢复标准尺寸。
支持前进、后退、跳过等操作，并带断点续传功能。

进入矫正前会自动将 `源文件/` 中的所有格式图片转为 PNG。
若已裁剪过（CROPPED_DIR 有数据），则直接从裁剪结果读取。
"""

import os
import math
from pathlib import Path

import cv2
import numpy as np

import config
import trans_png
from utils import scan_all_tasks, read_image_cv2, save_image_cv2

points = []
preview_rotated = None


def get_max_inscribed_rect(w, h, angle_degrees):
    """
    核心算法：计算图片旋转后，为了不出现黑边，能保留的最大矩形框大小
    """
    angle_rad = abs(math.radians(angle_degrees))
    sin_a = math.sin(angle_rad)
    cos_a = math.cos(angle_rad)

    new_w = w / (cos_a + (h / w) * sin_a)
    new_h = h / (cos_a + (w / h) * sin_a)
    return int(new_w), int(new_h)


def mouse_callback(event, x, y, flags, param):
    global points, preview_rotated
    original_img = param['original_img']
    display_scale = param['scale']

    if event == cv2.EVENT_LBUTTONDOWN:
        if len(points) < 2:
            points.append((x, y))

        if len(points) == 2:
            dx = points[1][0] - points[0][0]
            dy = points[1][1] - points[0][1]
            angle = math.degrees(math.atan2(dy, dx))

            print(f"  [检测] 倾斜角度: {angle:.2f} 度，正在拉平...")

            h, w = original_img.shape[:2]
            center = (w // 2, h // 2)

            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(original_img, M, (w, h), flags=cv2.INTER_LANCZOS4)

            in_w, in_h = get_max_inscribed_rect(w, h, angle)
            x_start = center[0] - in_w // 2
            y_start = center[1] - in_h // 2
            cropped = rotated[y_start:y_start + in_h, x_start:x_start + in_w]

            final_img = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

            preview_h, preview_w = int(h * display_scale), int(w * display_scale)
            preview_rotated = cv2.resize(final_img, (preview_w, preview_h))

            cv2.putText(preview_rotated, "Perfect! Press ENTER to save, R to redraw",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)


def process_images():
    """
    主处理函数：自动转换格式 → 交互水平矫正所有图片

    快捷键:
        [回车] 保存已矫正的图
        [S]    此图不需要矫正，原样保存并跳过
        [R]    重新画线
        [B]    退回上一张
        [Q]    退出程序
    """
    global points, preview_rotated

    # === 自动格式转换预处理 ===
    print("\n[1/2] 自动格式转换 (任意格式 -> PNG)...")
    trans_png.convert_to_png(config.SOURCE_DIR, config.PNG_DIR)

    # === 确定输入目录：优先裁剪后的图，否则用 PNG 目录 ===
    cropped_has_png = False
    if Path(config.CROPPED_DIR).exists():
        for root, dirs, files in os.walk(config.CROPPED_DIR):
            if any(f.lower().endswith('.png') for f in files):
                cropped_has_png = True
                break

    if cropped_has_png:
        input_dir = config.CROPPED_DIR
        print("\n[2/2] 开始水平矫正 (从裁剪结果读取)...")
    else:
        input_dir = config.PNG_DIR
        print("\n[2/2] 开始水平矫正 (从 PNG 目录读取)...")
    print(f"  输入目录: {input_dir}")
    print(f"  输出目录: {config.LEVELED_DIR}")

    output_path = Path(config.LEVELED_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    tasks = scan_all_tasks(input_dir, config.LEVELED_DIR, ext='.png')

    if not tasks:
        print("  [提示] 没有找到 PNG 图片，请先进行格式转换和裁剪！")
        return

    current_index = 0
    while current_index < len(tasks) and tasks[current_index]['out_file_path'].exists():
        current_index += 1

    cv2.namedWindow("Level Tool", cv2.WINDOW_AUTOSIZE)

    while current_index < len(tasks):
        task = tasks[current_index]
        points = []
        preview_rotated = None

        original_img = read_image_cv2(task['img_path'])
        if original_img is None:
            current_index += 1
            continue

        h, w = original_img.shape[:2]
        display_scale = 900.0 / h
        display_img = cv2.resize(original_img, (int(w * display_scale), int(h * display_scale)))

        cv2.setMouseCallback("Level Tool", mouse_callback,
                             {'original_img': original_img, 'scale': display_scale})

        print(f"\n  [{current_index + 1}/{len(tasks)}] {task['folder_name']}/{task['file_name']}")
        print("  找一条水平线，点左端和右端 -> [回车]保存 | [S]无需矫正跳过 | [R]重画 | [B]退回 | [Q]退出")

        action = None
        while True:
            if preview_rotated is not None:
                cv2.imshow("Level Tool", preview_rotated)
            else:
                temp_img = display_img.copy()
                for pt in points:
                    cv2.circle(temp_img, pt, 5, (0, 0, 255), -1)
                if len(points) == 2:
                    cv2.line(temp_img, points[0], points[1], (255, 0, 0), 2)
                cv2.imshow("Level Tool", temp_img)

            key = cv2.waitKey(20) & 0xFF

            if (key == 13 or key == 10) and preview_rotated is not None:
                dx = points[1][0] - points[0][0]
                dy = points[1][1] - points[0][1]
                angle = math.degrees(math.atan2(dy, dx))

                M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                rotated = cv2.warpAffine(original_img, M, (w, h), flags=cv2.INTER_LANCZOS4)
                in_w, in_h = get_max_inscribed_rect(w, h, angle)
                x_start, y_start = (w - in_w) // 2, (h - in_h) // 2
                cropped = rotated[y_start:y_start + in_h, x_start:x_start + in_w]
                final_img = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

                save_image_cv2(final_img, task['out_file_path'])
                print("  [成功] 已拉平保存！")
                action = 'next'
                break

            elif key in [ord('s'), ord('S')]:
                save_image_cv2(original_img, task['out_file_path'])
                print("  [跳过] 图片没歪，原样保存。")
                action = 'next'
                break

            elif key in [ord('r'), ord('R')]:
                points = []
                preview_rotated = None
                print("  [重置] 请重新画线。")

            elif key in [ord('b'), ord('B')]:
                action = 'back'
                break

            elif key in [ord('q'), ord('Q')]:
                cv2.destroyAllWindows()
                return

        if action == 'next':
            current_index += 1
        elif action == 'back':
            if current_index > 0:
                current_index -= 1
            else:
                print("  [提示] 已经是第一张了！")

    cv2.destroyAllWindows()
    print("\n  [完成] 所有图片水平矫正完毕！")


if __name__ == "__main__":
    process_images()
