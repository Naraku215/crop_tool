# crop_tool

轻量化的图片批量处理工具，支持 **任意格式图片浏览**、**四点透视裁剪**、**水平倾斜矫正**，并导出为 **PPT / PDF / Word**。

适用于会议照片、报告配图等不规则、不固定机位场景的批量整理与标准化处理。

## 下载使用（免安装版）

普通用户无需安装 Python，直接下载即可使用：

1. 前往 [Releases 页面](https://github.com/Naraku215/crop_tool/releases)
2. 下载最新的 `crop_tool-v2.0.zip`
3. 解压到任意目录
4. 双击 `crop_tool.exe` 运行
5. 在界面中点击"选择图片文件夹"，选择待处理的图片文件夹即可开始

## 功能特性

- **自选文件夹**：用户自由选择输入/输出文件夹，无需固定目录
- **缩略图浏览**：所有图片以缩略图形式展示，点击切换
- **窗口内裁剪**：四点透视裁剪集成到主窗口 Canvas，不再弹出独立窗口
- **窗口内矫正**：两点水平矫正同样在主窗口内完成，带实时预览
- **任意格式支持**：HEIC/HEIF/JPG/JPEG/BMP/TIFF/PNG，PIL 直接读取，无需预转换
- **多格式导出**：PPT（含比例矫正）、PDF、Word，导出到用户自选位置

## 快速开始（开发者）

### 1. 克隆仓库

```bash
git clone https://github.com/Naraku215/crop_tool.git
cd crop_tool
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 运行工具

**GUI 界面（推荐）：**

```bash
python gui.py
```

**使用流程：**

1. 点击"选择图片文件夹"，选择包含图片的文件夹
2. 缩略图加载完成后，点击缩略图选择图片
3. 选择"裁剪模式"或"矫正模式"
4. 在主画布上点击标记点，预览结果后点击"保存"
5. 处理完成后，点击"PPT"/"PDF"/"Word"导出到自选位置

**命令行工具：**

```bash
python main.py
```

## 目录结构

```
crop_tool/
├── gui.py             # GUI 界面入口（主入口）
├── main.py            # 命令行入口（CLI 工具）
├── build.bat          # PyInstaller 打包脚本
├── config.py          # 集中配置（尺寸、比例等参数）
├── utils.py           # 共享工具函数（排序、扫描、读写图片）
├── crop_tool.py       # 四点透视裁剪核心算法
├── level.py           # 水平矫正核心算法
├── trans_png.py       # 格式转换模块（CLI 工具）
├── check_folders.py   # 文件夹对账检查（CLI 工具）
├── export.py          # 统一导出模块（PPT / PDF / Word）
├── requirements.txt   # Python 依赖
├── LICENSE            # MIT 开源协议
└── README.md
```

处理后的图片保存在输入文件夹下的 `已处理/` 子目录中，保持原子文件夹结构。

## 各模块说明

### 图片透视裁剪 (`crop_tool.py`)

通过鼠标点击图片的4个角点（左上→右上→右下→左下），进行透视变换矫正，输出为标准 1920x1080 尺寸。点击4个点后自动预览裁剪结果。

### 水平矫正 (`level.py`)

在图片上找一条应该是水平的线，点击左端和右端，自动计算倾斜角度并旋转矫正，去除黑边。点击2个点后自动预览矫正结果。

### 导出模块 (`export.py`)

| 格式 | 说明 |
|------|------|
| PPT | 16:9 宽屏，支持视觉比例矫正（4:3 等），每个子文件夹生成一个 .pptx |
| PDF | 使用 Pillow 原生功能，每个子文件夹生成一个 .pdf |
| Word | 横向页面，每张图片占一页，每个子文件夹生成一个 .docx |

CLI 独立运行：

```bash
python export.py <input_dir> <output_dir> ppt
python export.py <input_dir> <output_dir> pdf
python export.py <input_dir> <output_dir> word
python export.py <input_dir> <output_dir> all
```

## 配置说明

参数集中在 `config.py` 中：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `TARGET_SIZE` | 裁剪目标尺寸 | `(1920, 1080)` |
| `TARGET_VISUAL_RATIO` | PPT 视觉比例矫正 | `4/3` |
| `THUMBNAIL_SIZE` | 缩略图尺寸 | `(140, 105)` |
| `IMAGE_EXTS` | 支持的图片格式 | `.png .jpg .jpeg .bmp .tiff .heic .heif` |

## 打包发布

使用 `build.bat` 一键打包为 Windows 可执行程序：

```bat
build.bat
```

打包完成后，`dist/` 目录下会生成：
- `crop_tool/` - 可执行程序文件夹
- `crop_tool-v2.0.zip` - 用于上传到 GitHub Releases 的压缩包

## 技术栈

- **OpenCV** - 图像处理、透视变换、旋转变换
- **Pillow** - 图片格式读取、PDF 生成
- **pillow-heif** - HEIC/HEIF 格式支持
- **python-pptx** - PPT 文件生成
- **python-docx** - Word 文件生成
- **NumPy** - 数值计算
- **tkinter** - GUI 界面

## 许可证

[MIT License](LICENSE)
