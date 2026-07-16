"""
图片裁剪矫正与导出工具 - GUI 界面

使用 tkinter 创建简易操作界面，普通用户无需命令行即可使用。
所有操作的日志输出显示在界面底部的日志区。

裁剪和矫正操作会打开 OpenCV 交互窗口，用户在其中用鼠标操作。
格式转换已内置到裁剪/矫正流程中，无需单独操作。

运行: python gui.py
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

import config

VERSION = "v1.0"


class StdoutRedirector:
    """将 stdout 重定向到 tkinter Text 控件（线程安全）"""

    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, text):
        if text:
            # 使用 after 调度到主线程，确保线程安全
            self.text_widget.after(0, self._append, text)

    def _append(self, text):
        self.text_widget.insert('end', text)
        self.text_widget.see('end')

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"图片裁剪矫正与导出工具 {VERSION}")
        self.root.resizable(False, False)
        self.buttons = []
        self.running = False

        # 确保数据目录存在
        for d in [config.SOURCE_DIR, config.CROPPED_DIR,
                  config.LEVELED_DIR, config.EXPORT_DIR]:
            d.mkdir(parents=True, exist_ok=True)

        self._build_ui()

        # 重定向 stdout 到日志区
        sys.stdout = StdoutRedirector(self.log_text)

        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 打印欢迎信息
        print("图片裁剪矫正与导出工具 " + VERSION)
        print("=" * 50)
        print("使用说明：")
        print("  1. 将图片按文件夹分类放入 [源文件] 目录")
        print("  2. 点击 [图片透视裁剪] 或 [图片水平矫正] 处理图片")
        print("  3. 处理完成后点击 [导出PPT/PDF/Word] 生成文档")
        print("  格式转换已内置，无需单独操作")
        print("=" * 50)

    def _build_ui(self):
        # === 标题区 ===
        title_frame = ttk.Frame(self.root, padding=(15, 10))
        title_frame.pack(fill='x')
        ttk.Label(title_frame, text=f"图片裁剪矫正与导出工具 {VERSION}",
                  font=('', 14, 'bold')).pack()

        # === 路径信息区 ===
        path_frame = ttk.LabelFrame(self.root, text="路径", padding=(15, 8))
        path_frame.pack(fill='x', padx=15, pady=(0, 8))

        paths = [
            ("源文件:", config.SOURCE_DIR),
            ("裁剪后:", config.CROPPED_DIR),
            ("导出至:", config.EXPORT_DIR),
        ]
        for i, (label, path) in enumerate(paths):
            ttk.Label(path_frame, text=label, width=8).grid(
                row=i, column=0, sticky='w', pady=2)
            ttk.Label(path_frame, text=str(path)).grid(
                row=i, column=1, sticky='w', padx=(0, 10), pady=2)
            if i == 0:
                btn = ttk.Button(path_frame, text="打开文件夹",
                                 command=self._open_source_dir)
                btn.grid(row=i, column=2, pady=2)

        # === 操作按钮区 ===
        btn_frame = ttk.LabelFrame(self.root, text="操作", padding=(15, 10))
        btn_frame.pack(fill='x', padx=15, pady=(0, 8))

        # 第一行：裁剪、矫正
        row1 = ttk.Frame(btn_frame)
        row1.pack(fill='x', pady=(0, 5))
        btn_crop = ttk.Button(row1, text="图片透视裁剪", width=18,
                              command=lambda: self._run(self._do_crop, "图片透视裁剪"))
        btn_crop.pack(side='left', padx=(0, 8))
        btn_level = ttk.Button(row1, text="图片水平矫正", width=18,
                               command=lambda: self._run(self._do_level, "图片水平矫正"))
        btn_level.pack(side='left')

        # 第二行：对账检查
        btn_check = ttk.Button(btn_frame, text="文件夹对账检查", width=18,
                               command=lambda: self._run(self._do_check, "文件夹对账检查"))
        btn_check.pack(fill='x', pady=(0, 5))

        # 第三行：导出
        row3 = ttk.Frame(btn_frame)
        row3.pack(fill='x')
        btn_ppt = ttk.Button(row3, text="导出PPT", width=10,
                             command=lambda: self._run(self._do_ppt, "导出PPT"))
        btn_ppt.pack(side='left', padx=(0, 5))
        btn_pdf = ttk.Button(row3, text="导出PDF", width=10,
                             command=lambda: self._run(self._do_pdf, "导出PDF"))
        btn_pdf.pack(side='left', padx=(0, 5))
        btn_word = ttk.Button(row3, text="导出Word", width=10,
                              command=lambda: self._run(self._do_word, "导出Word"))
        btn_word.pack(side='left')

        self.buttons = [btn_crop, btn_level, btn_check,
                        btn_ppt, btn_pdf, btn_word]

        # === 日志区 ===
        log_frame = ttk.LabelFrame(self.root, text="日志输出", padding=(5, 5))
        log_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=15, width=68,
            font=('Consolas', 9), state='normal',
            wrap='word'
        )
        self.log_text.pack(fill='both', expand=True)

    # === 操作执行函数 ===
    def _do_crop(self):
        import crop_tool
        crop_tool.process_images()

    def _do_level(self):
        import level
        level.process_images()

    def _do_check(self):
        import check_folders
        check_folders.check_folders()

    def _do_ppt(self):
        import export
        export.export_ppt()

    def _do_pdf(self):
        import export
        export.export_pdf()

    def _do_word(self):
        import export
        export.export_word()

    # === 线程执行器 ===
    def _run(self, func, name):
        if self.running:
            print("  [提示] 请等待当前操作完成...")
            return

        def worker():
            self.running = True
            # 禁用所有按钮（主线程调度）
            self.root.after(0, self._disable_buttons)
            try:
                print(f"\n{'=' * 50}")
                print(f"  开始: {name}")
                print(f"{'=' * 50}")
                func()
                print(f"\n  [{name}] 执行完毕！")
            except Exception as e:
                print(f"\n  [错误] {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.running = False
                self.root.after(0, self._enable_buttons)

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _disable_buttons(self):
        for btn in self.buttons:
            btn.config(state='disabled')

    def _enable_buttons(self):
        for btn in self.buttons:
            btn.config(state='normal')

    def _open_source_dir(self):
        try:
            os.startfile(str(config.SOURCE_DIR))
        except Exception as e:
            print(f"  [错误] 无法打开文件夹: {e}")

    def _on_close(self):
        try:
            import cv2
            cv2.destroyAllWindows()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    # 居中显示窗口
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
