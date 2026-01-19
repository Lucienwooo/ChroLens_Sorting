# -*- coding: utf-8 -*-
"""
ChroLens_Sorting 1.2 - 自動檔案整理工具
新增功能：復原、預覽、正則、自動子資料夾、遞迴搜尋、重命名規則、通知、多設定檔、模板系統、統計報表
"""

try:
    from version_manager import VersionManager
    from version_info_dialog import VersionInfoDialog
except ImportError:
    pass
import os
import shutil
import re
import json
import datetime
import sys
import threading
import csv
from collections import defaultdict
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, simpledialog
import tkinter as tk

# 嘗試載入通知模組
try:
    from plyer import notification
    NOTIFY_AVAILABLE = True
except ImportError:
    NOTIFY_AVAILABLE = False

from version_manager import VersionManager
from update_dialog import UpdateDialog, NoUpdateDialog

# ============================================================================
# 全域設定
# ============================================================================
SETTINGS_FILE = "settings.json"
TEMPLATES_FILE = "templates.json"
STATS_FILE = "stats.json"
SCHEDULE_FILE = "schedule_times.json"
GITHUB_REPO = "Lucienwooo/ChroLens_Sorting"
CURRENT_VERSION = "1.2"

# 模板設定（使用者完全自訂）

# ============================================================================
# 主程式類別
# ============================================================================
class AutoMoveApp:
    """ChroLens_Sorting 1.2 主程式"""
    
    def __init__(self, root):
        self.tip = None
        self.root = root
        self.root.title(f"ChroLens_Sorting {CURRENT_VERSION}")
        self._set_icon()
        
        self.style = tb.Style("darkly")
        self.font = ('微軟正黑體', 11)
        
        # 基本變數
        self.extension_entries = []
        self.dest_entries = []
        self.kind_var = tb.StringVar(value="3")
        self.move_delay_var = tb.StringVar(value="0")
        self.auto_close_var = tb.StringVar(value="0")
        
        # v1.2 新功能變數
        self.auto_subfolder_var = tk.BooleanVar(value=False)  # 移動時建立當日資料夾
        self.conflict_var = tk.StringVar(value="skip")  # 衝突處理
        
        # 停止標記
        self._stop_flag = False
        self._countdown_after_id = None
        
        # 移動歷史（用於復原）
        self._move_history = []
        self._max_history = 100
        
        # 統計資料
        self._stats = self._load_stats()
        
        # 模板
        self._templates = self._load_templates()
        
        # 拖曳功能
        self._drag_data = {"widget": None, "index": None, "type": None, "tip": None}
        
        self._build_ui()
        self._settings_loaded = False
        self.load_settings()
        self._start_auto_move()
    
    def _set_icon(self):
        try:
            icon_path = os.path.join(getattr(sys, "_MEIPASS", ""), "umi_綠色.ico") if hasattr(sys, "_MEIPASS") else "umi_綠色.ico"
            self.root.iconbitmap(icon_path)
        except:
            pass
    
    def _build_ui(self):
        """建立 UI"""
        # === row 0: 上方操作列 ===
        top_frame = tb.Frame(self.root)
        top_frame.pack(pady=5, anchor='w', padx=10, fill='x')
        
        tb.Button(top_frame, text="列出清單", command=self.list_files).pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="停止", command=self.stop_all, bootstyle="warning").pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="移動", command=self.move_files, bootstyle="success").pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="復原", command=self.undo_move, bootstyle="danger").pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="模板", command=self.open_template_window, bootstyle="info").pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="統計", command=self.show_stats, bootstyle="secondary").pack(side=LEFT, padx=2)
        tb.Button(top_frame, text="版本", command=self.check_for_updates, bootstyle="info").pack(side=LEFT, padx=2)
        
        # 種類選擇
        kind_box = tb.Combobox(top_frame, textvariable=self.kind_var, width=3, values=[str(i) for i in range(1, 21)])
        kind_box.pack(side=LEFT, padx=(10, 0))
        kind_box.bind("<<ComboboxSelected>>", self.update_dynamic_fields)
        tb.Label(top_frame, text="種").pack(side=LEFT, padx=(2, 5))
        
        # === row 1: 選項列 ===
        opt_frame = tb.Frame(self.root)
        opt_frame.pack(pady=3, anchor='w', padx=10, fill='x')
        
        tb.Checkbutton(opt_frame, text="移動時建立當日資料夾", variable=self.auto_subfolder_var, bootstyle="round-toggle").pack(side=LEFT, padx=5)
        
        # 衝突處理
        tb.Label(opt_frame, text="衝突:").pack(side=LEFT, padx=(10, 2))
        conflict_box = tb.Combobox(opt_frame, textvariable=self.conflict_var, width=8, 
                                   values=["skip", "overwrite", "rename"], state="readonly")
        conflict_box.pack(side=LEFT)
        
        # 延遲設定
        tb.Entry(opt_frame, width=3, textvariable=self.move_delay_var).pack(side=LEFT, padx=(15, 0))
        tb.Label(opt_frame, text="秒後移動").pack(side=LEFT)
        tb.Entry(opt_frame, width=3, textvariable=self.auto_close_var).pack(side=LEFT, padx=(10, 0))
        tb.Label(opt_frame, text="秒後關閉").pack(side=LEFT)
        
        # === row 2: 全部欄位 ===
        zero_frame = tb.Frame(self.root)
        zero_frame.pack(anchor='w', padx=10, pady=3)
        tb.Label(zero_frame, text="0.", width=3).pack(side=LEFT)
        self.all_var = tk.BooleanVar(value=False)
        tb.Checkbutton(zero_frame, variable=self.all_var, text="全部", bootstyle="success").pack(side=LEFT)
        self.entry_all_path = tb.Entry(zero_frame, width=40, font=self.font)
        self.entry_all_path.pack(side=LEFT, padx=2)
        tb.Button(zero_frame, text="存放位置", command=lambda: self.select_dest_folder(self.entry_all_path)).pack(side=LEFT)
        
        # === row 3: 動態欄位 ===
        self.dest_frame = tb.Frame(self.root)
        self.dest_frame.pack(pady=3, anchor='w', padx=10)
        
        # === row 4: 來源資料夾 ===
        source_row = tb.Frame(self.root)
        source_row.pack(pady=5, anchor='w', padx=10)
        self.source_entry = tb.Entry(source_row, width=35, font=self.font)
        self.source_entry.pack(side=LEFT)
        tb.Button(source_row, text="取出位置", command=self.select_source_folder, bootstyle="danger").pack(side=LEFT, padx=3)
        tb.Button(source_row, text="存檔", command=self.save_settings, bootstyle="warning").pack(side=LEFT, padx=3)
        tb.Button(source_row, text="匯入", command=self.import_settings, bootstyle="secondary").pack(side=LEFT, padx=3)
        tb.Button(source_row, text="匯出", command=self.export_settings, bootstyle="secondary").pack(side=LEFT, padx=3)
        tb.Button(source_row, text="排程", command=self.open_schedule_window, bootstyle="info").pack(side=LEFT, padx=3)
        
        # === row 5: 日誌 ===
        self.log_display = tb.Text(self.root, height=12, width=75, font=('Consolas', 9), wrap='word')
        self.log_display.pack(pady=5, padx=10, fill='both', expand=True)
        
        self.update_dynamic_fields()
        if not os.path.exists(SETTINGS_FILE):
            self.source_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
    
    def update_dynamic_fields(self, event=None):
        """動態更新欄位（保留現有資料）"""
        # 先保存現有資料
        old_exts = [e.get() for e in self.extension_entries]
        old_dests = [e.get() for e in self.dest_entries]
        
        for w in self.dest_frame.winfo_children():
            w.destroy()
        self.extension_entries.clear()
        self.dest_entries.clear()
        
        try:
            count = min(max(int(self.kind_var.get()), 1), 20)
        except:
            count = 3
        
        for i in range(count):
            row = tb.Frame(self.dest_frame)
            row.pack(anchor='w', pady=1)
            tb.Label(row, text=f"{i+1}.", width=3).pack(side=LEFT)
            
            ext_entry = tb.Entry(row, width=15, font=self.font)
            ext_entry.pack(side=LEFT, padx=2)
            ext_entry.bind("<Button-3>", lambda e, ent=ext_entry: ent.delete(0, "end"))
            # 拖曳事件
            ext_entry.bind("<ButtonPress-1>", lambda e, idx=i: self._start_drag(e, idx, "ext"))
            ext_entry.bind("<B1-Motion>", self._do_drag)
            ext_entry.bind("<ButtonRelease-1>", self._stop_drag)
            # 恢復舊資料
            if i < len(old_exts):
                ext_entry.insert(0, old_exts[i])
            self.extension_entries.append(ext_entry)
            
            dest_entry = tb.Entry(row, width=40, font=self.font)
            dest_entry.pack(side=LEFT, padx=2)
            dest_entry.bind("<Button-3>", lambda e, ent=dest_entry: ent.delete(0, "end"))
            # 拖曳事件
            dest_entry.bind("<ButtonPress-1>", lambda e, idx=i: self._start_drag(e, idx, "dest"))
            dest_entry.bind("<B1-Motion>", self._do_drag)
            dest_entry.bind("<ButtonRelease-1>", self._stop_drag)
            # 恢復舊資料
            if i < len(old_dests):
                dest_entry.insert(0, old_dests[i])
            self.dest_entries.append(dest_entry)
            
            tb.Button(row, text="存放位置", command=lambda e=dest_entry: self.select_dest_folder(e)).pack(side=LEFT)
        
        self.root.update_idletasks()
        self.root.geometry("")
    
    # ==================== 檔案操作 ====================
    
    def select_source_folder(self):
        folder = filedialog.askdirectory(initialdir=self.source_entry.get() or os.path.expanduser("~"))
        if folder:
            self.source_entry.delete(0, 'end')
            self.source_entry.insert(0, folder)
            self.log(f"選擇取出位置：{folder}")
    
    def select_dest_folder(self, entry):
        folder = filedialog.askdirectory(initialdir=entry.get() or self.source_entry.get() or os.path.expanduser("~"))
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)
    
    def _get_files(self, path):
        """取得檔案列表"""
        files = []
        for f in os.listdir(path):
            if os.path.isdir(os.path.join(path, f)):
                files.append(f + "/")
            else:
                files.append(f)
        return files
    
    def _match_pattern(self, filename, pattern):
        """匹配檔案"""
        if pattern == "[資料夾]":
            return filename.endswith("/")
        elif pattern.startswith("."):
            return filename.lower().endswith(pattern.lower()) and not filename.endswith("/")
        else:
            return pattern.lower() in filename.lower()
    
    def _resolve_dest_path(self, base_dest, filename):
        """解析目的路徑（建立當日資料夾）"""
        if not self.auto_subfolder_var.get():
            return base_dest
        
        # 建立 YYYY-MM-DD 格式的資料夾
        today = datetime.date.today().strftime("%Y-%m-%d")
        dest = os.path.join(base_dest, today)
        
        if not os.path.exists(dest):
            os.makedirs(dest, exist_ok=True)
        return dest
    
    def _handle_conflict(self, src_path, dst_path):
        """處理檔案衝突"""
        if not os.path.exists(dst_path):
            return dst_path, True
        
        mode = self.conflict_var.get()
        if mode == "skip":
            return dst_path, False
        elif mode == "overwrite":
            return dst_path, True
        elif mode == "rename":
            base, ext = os.path.splitext(dst_path)
            i = 1
            while os.path.exists(f"{base}_{i}{ext}"):
                i += 1
            return f"{base}_{i}{ext}", True
        return dst_path, False
    
    def list_files(self):
        """列出檔案"""
        path = self.source_entry.get().strip()
        if not path or not os.path.isdir(path):
            self.log("錯誤：來源路徑無效")
            return
        
        try:
            files = self._get_files(path)
        except Exception as e:
            self.log(f"錯誤：{e}")
            return
        
        ext_count = defaultdict(int)
        for f in files:
            if f.endswith("/"):
                ext_count["[資料夾]"] += 1
            else:
                ext = os.path.splitext(f)[1] or "(無副檔名)"
                ext_count[ext] += 1
        
        self.log(f"在 {path} 找到 {len(files)} 個項目：")
        for ext, count in sorted(ext_count.items()):
            self.log(f"  {ext}: {count} 個")
        
        # 自動填入
        ext_list = [e for e in ext_count.keys() if e != "(無副檔名)"][:20]
        if ext_list:
            self.kind_var.set(str(len(ext_list)))
            self.update_dynamic_fields()
            for entry, ext in zip(self.extension_entries, ext_list):
                entry.delete(0, "end")
                entry.insert(0, ext)
            for entry in self.dest_entries:
                entry.delete(0, "end")
                entry.insert(0, path)
    
    def stop_all(self):
        """停止所有動作"""
        self._stop_flag = True
        if self._countdown_after_id:
            self.root.after_cancel(self._countdown_after_id)
            self._countdown_after_id = None
        self.log("已停止所有動作")
    
    def _calculate_moves(self, src):
        """計算要移動的檔案"""
        files = self._get_files(src)
        moves = []
        moved = set()
        
        for ext, dst in zip([e.get().strip() for e in self.extension_entries],
                           [e.get().strip() for e in self.dest_entries]):
            if not ext or not dst:
                continue
            for f in files:
                if f in moved:
                    continue
                if self._match_pattern(f.rstrip("/"), ext):
                    real_dst = self._resolve_dest_path(dst, f.rstrip("/"))
                    moves.append((f.rstrip("/"), real_dst))
                    moved.add(f)
        
        # 處理「全部」
        if self.all_var.get():
            all_dst = self.entry_all_path.get().strip()
            if all_dst:
                for f in files:
                    if f not in moved:
                        moves.append((f.rstrip("/"), all_dst))
        
        return moves
    
    def move_files(self):
        """執行移動"""
        src = self.source_entry.get().strip()
        if not src or not os.path.isdir(src):
            self.log("錯誤：來源路徑無效")
            messagebox.showerror("錯誤", "請選擇有效的來源資料夾")
            return
        
        moves = self._calculate_moves(src)
        if not moves:
            self.log("沒有符合條件的檔案")
            return
        
        moved = 0
        failed = 0
        batch_history = []
        
        for filename, dest in moves:
            src_path = os.path.join(src, filename)
            dst_path = os.path.join(dest, os.path.basename(filename))
            
            if not os.path.exists(dest):
                try:
                    os.makedirs(dest, exist_ok=True)
                except:
                    self.log(f"無法建立目錄：{dest}")
                    failed += 1
                    continue
            
            final_dst, should_move = self._handle_conflict(src_path, dst_path)
            
            if not should_move:
                self.log(f"跳過：{filename}（已存在）")
                failed += 1
                continue
            
            try:
                shutil.move(src_path, final_dst)
                self.log(f"移動：{filename}")
                batch_history.append((final_dst, src_path))
                moved += 1
            except Exception as e:
                self.log(f"失敗：{filename}（{e}）")
                failed += 1
        
        # 記錄歷史
        if batch_history:
            self._move_history.append(batch_history)
            if len(self._move_history) > self._max_history:
                self._move_history.pop(0)
        
        self.log(f"完成：{moved} 成功，{failed} 失敗")
        self._update_stats(moved)
        self._send_notification(f"移動完成：{moved} 成功，{failed} 失敗")
        
        # 自動關閉
        try:
            sec = int(self.auto_close_var.get())
            if sec > 0:
                self._countdown("關閉", sec, self.root.destroy)
        except:
            pass
    
    def undo_move(self):
        """復原上次移動（含確認視窗）"""
        if not self._move_history:
            self.log("沒有可復原的移動記錄")
            messagebox.showinfo("提示", "沒有可復原的移動記錄")
            return
        
        # 顯示復原預覽視窗
        preview_win = tb.Toplevel(self.root)
        preview_win.title("復原預覽")
        preview_win.geometry("600x400")
        preview_win.grab_set()
        
        tb.Label(preview_win, text="以下檔案將被復原：", font=('微軟正黑體', 12, 'bold')).pack(pady=10)
        
        # 列表框架
        list_frame = tb.Frame(preview_win)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        text = tb.Text(list_frame, font=('Consolas', 9), wrap='none')
        text.pack(side=LEFT, fill='both', expand=True)
        
        scrollbar_y = tb.Scrollbar(list_frame, orient="vertical", command=text.yview)
        scrollbar_y.pack(side=LEFT, fill='y')
        text.config(yscrollcommand=scrollbar_y.set)
        
        scrollbar_x = tb.Scrollbar(preview_win, orient="horizontal", command=text.xview)
        scrollbar_x.pack(fill='x', padx=10)
        text.config(xscrollcommand=scrollbar_x.set)
        
        # 顯示復原資訊
        batch = self._move_history[-1]
        for current_path, original_path in batch:
            text.insert('end', f"{current_path}\n  → {original_path}\n\n")
        
        text.config(state='disabled')
        
        def do_undo():
            batch = self._move_history.pop()
            restored = 0
            
            for current_path, original_path in reversed(batch):
                try:
                    if os.path.exists(current_path):
                        os.makedirs(os.path.dirname(original_path), exist_ok=True)
                        shutil.move(current_path, original_path)
                        self.log(f"復原：{os.path.basename(original_path)}")
                        restored += 1
                except Exception as e:
                    self.log(f"復原失敗：{e}")
            
            self.log(f"復原完成：{restored} 個檔案")
            preview_win.destroy()
        
        # 按鈕
        btn_frame = tb.Frame(preview_win)
        btn_frame.pack(pady=10)
        tb.Button(btn_frame, text="確認復原", command=do_undo, bootstyle="success", width=12).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="取消", command=preview_win.destroy, bootstyle="secondary", width=12).pack(side=LEFT, padx=5)
    
    # ==================== 模板系統 ====================
    
    def _load_templates(self):
        """載入使用者自訂模板"""
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_templates(self):
        """儲存所有模板"""
        try:
            with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._templates, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def open_template_window(self):
        """開啟模板管理視窗"""
        win = tb.Toplevel(self.root)
        win.title("分類模板")
        win.geometry("500x450")
        win.grab_set()
        
        # 標題
        tb.Label(win, text="分類模板管理", font=('微軟正黑體', 14, 'bold')).pack(pady=(10, 5))
        tb.Label(win, text="在主程式設定好配置後，可儲存為模板重複使用", 
                font=('微軟正黑體', 9)).pack(pady=(0, 5))
        
        # 模板列表框架
        list_frame = tb.Frame(win)
        list_frame.pack(fill='both', expand=True, padx=15, pady=5)
        
        listbox = tk.Listbox(list_frame, font=('微軟正黑體', 10), height=10)
        listbox.pack(side=LEFT, fill='both', expand=True)
        
        scrollbar = tb.Scrollbar(list_frame, command=listbox.yview)
        scrollbar.pack(side=LEFT, fill='y')
        listbox.config(yscrollcommand=scrollbar.set)
        
        def refresh_list():
            listbox.delete(0, tk.END)
            if not self._templates:
                listbox.insert(tk.END, "（尚無模板）")
            else:
                for name in self._templates:
                    template = self._templates[name]
                    ext_count = len(template.get("extensions", []))
                    listbox.insert(tk.END, f"{name} ({ext_count} 個副檔名)")
        
        def apply_template():
            sel = listbox.curselection()
            if not sel or not self._templates:
                messagebox.showinfo("提示", "請先選擇一個模板")
                return
            
            # 取得真正的模板名稱（移除括號說明）
            item = listbox.get(sel[0])
            if item.startswith("（"):
                return
            name = item.rsplit(" (", 1)[0]
            
            template = self._templates.get(name)
            if not template:
                return
            
            # 套用完整配置
            config = template.get("config", {})
            exts = template.get("extensions", [])
            dests = template.get("destinations", [])
            
            # 設定欄位數量
            self.kind_var.set(str(max(len(exts), 1)))
            self.update_dynamic_fields()
            
            # 填入副檔名
            for entry, ext in zip(self.extension_entries, exts):
                entry.delete(0, "end")
                entry.insert(0, ext)
            
            # 填入目的路徑
            for entry, dest in zip(self.dest_entries, dests):
                entry.delete(0, "end")
                entry.insert(0, dest)
            
            # 填入其他設定
            if config.get("source"):
                self.source_entry.delete(0, "end")
                self.source_entry.insert(0, config.get("source", ""))
            
            self.move_delay_var.set(config.get("move_delay", "0"))
            self.auto_close_var.set(config.get("auto_close", "0"))
            self.recursive_var.set(config.get("recursive", False))
            self.regex_mode_var.set(config.get("regex_mode", False))
            self.auto_subfolder_var.set(config.get("auto_subfolder", False))
            self.conflict_var.set(config.get("conflict", "skip"))
            
            self.log(f"已套用模板：{name}")
            win.destroy()
        
        def save_current_config():
            """儲存當前完整配置為模板"""
            name = simpledialog.askstring("儲存模板", "請輸入模板名稱：", parent=win)
            if not name:
                return
            
            exts = [e.get().strip() for e in self.extension_entries if e.get().strip()]
            dests = [e.get().strip() for e in self.dest_entries]
            
            if not exts:
                messagebox.showwarning("警告", "請先在主介面設定至少一個副檔名")
                return
            
            # 儲存完整配置
            self._templates[name] = {
                "extensions": exts,
                "destinations": dests,
                "config": {
                    "source": self.source_entry.get().strip(),
                    "move_delay": self.move_delay_var.get(),
                    "auto_close": self.auto_close_var.get(),
                    "recursive": self.recursive_var.get(),
                    "regex_mode": self.regex_mode_var.get(),
                    "auto_subfolder": self.auto_subfolder_var.get(),
                    "conflict": self.conflict_var.get(),
                },
                "description": "完整配置模板"
            }
            self._save_templates()
            refresh_list()
            self.log(f"已儲存模板：{name}（包含完整配置）")
        
        def delete_template():
            sel = listbox.curselection()
            if not sel or not self._templates:
                return
            
            item = listbox.get(sel[0])
            if item.startswith("（"):
                return
            name = item.rsplit(" (", 1)[0]
            
            if messagebox.askyesno("確認刪除", f"確定要刪除模板「{name}」嗎？"):
                if name in self._templates:
                    del self._templates[name]
                    self._save_templates()
                    refresh_list()
                    self.log(f"已刪除模板：{name}")
        
        # 按鈕區域
        btn_frame = tb.Frame(win)
        btn_frame.pack(pady=15)
        
        tb.Button(btn_frame, text="套用選中模板", command=apply_template, 
                 bootstyle="success", width=14).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="儲存當前配置", command=save_current_config, 
                 bootstyle="info", width=14).pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="刪除", command=delete_template, 
                 bootstyle="danger", width=8).pack(side=LEFT, padx=5)
        
        # 說明
        hint_frame = tb.Frame(win)
        hint_frame.pack(pady=(0, 10), padx=15, fill='x')
        tb.Label(hint_frame, text="提示：模板會儲存副檔名、目的路徑及所有選項設定", 
                font=('微軟正黑體', 9), foreground='gray').pack()
        
        refresh_list()
    
    # ==================== 統計系統 ====================
    
    def _load_stats(self):
        if os.path.exists(STATS_FILE):
            try:
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"total": 0, "daily": {}}
    
    def _save_stats(self):
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._stats, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _update_stats(self, count):
        today = datetime.date.today().isoformat()
        self._stats["total"] += count
        self._stats["daily"][today] = self._stats["daily"].get(today, 0) + count
        self._save_stats()
    
    def show_stats(self):
        """顯示統計"""
        win = tb.Toplevel(self.root)
        win.title("統計報表")
        win.geometry("400x350")
        
        tb.Label(win, text=f"總移動檔案：{self._stats['total']} 個", 
                font=('微軟正黑體', 14, 'bold')).pack(pady=15)
        
        tb.Label(win, text="每日統計（最近7天）：", font=('微軟正黑體', 11)).pack(anchor='w', padx=20)
        
        text = tb.Text(win, height=10, font=('Consolas', 10))
        text.pack(padx=20, pady=10, fill='both', expand=True)
        
        daily = self._stats.get("daily", {})
        for date in sorted(daily.keys(), reverse=True)[:7]:
            text.insert('end', f"{date}: {daily[date]} 個\n")
        
        def export_csv():
            path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if path:
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["日期", "移動數量"])
                    for date, count in sorted(daily.items()):
                        writer.writerow([date, count])
                self.log(f"已匯出統計：{path}")
        
        tb.Button(win, text="匯出 CSV", command=export_csv).pack(pady=10)
    
    # ==================== 設定與通知 ====================
    
    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.kind_var.set(data.get("kind_var", "3"))
            self.move_delay_var.set(data.get("move_delay_var", "0"))
            self.auto_close_var.set(data.get("auto_close_var", "0"))
            self.auto_subfolder_var.set(data.get("auto_subfolder", False))
            self.conflict_var.set(data.get("conflict", "skip"))
            
            self.update_dynamic_fields()
            
            for entry, val in zip(self.extension_entries, data.get("extensions", [])):
                entry.delete(0, "end")
                entry.insert(0, val)
            for entry, val in zip(self.dest_entries, data.get("destinations", [])):
                entry.delete(0, "end")
                entry.insert(0, val)
            
            if data.get("source"):
                self.source_entry.delete(0, "end")
                self.source_entry.insert(0, data["source"])
            
            self._settings_loaded = True
            self.log("設定載入成功")
        except Exception as e:
            self.log(f"設定載入失敗：{e}")
    
    def save_settings(self):
        try:
            data = {
                "kind_var": self.kind_var.get(),
                "move_delay_var": self.move_delay_var.get(),
                "auto_close_var": self.auto_close_var.get(),
                "auto_subfolder": self.auto_subfolder_var.get(),
                "conflict": self.conflict_var.get(),
                "extensions": [e.get() for e in self.extension_entries],
                "destinations": [e.get() for e in self.dest_entries],
                "source": self.source_entry.get(),
            }
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log("設定已儲存")
        except Exception as e:
            self.log(f"儲存失敗：{e}")
    
    def import_settings(self):
        """匯入設定檔"""
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.load_settings()
                self.log(f"已匯入設定：{path}")
            except Exception as e:
                self.log(f"匯入失敗：{e}")
    
    def export_settings(self):
        """匯出設定檔"""
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            self.save_settings()
            try:
                shutil.copy(SETTINGS_FILE, path)
                self.log(f"已匯出設定：{path}")
            except Exception as e:
                self.log(f"匯出失敗：{e}")
    
    def _send_notification(self, message):
        """發送系統通知"""
        if NOTIFY_AVAILABLE:
            try:
                notification.notify(
                    title="ChroLens Sorting",
                    message=message,
                    timeout=5
                )
            except:
                pass
    
    def _countdown(self, mode, seconds, callback):
        if self._stop_flag or seconds <= 0:
            if not self._stop_flag:
                callback()
            self._stop_flag = False
            self._countdown_after_id = None
            return
        self.log(f"{mode}倒數：{seconds} 秒")
        self._countdown_after_id = self.root.after(1000, lambda: self._countdown(mode, seconds - 1, callback))
    
    def _start_auto_move(self):
        try:
            delay = int(self.move_delay_var.get())
            if delay > 0:
                self._countdown("自動移動", delay, self.move_files)
        except:
            pass
    
    def log(self, message):
        self.log_display.insert('end', message + '\n')
        line_count = int(self.log_display.index('end-1c').split('.')[0])
        if line_count > 1000:
            self.log_display.delete("1.0", f"{line_count - 500}.0")
        self.log_display.see('end')
    
    # ==================== 拖曳功能 ====================
    
    def _start_drag(self, event, idx, typ):
        """開始拖曳欄位內容"""
        self._drag_data["widget"] = event.widget
        self._drag_data["index"] = idx
        self._drag_data["type"] = typ
        value = event.widget.get()
        if value:
            self._drag_data["tip"] = tip = tk.Toplevel(self.root)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tip, text=value[:30] + ("..." if len(value) > 30 else ""), 
                           background="#ffffe0", relief="solid", borderwidth=1, 
                           font=("微軟正黑體", 10))
            label.pack(ipadx=5, ipady=2)
    
    def _do_drag(self, event):
        """拖曳中更新提示位置"""
        tip = self._drag_data.get("tip")
        if tip:
            tip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
    
    def _stop_drag(self, event):
        """停止拖曳並交換欄位內容"""
        if self._drag_data["widget"] is None:
            return
        
        x, y = event.x_root, event.y_root
        entries = self.extension_entries if self._drag_data["type"] == "ext" else self.dest_entries
        target_idx = None
        
        # 尋找放置目標
        for idx, entry in enumerate(entries):
            ex = entry.winfo_rootx()
            ey = entry.winfo_rooty()
            ew = entry.winfo_width()
            eh = entry.winfo_height()
            if ex <= x <= ex + ew and ey <= y <= ey + eh:
                target_idx = idx
                break
        
        # 交換內容
        if target_idx is not None and target_idx != self._drag_data["index"]:
            src_entry = entries[self._drag_data["index"]]
            dst_entry = entries[target_idx]
            src_val = src_entry.get()
            dst_val = dst_entry.get()
            src_entry.delete(0, "end")
            src_entry.insert(0, dst_val)
            dst_entry.delete(0, "end")
            dst_entry.insert(0, src_val)
            self.log(f"已交換 {self._drag_data['type']} 欄位 {self._drag_data['index']+1} ↔ {target_idx+1}")
        
        # 清理
        if self._drag_data.get("tip"):
            self._drag_data["tip"].destroy()
        self._drag_data = {"widget": None, "index": None, "type": None, "tip": None}
    
    # ==================== 排程與更新 ====================
    
    def open_schedule_window(self):
        """開啟排程視窗"""
        win = tb.Toplevel(self.root)
        win.title("定時執行")
        win.geometry("350x400")
        win.grab_set()
        
        tb.Label(win, text="設定執行時間 (24小時制)", font=('微軟正黑體', 11)).pack(pady=10)
        
        time_frame = tb.Frame(win)
        time_frame.pack()
        hour_var = tk.StringVar(value="09")
        minute_var = tk.StringVar(value="00")
        tb.Combobox(time_frame, textvariable=hour_var, width=4, values=[f"{i:02d}" for i in range(24)], state="readonly").pack(side=LEFT)
        tb.Label(time_frame, text=":").pack(side=LEFT)
        tb.Combobox(time_frame, textvariable=minute_var, width=4, values=[f"{i:02d}" for i in range(60)], state="readonly").pack(side=LEFT)
        
        listbox = tk.Listbox(win, height=8, font=('Consolas', 12))
        listbox.pack(pady=10, fill='both', expand=True, padx=20)
        
        def load_schedule():
            if os.path.exists(SCHEDULE_FILE):
                try:
                    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                        for t in json.load(f):
                            listbox.insert(tk.END, t)
                except:
                    pass
        
        def save_schedule():
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(list(listbox.get(0, tk.END)), f)
        
        def add_time():
            val = f"{hour_var.get()}:{minute_var.get()}"
            if val not in listbox.get(0, tk.END):
                listbox.insert(tk.END, val)
                self._create_task(val)
                save_schedule()
        
        def remove_time():
            for idx in reversed(listbox.curselection()):
                self._delete_task(listbox.get(idx))
                listbox.delete(idx)
            save_schedule()
        
        btn_frame = tb.Frame(win)
        btn_frame.pack(pady=10)
        tb.Button(btn_frame, text="新增", command=add_time, bootstyle="success").pack(side=LEFT, padx=5)
        tb.Button(btn_frame, text="移除", command=remove_time, bootstyle="danger").pack(side=LEFT, padx=5)
        
        load_schedule()
    
    def _create_task(self, time_str):
        import subprocess
        task_name = f"ChroLensSorting_{time_str.replace(':', '')}"
        exe = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
        cmd = f'schtasks /Create /TN "{task_name}" /SC DAILY /TR "{exe}" /ST {time_str} /F'
        try:
            subprocess.run(cmd, shell=True, capture_output=True)
            self.log(f"建立排程：{time_str}")
        except Exception as e:
            self.log(f"排程失敗：{e}")
    
    def _delete_task(self, time_str):
        import subprocess
        task_name = f"ChroLensSorting_{time_str.replace(':', '')}"
        try:
            subprocess.run(f'schtasks /Delete /TN "{task_name}" /F', shell=True, capture_output=True)
            self.log(f"刪除排程：{time_str}")
        except:
            pass
    
    def check_for_updates(self):
        """檢查更新"""
        def check():
            try:
                version_mgr = VersionManager(CURRENT_VERSION, logger=self.log)
                info = version_mgr.check_for_updates()
                if info:
                    self.root.after(0, lambda: UpdateDialog(self.root, version_mgr, info, on_update_callback=self.root.quit))
                else:
                    self.root.after(0, lambda: NoUpdateDialog(self.root, CURRENT_VERSION))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("錯誤", f"檢查更新失敗：{e}"))
        
        threading.Thread(target=check, daemon=True).start()


# ============================================================================
# 程式進入點
# ============================================================================
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
    root = tb.Window(themename="darkly")
    app = AutoMoveApp(root)
    root.mainloop()
