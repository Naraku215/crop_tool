@echo off
chcp 65001 >nul
echo ========================================
echo   图片裁剪工具 - 打包脚本
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
.venv\Scripts\pip.exe install pyinstaller >nul 2>&1
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
if exist "图片裁剪工具.spec" del /q "图片裁剪工具.spec"
echo   完成
echo.

REM PyInstaller 打包
echo [3/4] 正在打包 (可能需要几分钟)...
.venv\Scripts\pyinstaller.exe --noconfirm --windowed --onedir ^
  --name "图片裁剪工具" ^
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
powershell -Command "Compress-Archive -Path 'dist\图片裁剪工具\*' -DestinationPath 'dist\图片裁剪工具-v1.0.zip' -Force"
echo   完成
echo.

echo ========================================
echo   打包成功！
echo ========================================
echo   输出目录: dist\图片裁剪工具\
echo   压缩包:   dist\图片裁剪工具-v1.0.zip
echo.
echo   请将 zip 文件上传到 GitHub Releases
echo ========================================
pause
