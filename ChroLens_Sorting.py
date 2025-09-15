#中文：
#此工具為內部開發測試用，僅供參考，不保證其結果的準確性或適用性。**使用本工具所產生的一切後果，使用者需自行承擔。**開發者與公司對因使用此工具而造成的任何直接、間接或附帶損害，均不承擔任何責任。使用本工具即表示您已閱讀、理解並同意此免責聲明的所有條款。
#日本語：
#このツールは、社内での開発テスト用であり、あくまで参考として提供されるものです。その結果の正確性や適用性について、いかなる保証も行いません。本ツールの使用により生じるいかなる結果も、利用者自身の責任となります。開発者および会社は、本ツールの使用に起因する直接的、間接的、または付随的な損害について、一切の責任を負いません。本ツールを使用することにより、本免責事項のすべての条項を読み、理解し、同意したものとみなされます。
# row 0: 上方操作列（列出清單、移動、下拉選單、延遲/自動移動/自動關閉）
# row 1: 副檔名欄位 1~5
# row 2: 副檔名欄位 6~10
# row 3: 目的資料夾欄位（依副檔名數量動態產生）
# row 4: 來源資料夾選擇（含取出位置、存檔按鈕）
# row 5: 日誌視窗
# row 6: 進度條
#pyinstaller --noconsole --onefile --icon=umi_綠色.ico ChroLens_Sorting.py
import os
import shutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import tkinter as tk
import json
import datetime

SETTINGS_FILE = "settings.json"

