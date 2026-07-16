"""
图片裁剪矫正与导出工具 - 集中配置文件

所有路径默认相对于项目根目录，开箱即用。
如需自定义，只需修改本文件中的路径即可。
"""

import sys
from pathlib import Path

# ============ 路径配置 ============
# 项目根目录：打包后为 .exe 所在目录，开发模式为本文件所在目录
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后运行
    PROJECT_ROOT = Path(sys.executable).parent
else:
    # 开发模式运行
    PROJECT_ROOT = Path(__file__).parent

# 源文件目录：存放原始图片（支持 HEIC/JPG/JPEG/BMP/TIFF 等任意格式）
SOURCE_DIR = PROJECT_ROOT / "源文件"

# PNG 格式目录：自动转换格式后的 PNG 图片存放处
PNG_DIR = PROJECT_ROOT / "工程院图片PNG"

# 已裁剪目录：透视裁剪后的高清 PNG 图片
CROPPED_DIR = PROJECT_ROOT / "已裁剪照片"

# 最终拉平版目录：水平矫正后的图片
LEVELED_DIR = PROJECT_ROOT / "工程院图片_最终拉平版"

# 导出目录：生成的 PPT/PDF/Word 文件
EXPORT_DIR = PROJECT_ROOT / "导出文件"

# 转换报告路径
CONVERT_REPORT = PROJECT_ROOT / "格式转换报告" / "转换报告.txt"

# 对账检查报告路径
CHECK_REPORT = PROJECT_ROOT / "图片数量顺序检查.txt"


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


# ============ 文件格式 ============
# 支持的图片格式（用于导出时扫描）
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.heic', '.heif'}

# 需要转换为 PNG 的格式（非 PNG 格式）
CONVERT_EXTS = {'.heic', '.heif', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}

# HEIC 专用格式
HEIC_EXTS = {'.heic', '.heif'}
