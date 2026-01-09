@echo off
chcp 65001 >nul
title ChroLens_Sorting 打包工具 v1.2
color 0A

echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo    ChroLens_Sorting 自動打包工具 v1.2
echo    更新機制: GitHub Releases
echo ═══════════════════════════════════════════════════════════════════════════
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 1: 環境檢查
REM ═══════════════════════════════════════════════════════════════════════════
echo [1/6] 檢查 Python 環境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ❌ 錯誤：找不到 Python
    echo    請確認 Python 3.8+ 已安裝並加入系統 PATH
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo ✓ Python %PY_VER% 已就緒
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 2: 模組檢查
REM ═══════════════════════════════════════════════════════════════════════════
echo [2/6] 檢查必要模組...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ❌ 錯誤：PyInstaller 未安裝
    echo    請執行: pip install pyinstaller
    echo.
    pause
    exit /b 1
)
echo ✓ PyInstaller 已安裝

python -c "import ttkbootstrap" >nul 2>&1
if %errorlevel% neq 0 (
    color 0E
    echo ⚠️  警告：ttkbootstrap 未安裝，正在安裝...
    pip install ttkbootstrap
)
echo ✓ ttkbootstrap 已安裝
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 3: 專案檔案檢查
REM ═══════════════════════════════════════════════════════════════════════════
echo [3/6] 檢查專案檔案完整性...
set FILE_MISSING=0

if not exist "ChroLens_Sorting1.2.py" (
    echo ❌ 主程式: ChroLens_Sorting1.2.py
    set FILE_MISSING=1
) else (
    echo ✓ 主程式: ChroLens_Sorting1.2.py
)

if not exist "update_manager.py" (
    echo ❌ 更新管理器: update_manager.py
    set FILE_MISSING=1
) else (
    echo ✓ 更新管理器: update_manager.py
)

if not exist "update_dialog.py" (
    echo ❌ 更新對話框: update_dialog.py
    set FILE_MISSING=1
) else (
    echo ✓ 更新對話框: update_dialog.py
)

if not exist "umi_綠色.ico" (
    echo ⚠️  圖示: umi_綠色.ico (可選)
) else (
    echo ✓ 圖示: umi_綠色.ico
)

if %FILE_MISSING%==1 (
    color 0C
    echo.
    echo ❌ 檔案檢查失敗：有關鍵檔案遺失
    echo.
    pause
    exit /b 1
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 4: 清理舊產物
REM ═══════════════════════════════════════════════════════════════════════════
echo [4/6] 清理舊打包產物...
if exist "dist" (
    echo    正在刪除 dist 目錄...
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo    ⚠️  無法完全清理 dist 目錄（可能有檔案被佔用）
    ) else (
        echo    ✓ 已清理 dist 目錄
    )
) else (
    echo    ✓ dist 目錄不存在，無需清理
)

if exist "build" (
    echo    正在刪除 build 目錄...
    rmdir /s /q "build" 2>nul
    if exist "build" (
        echo    ⚠️  無法完全清理 build 目錄
    ) else (
        echo    ✓ 已清理 build 目錄
    )
) else (
    echo    ✓ build 目錄不存在，無需清理
)

