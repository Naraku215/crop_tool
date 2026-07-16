# 图片裁剪矫正与导出工具

轻量化的图片批量处理工具，支持 **HEIC/JPG 等任意格式自动转 PNG**、**四点透视裁剪**、**水平倾斜矫正**，并按顺序导出为 **PPT / PDF / Word**。

适用于会议照片、报告配图等不规则，不固定机位场景的批量整理与标准化处理。

## 下载使用（免安装版）

普通用户无需安装 Python，直接下载即可使用：

1. 前往 [Releases 页面](https://github.com/Naraku215/crop_tool/releases)
2. 下载最新的 `图片裁剪工具-v1.0.zip`
3. 解压到任意目录
4. 双击 `图片裁剪工具.exe` 运行
5. 将图片放入程序目录下的 `源文件/` 文件夹，按界面按钮操作即可

## 功能特性

- **自动格式转换**：HEIC/HEIF/JPG/JPEG/BMP/TIFF 自动转 PNG，内置到裁剪/矫正流程中
- **四点透视裁剪**：鼠标点击4个点，将倾斜拍摄的图片矫正为标准 1920x1080 尺寸
- **水平矫正**：两点拉平，自动计算倾斜角度并旋转矫正，去除黑边
- **断点续传**：已处理的图片自动跳过，支持前进/后退/跳过文件夹
- **多格式导出**：PPT（含比例矫正）、PDF、Word，按文件名顺序排列
- **对账检查**：对比源文件与裁剪结果的图片数量和顺序，生成检查报告

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

### 3. 准备图片

将原始图片按人物/主题分文件夹放入 `源文件/` 目录：

```
源文件/
  ├── 张三/
  │   ├── IMG_0001.heic
  │   ├── IMG_0002.heic
  │   └── ...
  ├── 李四/
  │   └── ...
```

### 4. 运行工具

**GUI 界面（推荐）：**

```bash
python gui.py
```

**命令行菜单：**

```bash
python main.py
```

按界面/菜单提示操作即可，推荐流程：

```
[1] 图片透视裁剪  →  [4] 导出为 PPT
                  →  [5] 导出为 PDF
                  →  [6] 导出为 Word
```

选择裁剪或矫正时，工具会自动先将源文件转换为 PNG，再进入交互操作。

## 目录结构

```
crop_tool/
├── gui.py             # GUI 界面入口（普通用户）
├── main.py            # 命令行入口（开发者）
├── build.bat          # PyInstaller 打包脚本
├── config.py          # 集中配置（路径、尺寸、比例等参数）
├── utils.py           # 共享工具函数（排序、扫描、读写图片）
├── trans_png.py       # 格式转换模块（任意格式 -> PNG，内部自动调用）
├── crop_tool.py       # 四点透视裁剪（含自动格式转换）
├── level.py           # 水平矫正（含自动格式转换）
├── check_folders.py   # 文件夹对账检查
├── export.py          # 统一导出模块（PPT / PDF / Word）
├── requirements.txt   # Python 依赖
├── LICENSE            # MIT 开源协议
└── README.md
```

### 数据目录（自动生成，不入库）

```
源文件/               # 用户放入原始图片（任意格式）
工程院图片PNG/         # 自动转换后的 PNG
已裁剪照片/            # 裁剪后的高清 PNG
工程院图片_最终拉平版/  # 矫正后的图片
导出文件/              # 生成的 PPT / PDF / Word
格式转换报告/          # 转换报告
```

## 各模块说明

### 图片透视裁剪 (`crop_tool.py`)

通过鼠标点击图片的4个角点，进行透视变换矫正，输出为标准 1920x1080 尺寸。

**快捷键：**

| 按键 | 功能 |
|------|------|
| 回车 | 保存裁剪结果，进入下一张 |
| S | 跳过当前图片 |
| B | 退回上一张 |
| N | 跳过当前文件夹 |
| R | 重画（清除已点击的点） |
| Q | 退出程序 |

### 水平矫正 (`level.py`)

在图片上找一条应该是水平的线，点击左端和右端，自动计算倾斜角度并旋转矫正。

**快捷键：**

| 按键 | 功能 |
|------|------|
| 回车 | 保存矫正结果 |
| S | 此图不需要矫正，原样保存 |
| R | 重新画线 |
| B | 退回上一张 |
| Q | 退出程序 |

### 导出模块 (`export.py`)

| 格式 | 说明 |
|------|------|
| PPT | 16:9 宽屏，支持视觉比例矫正（4:3 等），每个文件夹生成一个 .pptx |
| PDF | 使用 Pillow 原生功能，每个文件夹生成一个 .pdf |
| Word | 横向页面，每张图片占一页，每个文件夹生成一个 .docx |

也可独立运行：

```bash
python export.py ppt    # 仅导出 PPT
python export.py pdf     # 仅导出 PDF
python export.py word    # 仅导出 Word
python export.py all     # 全部导出（默认）
```

## 配置说明

所有配置集中在 `config.py` 中，修改一次即可全局生效：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `SOURCE_DIR` | 源文件目录（放入原始图片） | `项目根目录/源文件` |
| `PNG_DIR` | 转换后 PNG 目录 | `项目根目录/工程院图片PNG` |
| `CROPPED_DIR` | 裁剪后目录 | `项目根目录/已裁剪照片` |
| `LEVELED_DIR` | 矫正后目录 | `项目根目录/工程院图片_最终拉平版` |
| `EXPORT_DIR` | 导出文件目录 | `项目根目录/导出文件` |
| `TARGET_SIZE` | 裁剪目标尺寸 | `(1920, 1080)` |
| `TARGET_VISUAL_RATIO` | PPT 视觉比例矫正 | `4/3` |

所有路径默认相对于项目根目录，克隆后无需修改即可使用。
如需使用其他路径，直接修改 `config.py` 中对应的值即可。

## 打包发布

使用 `build.bat` 一键打包为 Windows 可执行程序：

```bat
build.bat
```

打包完成后，`dist/` 目录下会生成：
- `图片裁剪工具/` - 可执行程序文件夹
- `图片裁剪工具-v1.0.zip` - 用于上传到 GitHub Releases 的压缩包

上传步骤：
1. 在 GitHub 仓库页面点击 Releases -> Create a new release
2. 创建 tag（如 `v1.0.0`）
3. 上传 `图片裁剪工具-v1.0.zip`
4. 发布

## 技术栈

- **OpenCV** - 图像处理、透视变换、旋转变换
- **Pillow** - 图片格式转换、PDF 生成
- **pillow-heif** - HEIC/HEIF 格式支持
- **python-pptx** - PPT 文件生成
- **python-docx** - Word 文件生成
- **NumPy** - 数值计算

## 许可证

[MIT License](LICENSE)
