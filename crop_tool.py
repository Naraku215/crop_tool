"""
图片透视裁剪工具 - 四点透视矫正裁剪

通过鼠标点击4个点，将倾斜拍摄的图片裁剪矫正为标准尺寸。
支持前进、后退、跳过、重做等操作，并带断点续传功能。

进入裁剪前会自动将 `源文件/` 中的所有格式图片转为 PNG。
"""

import cv2
import numpy as np

import config
import trans_png
from utils import scan_all_tasks, read_image_cv2, save_image_cv2

points = []


def mouse_callback(event, x, y, flags, param):
    global points
    if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
        points.append([x, y])


def order_points(pts):
    """将4个点按 左上、右上、右下、左下 排序"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def process_images():
    """
    主处理函数：自动转换格式 → 交互裁剪所有图片

    快捷键:
        [回车] 保存并进入下一张
        [S]    跳过当前图片
        [B]    退回上一张
        [N]    跳过当前文件夹（下一文件夹）
        [R]    重画（清除已点击的点）
        [Q]    退出程序
    """
    global points

    # === 自动格式转换预处理 ===
    print("\n[1/2] 自动格式转换 (任意格式 -> PNG)...")
    print(f"  源文件目录: {config.SOURCE_DIR}")
    print(f"  PNG 目录:   {config.PNG_DIR}")
    trans_png.convert_to_png(config.SOURCE_DIR, config.PNG_DIR)

    # === 交互裁剪 ===
    print("\n[2/2] 开始透视裁剪...")
    print(f"  输入目录: {config.PNG_DIR}")
    print(f"  输出目录: {config.CROPPED_DIR}")

    tasks = scan_all_tasks(config.PNG_DIR, config.CROPPED_DIR, ext='.png')

    if not tasks:
        print("  [提示] 没有找到 PNG 图片，请检查源文件目录是否有图片！")
        return

    # 断点续传：跳过已处理的图片
    current_index = 0
    while current_index < len(tasks) and tasks[current_index]['out_file_path'].exists():
        current_index += 1

    if current_index >= len(tasks):
        print("  [提示] 所有图片都已经处理过了！如需修改，请按 B 退回。")
        current_index = len(tasks) - 1

    cv2.namedWindow("Crop Tool", cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback("Crop Tool", mouse_callback)

    while current_index < len(tasks):
        task = tasks[current_index]
        points = []

        original_img = read_image_cv2(task['img_path'])
        if original_img is None:
            current_index += 1
            continue

        h, w = original_img.shape[:2]
        scale = 900.0 / h
        display_img = cv2.resize(original_img, (int(w * scale), int(h * scale)))

        is_overwrite = task['out_file_path'].exists()

        print(f"\n  [{current_index + 1}/{len(tasks)}] {task['folder_name']}/{task['file_name']}")
        if is_overwrite:
            print("  [注意] 此图已处理过，当前为重做模式，保存将覆盖原图。")
        print("  [回车]保存 | [S]跳过 | [B]退回 | [N]跳过此文件夹 | [R]重画 | [Q]退出")

        action = None
        while True:
            temp_img = display_img.copy()

            for i, pt in enumerate(points):
                cv2.circle(temp_img, tuple(pt), 5, (0, 0, 255), -1)
                if i > 0:
                    cv2.line(temp_img, tuple(points[i - 1]), tuple(pt), (0, 255, 0), 2)

            if len(points) == 4:
                cv2.line(temp_img, tuple(points[3]), tuple(points[0]), (0, 255, 0), 2)
                cv2.putText(temp_img, "Press ENTER to Save", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            if is_overwrite:
                cv2.putText(temp_img, "OVERWRITE MODE", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            cv2.imshow("Crop Tool", temp_img)
            key = cv2.waitKey(20) & 0xFF

            if (key == 13 or key == 10) and len(points) == 4:
                pts = np.array(points, dtype="float32") / scale
                rect = order_points(pts)
                dst = np.array([
                    [0, 0], [config.TARGET_SIZE[0] - 1, 0],
                    [config.TARGET_SIZE[0] - 1, config.TARGET_SIZE[1] - 1],
                    [0, config.TARGET_SIZE[1] - 1]
                ], dtype="float32")

                M = cv2.getPerspectiveTransform(rect, dst)
                warped = cv2.warpPerspective(original_img, M, config.TARGET_SIZE,
                                             flags=cv2.INTER_LANCZOS4)

                save_image_cv2(warped, task['out_file_path'])
                print("  [成功] 已保存，进入下一张。")
                action = 'next'
                break

            elif key in [ord('r'), ord('R')]:
                points = []
                print("  [刷新] 请重新点击4个点")

            elif key in [ord('s'), ord('S')]:
                print("  [跳过] 跳过此图，进入下一张。")
                action = 'next'
                break

            elif key in [ord('b'), ord('B')]:
                print("  [退回] 返回上一张图片！")
                action = 'back'
                break

            elif key in [ord('n'), ord('N')]:
                print(f"  [跳过文件夹] 正在跳过 [{task['folder_name']}] 的剩余图片...")
                action = 'next_folder'
                break

            elif key in [ord('q'), ord('Q')]:
                print("\n  [退出] 程序已退出。")
                cv2.destroyAllWindows()
                return

        if action == 'next':
            current_index += 1
        elif action == 'back':
            if current_index > 0:
                current_index -= 1
            else:
                print("  [提示] 已经是第一张图了，无法再退！")
        elif action == 'next_folder':
            current_folder = task['folder_name']
            while current_index < len(tasks) and tasks[current_index]['folder_name'] == current_folder:
                current_index += 1

    cv2.destroyAllWindows()
    print("\n  [完成] 所有图片裁剪完毕！")


if __name__ == "__main__":
    process_images()
