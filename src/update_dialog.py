# -*- coding: utf-8 -*-
"""
版本資訊對話框 - ChroLens_Sorting
顯示當前版本、更新日誌和檢查更新
"""

import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox, scrolledtext
import threading


class UpdateDialog(tb.Toplevel):
    """更新對話框"""
    
    def __init__(self, parent, version_manager, update_info, on_update_callback=None):
        super().__init__(parent)
        
        self.parent = parent
        self.version_manager = version_manager
        self.update_info = update_info
        self.on_update_callback = on_update_callback
        
        self.title("發現新版本")
        self.geometry("550x500")
        self.resizable(False, False)
        
        # 置中顯示
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        self.transient(parent)
        self.grab_set()
        
        self._create_ui()
    
    def _create_ui(self):
        """創建 UI"""
        main_frame = tb.Frame(self, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # 標題
        title_label = tb.Label(
            main_frame,
            text="發現新版本",
            font=("微軟正黑體", 16, "bold"),
            bootstyle="success"
        )
        title_label.pack(pady=(0, 15))
        
        # 版本資訊
        info_frame = tb.Labelframe(main_frame, text="版本資訊", padding=15)
        info_frame.pack(fill=X, pady=(0, 15))
        
        current_frame = tb.Frame(info_frame)
        current_frame.pack(fill=X, pady=5)
        tb.Label(current_frame, text="目前版本：", width=10, anchor=W).pack(side=LEFT)
        tb.Label(current_frame, text=f"v{self.version_manager.current_version}", 
                font=("微軟正黑體", 10, "bold")).pack(side=LEFT)
        
        latest_frame = tb.Frame(info_frame)
        latest_frame.pack(fill=X, pady=5)
        tb.Label(latest_frame, text="最新版本：", width=10, anchor=W).pack(side=LEFT)
        tb.Label(latest_frame, text=f"v{self.update_info['version']}", 
                font=("微軟正黑體", 10, "bold"), bootstyle="success").pack(side=LEFT)
        
        # 更新說明
        notes_frame = tb.Labelframe(main_frame, text="更新說明", padding=15)
        notes_frame.pack(fill=BOTH, expand=YES, pady=(0, 15))
        
        self.notes_text = scrolledtext.ScrolledText(
            notes_frame,
            wrap=tk.WORD,
            font=("微軟正黑體", 9),
            height=10
        )
        self.notes_text.pack(fill=BOTH, expand=YES)
        self.notes_text.insert("1.0", self.update_info.get('release_notes', '無更新說明'))
        self.notes_text.config(state=tk.DISABLED)
        
        # 進度區域（初始隱藏）
        self.progress_frame = tb.Labelframe(main_frame, text="更新進度", padding=10)
        
        self.progress_label = tb.Label(self.progress_frame, text="準備下載...")
        self.progress_label.pack(pady=(0, 5))
        
        self.progress_bar = tb.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=450,
            bootstyle="success"
        )
        self.progress_bar.pack(pady=(0, 5))
        
        self.progress_detail = tb.Label(self.progress_frame, text="", bootstyle="secondary")
        self.progress_detail.pack()
        
        # 按鈕
        button_frame = tb.Frame(main_frame)
        button_frame.pack(fill=X, pady=(10, 0))
        
        self.update_btn = tb.Button(
            button_frame,
            text="立即更新",
            bootstyle="success",
            width=15,
            command=self._start_update
        )
        self.update_btn.pack(side=LEFT, padx=5)
        
        tb.Button(
            button_frame,
            text="稍後提醒",
            bootstyle="secondary",
            width=15,
            command=self.destroy
        ).pack(side=RIGHT, padx=5)
    
    def _start_update(self):
        """開始更新"""
        result = messagebox.askyesno(
            "確認更新",
            f"即將更新到 v{self.update_info['version']}\n\n更新完成後程式將自動重啟。\n\n確定要更新嗎？",
            parent=self
        )
        
        if not result:
            return
        
        self.update_btn.config(state=DISABLED)
        self.progress_frame.pack(fill=X, pady=(0, 10), before=self.winfo_children()[0].winfo_children()[-1])
        
        threading.Thread(target=self._perform_update, daemon=True).start()
    
    def _perform_update(self):
        """執行更新"""
        try:
            # 下載
            self.after(0, lambda: self.progress_label.config(text="階段 1/3: 下載更新"))
            
            def progress_callback(downloaded, total):
                if total > 0:
                    percent = (downloaded / total) * 40
                    self.after(0, lambda p=percent: self.progress_bar.config(value=p))
                    
                    downloaded_mb = downloaded / (1024 * 1024)
                    total_mb = total / (1024 * 1024)
                    self.after(0, lambda d=downloaded_mb, t=total_mb: 
                              self.progress_detail.config(text=f"已下載: {d:.2f}MB / {t:.2f}MB"))
            
            zip_path = self.version_manager.download_update(
                self.update_info['download_url'],
                progress_callback
            )
            
            if not zip_path:
                raise Exception("下載失敗")
            
            # 解壓縮
            self.after(0, lambda: self.progress_bar.config(value=40))
            self.after(0, lambda: self.progress_label.config(text="階段 2/3: 解壓縮"))
            self.after(0, lambda: self.progress_detail.config(text="正在解壓縮..."))
            
            import time
            for i in range(40, 70, 5):
                self.after(0, lambda p=i: self.progress_bar.config(value=p))
                time.sleep(0.1)
            
            extract_dir = self.version_manager.extract_update(zip_path)
            
            if not extract_dir:
                raise Exception("解壓縮失敗")
            
            # 應用更新
            self.after(0, lambda: self.progress_bar.config(value=70))
            self.after(0, lambda: self.progress_label.config(text="階段 3/3: 安裝更新"))
            self.after(0, lambda: self.progress_detail.config(text="正在準備更新..."))
            self.after(0, lambda: self.progress_bar.config(value=80))
            
            success = self.version_manager.apply_update(extract_dir, restart_after=True)
            
            if success:
                self.after(0, lambda: self.progress_bar.config(value=100))
                self.after(0, lambda: self.progress_detail.config(text="更新完成!"))
                self.after(0, self._show_success)
            else:
                raise Exception("應用更新失敗")
                
        except Exception as e:
            self.after(0, lambda err=str(e): self._show_error(err))
    
    def _show_success(self):
        """顯示成功"""
        self.progress_bar.config(value=100)
        self.progress_label.config(text="更新完成!")
        
        messagebox.showinfo(
            "更新完成",
            "更新已成功完成！\n\n程式即將重新啟動。",
            parent=self
        )
        
        if self.on_update_callback:
            self.on_update_callback()
        
        self.destroy()
    
    def _show_error(self, error_msg):
        """顯示錯誤"""
        self.progress_bar.config(bootstyle="danger")
        self.progress_label.config(text="更新失敗")
        self.progress_detail.config(text=f"錯誤: {error_msg}")
        self.update_btn.config(state=NORMAL)
        
        messagebox.showerror(
            "更新失敗",
            f"更新過程中發生錯誤：\n\n{error_msg}\n\n請稍後再試。",
            parent=self
        )


class NoUpdateDialog(tb.Toplevel):
    """無更新對話框"""
    
    def __init__(self, parent, current_version):
        super().__init__(parent)
        
        self.title("版本資訊")
        self.geometry("400x250")
        self.resizable(False, False)
        
        # 置中
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
        
        self.transient(parent)
        self.grab_set()
        
        main_frame = tb.Frame(self, padding=30)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # 標題
        tb.Label(
            main_frame,
            text="ChroLens_Sorting",
            font=("微軟正黑體", 16, "bold"),
            bootstyle="primary"
        ).pack(pady=(0, 20))
        
        # 版本
        tb.Label(
            main_frame,
            text=f"版本 v{current_version}",
            font=("微軟正黑體", 12)
        ).pack(pady=5)
        
        # 狀態
        tb.Label(
            main_frame,
            text="目前已是最新版本",
            font=("微軟正黑體", 11),
            bootstyle="success"
        ).pack(pady=20)
        
        # 關閉按鈕
        tb.Button(
            main_frame,
            text="確定",
            bootstyle="primary",
            width=15,
            command=self.destroy
        ).pack(pady=(20, 0))