if exist "*.spec" (
    echo    正在刪除舊的 .spec 檔案...
    del /q "*.spec" 2>nul
    echo    ✓ 已清理 .spec 檔案
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 5: 執行打包
REM ═══════════════════════════════════════════════════════════════════════════
echo [5/6] 開始執行 PyInstaller 打包...
echo ───────────────────────────────────────────────────────────────────────────

REM 設定打包參數
set APP_NAME=ChroLens_Sorting
set MAIN_SCRIPT=ChroLens_Sorting1.2.py
set ICON_FILE=umi_綠色.ico
set VERSION=1.2

REM 建立 hiddenimports 清單
set HIDDEN_IMPORTS=--hidden-import=ttkbootstrap --hidden-import=json --hidden-import=threading --hidden-import=csv

REM 檢查圖示檔案
if exist "%ICON_FILE%" (
    set ICON_PARAM=--icon="%ICON_FILE%" --add-data "%ICON_FILE%;."
) else (
    set ICON_PARAM=
)

REM 執行 PyInstaller
echo 正在打包 %APP_NAME% v%VERSION%...
pyinstaller --noconfirm --onedir --windowed ^
    --name "%APP_NAME%" ^
    %ICON_PARAM% ^
    %HIDDEN_IMPORTS% ^
    --add-data "update_manager.py;." ^
    --add-data "update_dialog.py;." ^
    "%MAIN_SCRIPT%"

set PACK_RESULT=%errorlevel%
echo ───────────────────────────────────────────────────────────────────────────

if %PACK_RESULT% neq 0 (
    color 0C
    echo.
    echo ❌ 打包過程失敗 (錯誤碼: %PACK_RESULT%)
    echo    請檢查上方輸出的錯誤訊息
    echo.
    pause
    exit /b %PACK_RESULT%
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 6: 驗證打包結果
REM ═══════════════════════════════════════════════════════════════════════════
echo [6/6] 驗證打包產物...

if not exist "dist\%APP_NAME%" (
    color 0C
    echo ❌ 找不到輸出目錄: dist\%APP_NAME%
    pause
    exit /b 1
)
echo ✓ 輸出目錄存在: dist\%APP_NAME%

if not exist "dist\%APP_NAME%\%APP_NAME%.exe" (
    color 0C
    echo ❌ 找不到主執行檔: %APP_NAME%.exe
    pause
    exit /b 1
)
echo ✓ 主執行檔存在: %APP_NAME%.exe

REM 取得檔案大小
for %%A in ("dist\%APP_NAME%\%APP_NAME%.exe") do set EXE_SIZE=%%~zA
set /a EXE_SIZE_MB=%EXE_SIZE%/1048576
echo ✓ 執行檔大小: 約 %EXE_SIZE_MB% MB
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 步驟 7: 建立 ZIP 壓縮檔
REM ═══════════════════════════════════════════════════════════════════════════
echo [7/7] 建立發布用 ZIP 壓縮檔...
set ZIP_NAME=%APP_NAME%_v%VERSION%.zip

REM 使用 PowerShell 壓縮
powershell -Command "Compress-Archive -Path 'dist\%APP_NAME%\*' -DestinationPath 'dist\%ZIP_NAME%' -Force"

if exist "dist\%ZIP_NAME%" (
    for %%A in ("dist\%ZIP_NAME%") do set ZIP_SIZE=%%~zA
    set /a ZIP_SIZE_MB=%ZIP_SIZE%/1048576
    echo ✓ ZIP 壓縮檔已建立: dist\%ZIP_NAME% (約 %ZIP_SIZE_MB% MB)
) else (
    color 0E
    echo ⚠️ 無法建立 ZIP 壓縮檔
    echo    請手動壓縮 dist\%APP_NAME% 目錄
)
echo.

REM ═══════════════════════════════════════════════════════════════════════════
REM 完成訊息
REM ═══════════════════════════════════════════════════════════════════════════
color 0A
echo ═══════════════════════════════════════════════════════════════════════════
echo ✅ 打包完成！
echo ═══════════════════════════════════════════════════════════════════════════
echo.
echo 📦 輸出目錄: dist\%APP_NAME%\
echo 📦 ZIP 檔案: dist\%ZIP_NAME%
echo.
echo 🧪 測試建議:
echo    1. 執行 dist\%APP_NAME%\%APP_NAME%.exe 確認正常啟動
echo    2. 測試基本功能（列出清單、移動、復原、模板）
echo    3. 測試新功能（遞迴搜尋、正則模式、統計報表）
echo    4. 點擊「版本」檢查是否能連接 GitHub API
echo.
echo 🚀 發布新版本流程:
echo    【步驟 1】本地準備
echo       a) 更新 ChroLens_Sorting1.2.py 中的 CURRENT_VERSION = "1.x"
echo       b) 執行本打包腳本 (打包.bat)
echo       c) 測試所有功能
echo.
echo    【步驟 2】GitHub 發布
echo       a) 提交程式碼: git add . ^&^& git commit -m "v1.x"
echo       b) 推送到 GitHub: git push origin main
echo       c) 前往 GitHub → Releases → Create a new release
echo          • Tag version: v1.x
echo          • Release title: ChroLens_Sorting v1.x
echo          • Description: 詳細更新說明
echo          • 上傳 dist\%ZIP_NAME%
echo       d) 點擊「Publish release」
echo.
echo ═══════════════════════════════════════════════════════════════════════════
echo.
pause
