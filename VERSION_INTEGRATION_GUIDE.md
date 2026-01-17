# ChroLens_Sorting 版本管理整合指南

## 已完成的步驟

✅ 1. 已複製 LICENSE 檔案
✅ 2. 已複製版本管理模組（如果有 main 目錄）
   - version_manager.py
   - version_info_dialog.py

## 需要手動完成的步驟

### 1. 在主程式中添加版本定義

在主程式檔案開頭添加：

```python
VERSION = "1.0.0"
```

### 2. 匯入版本管理模組

在主程式中添加：

```python
try:
    from version_manager import VersionManager
    from version_info_dialog import VersionInfoDialog
    VERSION_MANAGER_AVAILABLE = True
except ImportError:
    print("版本管理模組未安裝")
    VERSION_MANAGER_AVAILABLE = False
```

### 3. 初始化版本管理器

在應用程式初始化時：

```python
if VERSION_MANAGER_AVAILABLE:
    self.version_manager = VersionManager(
        current_version=VERSION,
        logger=self.log  # 你的日誌函數
    )
```

### 4. 添加版本檢查功能

在 UI 中添加「檢查更新」按鈕：

```python
def check_for_updates(self):
    if not VERSION_MANAGER_AVAILABLE:
        messagebox.showinfo("提示", "版本管理功能未啟用")
        return
    
    # 開啟版本資訊對話框
    dialog = VersionInfoDialog(
        parent=self.root,
        version_manager=self.version_manager,
        current_version=VERSION,
        on_update_callback=self.on_update_complete
    )

def on_update_complete(self):
    # 更新完成後的處理
    messagebox.showinfo("提示", "更新完成！請重新啟動應用程式。")
```

### 5. 在選單中添加版本資訊

```python
# 在 Help 選單中添加
help_menu.add_command(label="關於", command=self.show_about)
help_menu.add_command(label="檢查更新", command=self.check_for_updates)

def show_about(self):
    messagebox.showinfo(
        "關於",
        f"ChroLens_Sorting\n版本: {VERSION}\n\n© 2025 Lucienwooo"
    )
```

## 測試步驟

1. 執行應用程式
2. 點擊「檢查更新」
3. 確認版本資訊正確顯示
4. 測試更新功能（需要先在 GitHub 建立 Release）

## GitHub Release 設定

在 GitHub 上建立 Release 時：
- Tag version: v1.0.0
- Release title: ChroLens_Sorting v1.0.0
- 上傳打包後的執行檔（.exe 或 .zip）
