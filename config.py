"""
crop_tool - 集中配置文件

仅包含参数配置，不包含路径。
路径由用户在 GUI 中动态选择。
"""

import sys
from pathlib import Path

# ============ 项目根目录（用于 PyInstaller 打包） ============
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).parent


# ============ 裁剪参数 ============
# 裁剪目标尺寸（宽, 高），16:9 比例
TARGET_SIZE = (1920, 1080)


# ============ PPT 参数 ============
# PPT 页面尺寸（英寸），16:9 宽屏
SLIDE_WIDTH_INCH = 13.333
SLIDE_HEIGHT_INCH = 7.5

# PPT 视觉比例矫正
# 由于原图可能被拉伸为 1920x1080 (16:9)，但实际内容比例不同（如 4:3）
# 此参数用于在 PPT 中恢复正确比例
# 常见值：4/3（标准老版PPT）、16/10（常见会议宽屏）、16/9（不矫正）
TARGET_VISUAL_RATIO = 4 / 3


# ============ GUI 参数 ============
# 缩略图尺寸（宽, 高）
THUMBNAIL_SIZE = (120, 90)


# ============ 文件格式 ============
# 支持的图片格式（用于扫描文件夹）
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

# 需要转换为 PNG 的格式（非 PNG 格式）
CONVERT_EXTS = {'.heic', '.heif', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}

# HEIC 专用格式
HEIC_EXTS = {'.heic', '.heif'}
