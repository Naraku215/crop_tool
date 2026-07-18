@echo off
chcp 65001 >nul
echo ========================================
echo   crop_tool - 打包脚本
echo ========================================
echo.

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先创建:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM 安装 PyInstaller
echo [1/4] 安装 PyInstaller...
.venv\Scripts\python.exe -m pip install pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)
echo   完成
echo.

REM 清理旧构建产物
echo [2/4] 清理旧构建产物...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "crop_tool.spec" del /q "crop_tool.spec"
echo   完成
echo.

REM PyInstaller 打包
echo [3/4] 正在打包 (可能需要几分钟)...
.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir ^
  --name "crop_tool" ^
  --hidden-import pillow_heif ^
  --collect-submodules pillow_heif ^
  --collect-data pillow_heif ^
  --hidden-import PIL ^
  gui.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)
echo   完成
echo.

REM 压缩为 zip
echo [4/4] 压缩为 zip...
powershell -Command "Compress-Archive -Path 'dist\crop_tool\*' -DestinationPath 'dist\crop_tool-v2.6.zip' -Force"
echo   完成
echo.

echo ========================================
echo   打包成功！
echo ========================================
echo   输出目录: dist\crop_tool\
echo   压缩包:   dist\crop_tool-v2.6.zip
echo.
echo   请将 zip 文件上传到 GitHub Releases
echo ========================================
pause