class AutoMoveApp:
    def __init__(self, root):
        self.tip = None
        self.root = root
        self.root.title("ChroLens_Sorting1.0")
        try:
            self.root.iconbitmap("umi_綠色.ico")
        except Exception as e:
            print(f"無法載入icon: {e}")
        self.style = tb.Style("darkly")
        self.font = ('微軟正黑體', 11)
        self.extension_entries = []
        self.dest_entries = []
        self.kind_var = tb.StringVar(value="3")  # 預設顯示3個欄位
        self.move_delay_var = tb.StringVar(value="0")
        self.auto_close_var = tb.StringVar(value="0")

        # row 0: 上方操作列
        top_frame = tb.Frame(self.root)
        top_frame.pack(pady=5, anchor='w', padx=10, fill='x')
        tb.Button(top_frame, text="列出清單", command=self.list_files).pack(side=LEFT, padx=5)
        tb.Button(top_frame, text="移動", command=self.move_files, bootstyle="success").pack(side=LEFT, padx=5)
        kind_box = tb.Combobox(top_frame, textvariable=self.kind_var, width=3, values=[str(i) for i in range(1, 21)])
        kind_box.pack(side=LEFT, padx=(5, 0))
        kind_box.bind("<<ComboboxSelected>>", self.update_dynamic_fields)
        tb.Label(top_frame, text="種").pack(side=LEFT, padx=(5, 10))

        delay_frame = tb.Frame(top_frame)
        delay_frame.pack(side=LEFT, padx=10)
        self.move_delay_entry = tb.Entry(delay_frame, width=4, font=self.font, textvariable=self.move_delay_var)
        self.move_delay_entry.pack(side=LEFT)
        tb.Label(delay_frame, text="秒後自動移動").pack(side=LEFT)
        self.move_delay_entry.bind("<Enter>", lambda e: self.show_tip("不能高於關閉時間"))
        self.move_delay_entry.bind("<Leave>", lambda e: self.hide_tip())
        self.move_delay_entry.bind("<FocusOut>", self.validate_move_delay)
        self.move_delay_entry.bind("<KeyRelease>", self.validate_move_delay)
        self.close_entry = tb.Entry(delay_frame, width=4, font=self.font, textvariable=self.auto_close_var)
        self.close_entry.pack(side=LEFT, padx=(10, 0))
        tb.Label(delay_frame, text="秒後自動關閉").pack(side=LEFT)
        self.close_entry.bind("<Enter>", lambda e: self.show_tip("0 為不動作"))
        self.close_entry.bind("<Leave>", lambda e: self.hide_tip())
        self.close_entry.bind("<FocusOut>", self.validate_auto_close)
        self.close_entry.bind("<KeyRelease>", self.validate_auto_close)

        # row 0 下方新增獨立欄位 "0."
        zero_frame = tb.Frame(self.root)
        zero_frame.pack(anchor='w', padx=10, pady=(0, 0))
        tb.Label(zero_frame, text="0.", width=4, anchor='w').pack(side=LEFT, padx=(0, 5))
        self.all_var = tk.BooleanVar(value=False)
        all_check = tb.Checkbutton(zero_frame, variable=self.all_var, text="全部", bootstyle="success")
        all_check.pack(side=LEFT, padx=(0, 5))
        self.entry_all_path = tb.Entry(zero_frame, width=34, font=self.font)
        self.entry_all_path.pack(side=LEFT)
        tb.Button(zero_frame, text="存放位置", command=lambda: self.select_dest_folder(self.entry_all_path)).pack(side=LEFT, padx=5)
        # 右鍵清空存放位置欄位
        self.entry_all_path.bind("<Button-3>", lambda e: self.entry_all_path.delete(0, "end"))

        # row 1: 副檔名欄位 1~5
        self.ext_frame_1 = tb.Frame(self.root)
        self.ext_frame_1.pack(pady=5, anchor='w', padx=10)
        # row 2: 副檔名欄位 6~10
        self.ext_frame_2 = tb.Frame(self.root)
        self.ext_frame_2.pack(pady=5, anchor='w', padx=10)

        # row 3: 目的資料夾欄位（依副檔名數量動態產生）
        self.dest_frame = tb.Frame(self.root)
        self.dest_frame.pack(pady=5, anchor='w', padx=10)

        # row 4: 來源資料夾
        source_row = tb.Frame(self.root)
        source_row.pack(pady=5, anchor='w', padx=10)
        self.source_entry = tb.Entry(source_row, width=28, font=self.font)
        self.source_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        self.source_entry.pack(side=LEFT)
        tb.Button(source_row, text="取出位置", command=self.select_source_folder, bootstyle="danger").pack(side=LEFT, padx=5)
        # 刪除「帶入副檔名」按鈕，將「定時執行」功能移到這裡
        tb.Button(source_row, text="定時執行", command=self.open_schedule_window, bootstyle="info").pack(side=LEFT, padx=5)
        tb.Button(source_row, text="存檔", command=self.save_settings, bootstyle="warning").pack(side=LEFT, padx=5)

        # row 5: 日誌視窗
        self.log_display = tb.Text(self.root, height=10, width=70, font=self.font, wrap='word')  # ← 增加日誌顯示框寬度
        self.log_display.pack(pady=10, padx=10, fill='x')  # ← 讓日誌框更靠近主程式邊框
        self.log_display.config(xscrollcommand=lambda *args: None)

        # row 6: 進度條（移除進度條相關程式碼）
        # self.progress = tb.Progressbar(self.root, orient='horizontal', mode='determinate', length=660)
        # self.progress.pack(pady=(0, 10))

        self.update_dynamic_fields()
        self.load_settings()
        # 啟動時自動移動倒數（以當前來源路徑為主）
        try:
            delay = int(self.move_delay_var.get())
        except ValueError:
            delay = 0
        if delay > 0:
            self.countdown("自動移動", delay, self.move_files)
        # 首次開啟時自動列出清單，並刷新所有欄位帶入目前取出路徑內容
        self.list_files()

    def update_dynamic_fields(self, event=None):
        for widget in self.dest_frame.winfo_children():
            widget.destroy()
        self.extension_entries.clear()
        self.dest_entries.clear()
        try:
            count = int(self.kind_var.get())
        except ValueError:
            count = 10
        count = min(max(count, 1), 20)
        self._drag_data = {"widget": None, "index": None, "type": None, "tip": None}
        for i in range(count):
            row_dest = tb.Frame(self.dest_frame)
            row_dest.pack(anchor='w', pady=2)
            label_text = f"{i+1}.".ljust(4)
            tb.Label(row_dest, text=label_text, width=4, anchor='w').pack(side=LEFT, padx=(0, 5))
            entry_ext = tb.Entry(row_dest, width=12, font=self.font)
            entry_ext.pack(side=LEFT, padx=(0, 5))
            entry_ext.bind("<ButtonPress-1>", lambda e, idx=i: self.start_drag(e, idx, "ext"))
            entry_ext.bind("<B1-Motion>", self.do_drag)
            entry_ext.bind("<ButtonRelease-1>", self.stop_drag)
            entry_ext.bind("<Button-3>", lambda e, ent=entry_ext: ent.delete(0, "end"))
            self.extension_entries.append(entry_ext)
            entry_dest = tb.Entry(row_dest, width=34, font=self.font)
            entry_dest.insert(0, "")  # 不預設路徑
            entry_dest.pack(side=LEFT)
            entry_dest.bind("<ButtonPress-1>", lambda e, idx=i: self.start_drag(e, idx, "dest"))
            entry_dest.bind("<B1-Motion>", self.do_drag)
            entry_dest.bind("<ButtonRelease-1>", self.stop_drag)
            # 右鍵清空存放位置欄位
            entry_dest.bind("<Button-3>", lambda e, ent=entry_dest: ent.delete(0, "end"))
            self.dest_entries.append(entry_dest)
            btn = tb.Button(row_dest, text="存放位置", command=lambda e=entry_dest: self.select_dest_folder(e))
            btn.pack(side=LEFT, padx=5)
        # 自動調整視窗大小
        self.root.update_idletasks()
        self.root.geometry("")

    def select_source_folder(self):
        folder = filedialog.askdirectory(initialdir=self.source_entry.get())
        if folder:
            self.source_entry.delete(0, 'end')
            self.source_entry.insert(0, folder)
            self.log(f"選擇取出位置：{folder}")
            self.save_settings()

    def select_dest_folder(self, entry):
        folder = filedialog.askdirectory(initialdir=entry.get())
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)
            self.log(f"選擇存放位置：{folder}")
            self.save_settings()

    def list_files(self):
        path = self.source_entry.get()
        # 每次列出清單時刷新所有欄位並帶入目前取出路徑
        self.kind_var.set("3")
        self.update_dynamic_fields()
        for entry in self.extension_entries:
            entry.delete(0, "end")
        for entry in self.dest_entries:
            entry.delete(0, "end")
        # 預設將來源路徑帶入所有目的地欄位
        for entry in self.dest_entries:
            entry.insert(0, path)
        extensions = [e.get().strip() for e in self.extension_entries]
        if not os.path.isdir(path):
            self.log("來源路徑無效")
            return
        if all(not ext for ext in extensions):
            all_files = [f for f in os.listdir(path)]
            ext_count = {}
            folder_count = 0
            for f in all_files:
                full = os.path.join(path, f)
                if os.path.isdir(full):
                    folder_count += 1
                else:
                    _, ext = os.path.splitext(f)
                    if ext:
                        ext_count[ext] = ext_count.get(ext, 0) + 1
                    else:
                        ext_count["(無副檔名)"] = ext_count.get("(無副檔名)", 0) + 1
            if not all_files:
                self.log(f"{path} 中沒有找到任何檔案或資料夾")
                return
            self.log(f"在 {path} 找到以下檔案與資料夾：")
            total_size = 0
            for idx, f in enumerate(all_files, 1):
                full = os.path.join(path, f)
                if os.path.isdir(full):
                    self.log(f"{idx}－[資料夾]－{f}")
                else:
                    size = os.path.getsize(full)
                    total_size += size
                    self.log(f"{idx}－{self.format_size(size)}－{f}")
            self.log(f"共找到 {len(all_files)} 個項目，總容量 {self.format_size(total_size)}（不含資料夾）")
            for ext, count in sorted(ext_count.items()):
                self.log(f"{ext}={count}個檔案")
            if folder_count > 0:
                self.log(f"[資料夾]={folder_count}個")
            # 自動填入副檔名到欄位，並自動調整欄位數量
            ext_list = [ext for ext in ext_count if ext != "(無副檔名)"]
            if folder_count > 0:
                ext_list.append("[資料夾]")
            if ext_list:
                self.kind_var.set(str(len(ext_list)))
                self.update_dynamic_fields()
                # 重新帶入來源路徑到目的地欄位
                for entry in self.dest_entries:
                    entry.delete(0, "end")
                    entry.insert(0, path)
            for entry, ext in zip(self.extension_entries, ext_list):
                entry.delete(0, "end")
                entry.insert(0, ext)
        else:
            all_files = []
            ext_count = {ext: 0 for ext in extensions if ext}
            for ext in extensions:
                if not ext:
                    continue
                if ext == "[資料夾]":
                    files = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
                else:
                    files = [f for f in os.listdir(path) if f.endswith(ext)]
                all_files += files
                ext_count[ext] += len(files)
            if not all_files:
                self.log(f"{path} 中沒有找到符合條件的檔案或資料夾")
                return
            self.log(f"在 {path} 找到以下檔案與資料夾：")
            total_size = 0
            for idx, f in enumerate(all_files, 1):
                full = os.path.join(path, f)
                if os.path.isdir(full):
                    self.log(f"{idx}－[資料夾]－{f}")
                else:
                    size = os.path.getsize(full)
                    total_size += size
                    self.log(f"{idx}－{self.format_size(size)}－{f}")
            self.log(f"共找到 {len(all_files)} 個項目，總容量 {self.format_size(total_size)}（不含資料夾）")
            for ext, count in ext_count.items():
                self.log(f"{ext}={count}個檔案")

    def move_files(self):
        src = self.source_entry.get()
        extensions = [e.get().strip() for e in self.extension_entries]
        destinations = [e.get().strip() for e in self.dest_entries]
        all_files = os.listdir(src)
        moved_files = set()
        ext_dst_pairs = [(ext, dst) for ext, dst in zip(extensions, destinations) if ext and dst]
        idx = 1
        moved = failed = 0
        total = len(all_files)
        # self.progress["maximum"] = total  # 進度條已移除

        # 先依照副檔名/關鍵字欄位順序移動
        for ext, dst in ext_dst_pairs:
            if ext == "[資料夾]":
                files = [f for f in all_files if f not in moved_files and os.path.isdir(os.path.join(src, f))]
            elif ext.startswith("."):
                files = [f for f in all_files if f not in moved_files and f.endswith(ext) and os.path.isfile(os.path.join(src, f))]
            else:
                # 關鍵字搜尋時，檔案與資料夾都要比對名稱（不分大小寫）
                files = [f for f in all_files if f not in moved_files and ext.lower() in f.lower()]
            for f in files:
                try:
                    shutil.move(os.path.join(src, f), os.path.join(dst, f))
                    self.log(f"{idx}－成功移動：{f}")
                    moved += 1
                    moved_files.add(f)
                except Exception as e:
                    self.log(f"{idx}－移動失敗：{f}（錯誤：{e}）")
                    failed += 1
                idx += 1
                # self.progress["value"] = idx  # 進度條已移除
                self.root.update_idletasks()

        # 最後處理 0.欄位（全部），只有在有勾選時才執行
        if self.all_var.get():
            all_path = self.entry_all_path.get().strip()
            if all_path:
                remain_files = [f for f in all_files if f not in moved_files]
                for f in remain_files:
                    try:
                        shutil.move(os.path.join(src, f), os.path.join(all_path, f))
                        self.log(f"{idx}－ALL移動：{f}")
                        moved += 1
                    except Exception as e:
                        self.log(f"{idx}－ALL移動失敗：{f}（錯誤：{e}）")
                        failed += 1
                    idx += 1
                    # self.progress["value"] = idx  # 進度條已移除
                    self.root.update_idletasks()
        self.log(f"移動完成：{moved} 成功，{failed} 失敗")

        # 只處理自動關閉
        try:
            sec = int(self.auto_close_var.get())
        except ValueError:
            sec = 0
        if 0 < sec < 5:
            sec = 5
            self.auto_close_var.set("5")
        if sec > 0:
            self.countdown("自動關閉", sec, self.root.destroy)

    def countdown(self, mode, seconds, callback):
        # mode: "自動移動" or "自動關閉"
        if seconds <= 0:
            self.log(f"{mode}開始執行")
            callback()
            return
        self.log(f"{mode}倒數：{seconds} 秒")
        self.root.after(1000, lambda: self.countdown(mode, seconds - 1, callback))

    def move_files_once(self):
        # 執行一次移動，不再觸發自動移動
        self.move_delay_var.set("0")
        self.move_files()

    def show_tip(self, text):
        if self.tip is not None:
            return
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        self.tip = tw = tk.Toplevel(self.root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x+10}+{y+10}")
        label = tk.Label(tw, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("微軟正黑體", 10))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self):
        if self.tip:
            self.tip.destroy()
            self.tip = None

    def format_size(self, size):
        if size < 1024 * 1024:
            return f"{round(size / 1024)}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{round(size / (1024 * 1024), 1)}MB"
        else:
            return f"{round(size / (1024 * 1024 * 1024), 1)}GB"

    def log(self, message):
        self.log_display.insert('end', message + '\n')
        if int(self.log_display.index('end-1c').split('.')[0]) > 1000:
            self.log_display.delete("1.0", "2.0")
        self.log_display.see('end')

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.kind_var.set(data.get("kind_var", "10"))
            self.move_delay_var.set(data.get("move_delay_var", "0"))
            self.auto_close_var.set(data.get("auto_close_var", "0"))
            self.update_dynamic_fields()
            for entry, val in zip(self.extension_entries, data.get("extensions", [])):
                entry.delete(0, "end")
                entry.insert(0, val)
            for entry, val in zip(self.dest_entries, data.get("destinations", [])):
                entry.delete(0, "end")
                entry.insert(0, val)
            if "source" in data:
                self.source_entry.delete(0, "end")
                self.source_entry.insert(0, data["source"])
        except Exception as e:
            self.log(f"設定檔載入失敗：{e}")

    def save_settings(self):
        try:
            data = {
                "kind_var": self.kind_var.get(),
                "move_delay_var": self.move_delay_var.get(),
                "auto_close_var": self.auto_close_var.get(),
                "extensions": [e.get() for e in self.extension_entries],
                "destinations": [e.get() for e in self.dest_entries],
                "source": self.source_entry.get(),
            }
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"設定檔儲存失敗：{e}")

    def start_drag(self, event, idx, typ):
        self._drag_data["widget"] = event.widget
        self._drag_data["index"] = idx
        self._drag_data["type"] = typ
        value = event.widget.get()
        if value:
            self._drag_data["tip"] = tip = tk.Toplevel(self.root)
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            label = tk.Label(tip, text=value, background="#ffffe0", relief="solid", borderwidth=1, font=("微軟正黑體", 10))
            label.pack(ipadx=5, ipady=2)

    def do_drag(self, event):
        tip = self._drag_data.get("tip")
        if tip:
            tip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")

    def stop_drag(self, event):
        if self._drag_data["widget"] is None:
            return
        x, y = event.x_root, event.y_root
        entries = self.extension_entries if self._drag_data["type"] == "ext" else self.dest_entries
        target_idx = None
        for idx, entry in enumerate(entries):
            ex, ey, ew, eh = entry.winfo_rootx(), entry.winfo_rooty(), entry.winfo_width(), entry.winfo_height()
            if ex <= x <= ex+ew and ey <= y <= ey+eh:
                target_idx = idx
                break
        if target_idx is not None and target_idx != self._drag_data["index"]:
            src_entry = entries[self._drag_data["index"]]
            dst_entry = entries[target_idx]
            src_val = src_entry.get()
            dst_val = dst_entry.get()
            src_entry.delete(0, "end")
            src_entry.insert(0, dst_val)
            dst_entry.delete(0, "end")
            dst_entry.insert(0, src_val)
        if self._drag_data.get("tip"):
            self._drag_data["tip"].destroy()
        self._drag_data = {"widget": None, "index": None, "type": None, "tip": None}

    def validate_move_delay(self, event=None):
        try:
            move_delay = int(self.move_delay_var.get())
        except ValueError:
            move_delay = 0
        try:
            auto_close = int(self.auto_close_var.get())
        except ValueError:
            auto_close = 0
        # 自動移動不能大於自動關閉，且不能為負
        if move_delay < 0:
            move_delay = 0
            self.move_delay_var.set("0")
        if auto_close > 0 and move_delay > auto_close:
            self.move_delay_var.set(str(auto_close))
            self.log("自動移動秒數已自動修正為不高於自動關閉秒數")

    def validate_auto_close(self, event=None):
        try:
            move_delay = int(self.move_delay_var.get())
        except ValueError:
            move_delay = 0
        val = self.auto_close_var.get()
        try:
            num = int(val)
        except ValueError:
            num = 0
        if 0 < num < 5:
            num = 5
            self.auto_close_var.set("5")
        elif num < 0:
            num = 0
            self.auto_close_var.set("0")
        # 自動關閉不能小於自動移動
        if num > 0 and num < move_delay:
            self.auto_close_var.set(str(move_delay))
            self.log("自動關閉秒數已自動修正為不低於自動移動秒數")

    def open_schedule_window(self):
        SCHEDULE_FILE = "schedule_times.json"
        win = tb.Toplevel(self.root)
        win.title("定時執行設定")
        win.geometry("400x400")
        win.resizable(False, False)
        win.grab_set()
        try:
            win.iconbitmap("umi_綠色.ico")
        except Exception as e:
            print(f"無法載入icon: {e}")
        tb.Label(win, text="請設定執行時間 (24小時制)", font=("Microsoft JhengHei", 12)).pack(pady=(16, 8))

        # 時間選擇區
        time_frame = tb.Frame(win)
        time_frame.pack(pady=(0, 12))
        hour_var = tk.StringVar(value="09")
        minute_var = tk.StringVar(value="00")
        hour_box = tb.Combobox(time_frame, textvariable=hour_var, width=4, font=("Consolas", 13), values=[f"{i:02d}" for i in range(24)], justify="center", state="readonly")
        hour_box.pack(side=LEFT, padx=(0, 8))
        minute_box = tb.Combobox(time_frame, textvariable=minute_var, width=4, font=("Consolas", 13), values=[f"{i:02d}" for i in range(0, 60, 1)], justify="center", state="readonly")
        minute_box.pack(side=LEFT, padx=(0, 8))

        # 時間清單區（縮小框框寬度）
        tb.Label(win, text="已建立排程：", font=("微軟正黑體", 11)).pack(anchor='w', padx=14, pady=(0, 4))
        list_frame = tb.Frame(win)
        list_frame.pack(fill='both', expand=True, padx=14, pady=(0, 8))
        schedule_list = tk.Listbox(list_frame, height=1, font=("Consolas", 30), selectmode=tk.MULTIPLE, width=12)
        schedule_list.pack(side=LEFT, fill='y', expand=False)
        scrollbar = tb.Scrollbar(list_frame, orient="vertical", command=schedule_list.yview)
        scrollbar.pack(side=LEFT, fill='y')
        schedule_list.config(yscrollcommand=scrollbar.set)

        # 載入已儲存的排程
        def load_schedule():
            import json
            if os.path.exists(SCHEDULE_FILE):
                try:
                    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
                        times = json.load(f)
                    for t in times:
                        schedule_list.insert(tk.END, t)
                except Exception:
                    pass

        def save_schedule():
            import json
            times = list(schedule_list.get(0, tk.END))
            with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
                json.dump(times, f, ensure_ascii=False, indent=2)

        # 按鈕區
        btn_frame = tb.Frame(win)
        btn_frame.pack(pady=12)
        tb.Button(btn_frame, text="新增", command=lambda: add_time(), bootstyle="success", width=10).pack(side=LEFT, padx=12)
        tb.Button(btn_frame, text="移除", command=lambda: remove_time(), bootstyle="danger", width=10).pack(side=LEFT, padx=12)

        # 功能
        def add_time():
            val = f"{hour_var.get()}:{minute_var.get()}"
            if val not in schedule_list.get(0, tk.END):
                schedule_list.insert(tk.END, val)
                self.create_windows_task(val)
                self.log(f"已建立排程：{val}")
                save_schedule()
                # 1秒後自動開啟工作排程
                self.root.after(1000, lambda: os.system("control schedtasks"))

        def remove_time():
            sel = schedule_list.curselection()
            for idx in reversed(sel):
                self.delete_windows_task(schedule_list.get(idx))
                schedule_list.delete(idx)
            save_schedule()

        def check_schedule():
            now = datetime.datetime.now().strftime("%H:%M")
            for t in schedule_list.get(0, tk.END):
                if now == t:
                    self.move_files()
            win.after(1000 * 60, check_schedule)

        load_schedule()
        win.after(1000 * 60, check_schedule)

    def create_windows_task(self, time_str):
        import sys
        import subprocess
        script_path = os.path.abspath(sys.argv[0])
        task_name = f"ChroLensSorting_{time_str.replace(':','')}"
        cmd = f'schtasks /Create /TN "{task_name}" /SC DAILY /TR "{sys.executable} {script_path}" /ST {time_str} /F'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            self.log(f"建立排程失敗：{result.stderr.strip()}")

    def delete_windows_task(self, time_str):
        import subprocess
        task_name = f"ChroLensSorting_{time_str.replace(':','')}"
        cmd = f'schtasks /Delete /TN "{task_name}" /F'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            self.log(f"刪除排程失敗：{result.stderr.strip()}")

if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app = AutoMoveApp(root)
    root.mainloop()
