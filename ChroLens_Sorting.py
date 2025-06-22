# ────────────── 參數/變數說明區塊 ──────────────
# text= 顯示在按鈕或標籤上的文字
# side= 元件對齊位置（LEFT=左, RIGHT=右, TOP=上, BOTTOM=下）
# anchor= 對齊點（'w'=左對齊, 'e'=右對齊, 'center'=置中）
# padx / pady = 元件與其他元件或邊界的水平/垂直間距
# font= 字型設定，例如 ('微軟正黑體', 11)
# insert(位置, 值)= 插入預設文字
# pack(side=..., padx=..., pady=...) = 佈局設定
# Combobox= 下拉選單，values=可選擇的值列表
# Text= 文字框，可顯示日誌
# Entry= 單行輸入框
# BooleanVar / StringVar= 綁定變數
# filedialog.askdirectory() = 彈出資料夾選取視窗
# Progressbar= 進度條小工具
# ScrollableFrame= 自訂可滾動的框架（往下看）
# ────────────────────────────────────────

# row 0: 上方操作列（列出清單、移動、下拉選單、延遲/自動移動/自動關閉）
# row 1: 副檔名欄位 1~5
# row 2: 副檔名欄位 6~10
# row 3: 目的資料夾欄位（依副檔名數量動態產生）
# row 4: 來源資料夾選擇（含移出路徑、存檔按鈕）
# row 5: 日誌視窗
# row 6: 進度條

import os
import shutil
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
import tkinter as tk
import json

SETTINGS_FILE = "settings.json"

class AutoMoveApp:
    def __init__(self, root):
        self.tip = None
        self.root = root
        self.root.title("ChroLens_Sorting1.0")
        try:
            self.root.iconbitmap("法師貓貓.ico")
        except Exception as e:
            print(f"無法載入icon: {e}")
        self.style = tb.Style("darkly")
        self.font = ('微軟正黑體', 11)
        self.extension_entries = []
        self.dest_entries = []
        self.kind_var = tb.StringVar(value="10")
        self.move_delay_var = tb.StringVar(value="0")
        self.auto_close_var = tb.StringVar(value="0")

        # row 0: 上方操作列
        top_frame = tb.Frame(self.root)
        top_frame.pack(pady=5, anchor='w', padx=10, fill='x')
        tb.Button(top_frame, text="列出清單", command=self.list_files).pack(side=LEFT, padx=5)
        tb.Button(top_frame, text="移動", command=self.move_files).pack(side=LEFT, padx=5)
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

        # row 3: 副檔名與目的資料夾欄位
        self.dest_frame = tb.Frame(self.root)
        self.dest_frame.pack(pady=5, anchor='w', padx=10)

        # row 4: 來源資料夾
        source_row = tb.Frame(self.root)
        source_row.pack(pady=5, anchor='w', padx=10)
        self.source_entry = tb.Entry(source_row, width=28, font=self.font)
        self.source_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        self.source_entry.pack(side=LEFT)
        tb.Button(source_row, text="移出路徑", command=self.select_source_folder, bootstyle="dark").pack(side=LEFT, padx=5)
        tb.Button(source_row, text="帶入副檔名", command=self.fill_extensions_from_log, bootstyle="info").pack(side=LEFT, padx=5)
        tb.Button(source_row, text="存檔", command=self.save_settings, bootstyle="warning").pack(side=LEFT, padx=5)

        # row 6: 日誌視窗
        self.log_display = tb.Text(self.root, height=30, width=48, font=self.font, wrap='word')
        self.log_display.pack(pady=10, padx=10)
        self.log_display.config(xscrollcommand=lambda *args: None)

        # row 7: 進度條
        self.progress = tb.Progressbar(self.root, orient='horizontal', mode='determinate', length=660)
        self.progress.pack(pady=(0, 10))

        self.update_dynamic_fields()
        self.load_settings()
        # 啟動時自動移動倒數
        try:
            delay = int(self.move_delay_var.get())
        except ValueError:
            delay = 0
        if delay > 0:
            self.countdown("自動移動", delay, self.move_files)

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
            entry_ext = tb.Entry(row_dest, width=5, font=self.font)
            entry_ext.pack(side=LEFT, padx=(0, 5))
            entry_ext.bind("<ButtonPress-1>", lambda e, idx=i: self.start_drag(e, idx, "ext"))
            entry_ext.bind("<B1-Motion>", self.do_drag)
            entry_ext.bind("<ButtonRelease-1>", self.stop_drag)
            self.extension_entries.append(entry_ext)
            entry_dest = tb.Entry(row_dest, width=34, font=self.font)
            entry_dest.insert(0, "")
            entry_dest.pack(side=LEFT)
            entry_dest.bind("<ButtonPress-1>", lambda e, idx=i: self.start_drag(e, idx, "dest"))
            entry_dest.bind("<B1-Motion>", self.do_drag)
            entry_dest.bind("<ButtonRelease-1>", self.stop_drag)
            self.dest_entries.append(entry_dest)
            btn = tb.Button(row_dest, text="移入路徑", command=lambda e=entry_dest: self.select_dest_folder(e))
            btn.pack(side=LEFT, padx=5)
        base_height = 420
        extra_height = max(0, (count - 1) * 45)
        self.root.geometry(f"720x{base_height + extra_height}")

    def select_source_folder(self):
        folder = filedialog.askdirectory(initialdir=self.source_entry.get())
        if folder:
            self.source_entry.delete(0, 'end')
            self.source_entry.insert(0, folder)
            self.log(f"選擇移出路徑：{folder}")
            self.save_settings()

    def select_dest_folder(self, entry):
        folder = filedialog.askdirectory(initialdir=entry.get())
        if folder:
            entry.delete(0, 'end')
            entry.insert(0, folder)
            self.log(f"選擇移入路徑：{folder}")
            self.save_settings()

    def list_files(self):
        path = self.source_entry.get()
        extensions = [e.get().strip() for e in self.extension_entries]
        if not os.path.isdir(path):
            self.log("來源路徑無效")
            return
        if all(not ext for ext in extensions):
            all_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            ext_count = {}
            for f in all_files:
                _, ext = os.path.splitext(f)
                if ext:
                    ext_count[ext] = ext_count.get(ext, 0) + 1
                else:
                    ext_count["(無副檔名)"] = ext_count.get("(無副檔名)", 0) + 1
            if not all_files:
                self.log(f"{path} 中沒有找到任何檔案")
                return
            self.log(f"在 {path} 找到以下檔案：")
            total_size = 0
            for idx, f in enumerate(all_files, 1):
                full = os.path.join(path, f)
                size = os.path.getsize(full)
                total_size += size
                self.log(f"{idx}－{self.format_size(size)}－{f}")
            self.log(f"共找到 {len(all_files)} 個檔案，總容量 {self.format_size(total_size)}")
            for ext, count in sorted(ext_count.items()):
                self.log(f"{ext}={count}個檔案")
        else:
            all_files = []
            ext_count = {ext: 0 for ext in extensions if ext}
            for ext in extensions:
                if not ext:
                    continue
                files = [f for f in os.listdir(path) if f.endswith(ext)]
                all_files += files
                ext_count[ext] += len(files)
            if not all_files:
                self.log(f"{path} 中沒有找到符合副檔名的檔案")
                return
            self.log(f"在 {path} 找到以下檔案：")
            total_size = 0
            for idx, f in enumerate(all_files, 1):
                full = os.path.join(path, f)
                size = os.path.getsize(full)
                total_size += size
                self.log(f"{idx}－{self.format_size(size)}－{f}")
            self.log(f"共找到 {len(all_files)} 個檔案，總容量 {self.format_size(total_size)}")
            for ext, count in ext_count.items():
                self.log(f"{ext}={count}個檔案")

    def move_files(self):
        src = self.source_entry.get()
        extensions = [e.get().strip() for e in self.extension_entries]
        destinations = [e.get().strip() for e in self.dest_entries]
        all_files = []
        ext_dst_map = {}
        for ext, dst in zip(extensions, destinations):
            if ext and dst:
                ext_dst_map[ext] = dst
                all_files += [f for f in os.listdir(src) if f.endswith(ext)]
        total = len(all_files)
        self.progress['maximum'] = total
        self.progress['value'] = 0
        moved = failed = 0
        for idx, f in enumerate(all_files, 1):
            ext = os.path.splitext(f)[1]
            dst = ext_dst_map.get(ext)
            if not dst:
                continue
            try:
                shutil.move(os.path.join(src, f), os.path.join(dst, f))
                self.log(f"{idx}－成功移動：{f}")
                moved += 1
            except Exception as e:
                self.log(f"{idx}－移動失敗：{f}（錯誤：{e}）")
                failed += 1
            self.progress['value'] = idx
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

    def fill_extensions_from_log(self):
        log_text = self.log_display.get("1.0", "end")
        import re
        ext_list = re.findall(r"(\.[a-zA-Z0-9]+)=\d+個檔案", log_text)
        if not ext_list:
            self.log("未在日誌中找到副檔名統計，請先執行『列出清單』")
            return
        current_exts = set(e.get().strip() for e in self.extension_entries if e.get().strip())
        new_exts = [ext for ext in ext_list if ext not in current_exts]
        filled = 0
        for entry in self.extension_entries:
            if not entry.get().strip() and filled < len(new_exts):
                entry.delete(0, "end")
                entry.insert(0, new_exts[filled])
                filled += 1
        if filled < len(new_exts):
            remain = new_exts[filled:]
            self.log(f"還有{len(remain)}個副檔名未帶入：" + "、".join(remain))
        elif not new_exts:
            self.log("所有副檔名都已存在於欄位中，無需帶入")
        else:
            self.log("副檔名已自動帶入完畢")

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

if __name__ == "__main__":
    root = tb.Window(themename="darkly")
    app = AutoMoveApp(root)
    root.mainloop()
