"""
crop_tool - GUI v2.3

深色主题三栏布局，快捷键全流程操作，处理结果持久化保存 + 自由导出。
运行: python gui.py
"""

import os
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk

import config
import crop_tool
import level
import export
from utils import scan_images, read_image_pil, pil_to_cv2, cv2_to_pil, save_image_cv2

VERSION = "v2.3"
OUTPUT_SUBDIR = "crop_tool_已处理"

# ============================== 色彩体系 ==============================
BG_MAIN     = '#0f1117'
BG_PANEL    = '#171a23'
BG_CARD     = '#1e222e'
BG_HOVER    = '#2a2f3f'
BG_INPUT    = '#0b0d12'
BG_BANNER   = '#1a1e2b'
ACCENT      = '#6ea8fe'
ACCENT_HI   = '#93b4ff'
ACCENT_DIM  = '#2d3348'
TEXT_MAIN   = '#e4e7ef'
TEXT_DIM    = '#7a8290'
BORDER      = '#2b3040'
GREEN       = '#4ade80'
RED         = '#f87171'
YELLOW      = '#fbbf24'
CYAN        = '#38bdf8'
ORANGE      = '#fb923c'

# 字体
FONT_MAIN   = ('Microsoft YaHei UI', 9)
FONT_BOLD   = ('Microsoft YaHei UI', 9, 'bold')
FONT_SMALL  = ('Microsoft YaHei UI', 8)
FONT_TITLE  = ('Microsoft YaHei UI', 13, 'bold')
FONT_STATUS = ('Microsoft YaHei UI', 13, 'bold')
FONT_HDR    = ('Microsoft YaHei UI', 9, 'bold')
FONT_LOG    = ('Consolas', 9)


class ColoredLogRedirector:
    """stdout -> Text widget, 彩色高亮"""
    COLOR_MAP = [
        ('error',   ('[错误]', '[失败]'),          RED),
        ('success', ('[完成]', '[成功]', '[保存]'), GREEN),
        ('warn',    ('[提示]', '[警告]', '[已处理]'), YELLOW),
        ('info',    ('[模式]', '[预览]', '[检测]', '[加载]', '[导出]', '[输出]'), CYAN),
        ('skip',    ('[跳过]', '[重置]', '[退回]'), ORANGE),
    ]

    def __init__(self, text_widget):
        self.tw = text_widget
        self._buf = ''

    def write(self, text):
        if not text:
            return
        self.tw.after(0, self._append, text)

    def _append(self, text):
        self._buf += text
        while '\n' in self._buf:
            line, self._buf = self._buf.split('\n', 1)
            self._insert_line(line + '\n')
        if self._buf:
            self._insert_line(self._buf)
            self._buf = ''

    def _insert_line(self, line):
        tag = 'default'
        for tn, prefixes, _ in self.COLOR_MAP:
            if any(p in line for p in prefixes):
                tag = tn
                break
        self.tw.insert('end', line, tag)
        self.tw.see('end')

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"crop_tool {VERSION}")

        self.input_dir = None
        self.output_dir = None
        self.image_list = []
        self.current_idx = -1
        self.mode = None
        self.points = []
        self.canvas_scale = 1.0
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.original_img = None
        self.preview_result = None
        self.processed_set = set()
        self.result_paths = {}       # idx -> 已保存文件路径
        self.result_data = {}        # idx -> {'frame','ilbl','path'}
        self.running = False
        self.thumb_photos = []
        self.thumb_widgets = {}
        self.result_photos = {}      # idx -> PhotoImage (防 GC)
        self.current_photo = None
        self.all_buttons = []
        self.viewing_result = False

        self._setup_style()
        self._build_ui()
        sys.stdout = ColoredLogRedirector(self.log_text)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind('<KeyPress>', self._on_keypress)

        self._show_canvas_hint()
        self._update_status_bar()
        print("crop_tool " + VERSION)
        print("=" * 50)
        print("快捷键: Enter=保存  S=跳过  B=上一张  N=跳过文件夹  R=重画  1=裁剪  2=矫正  Esc=返回原图  Q=退出")

    # ============================== 样式 ==============================

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TButton', font=FONT_MAIN, foreground=TEXT_MAIN,
                        background=BG_CARD, borderwidth=0, focusthickness=0, padding=(12, 7))
        style.map('TButton',
                   background=[('active', BG_HOVER), ('pressed', ACCENT_DIM), ('disabled', BG_PANEL)],
                   foreground=[('disabled', TEXT_DIM)])

        style.configure('Accent.TButton', font=FONT_BOLD, foreground='#0b0d12',
                        background=ACCENT, borderwidth=0, focusthickness=0, padding=(12, 7))
        style.map('Accent.TButton',
                   background=[('active', ACCENT_HI), ('pressed', ACCENT_DIM)])

        style.configure('Export.TButton', font=FONT_MAIN, foreground=TEXT_MAIN,
                        background=ACCENT_DIM, borderwidth=0, focusthickness=0, padding=(14, 6))
        style.map('Export.TButton', background=[('active', BG_HOVER)])

        style.configure('TLabel', font=FONT_MAIN, foreground=TEXT_MAIN, background=BG_MAIN)
        style.configure('Dim.TLabel', foreground=TEXT_DIM, background=BG_MAIN)
        style.configure('Hdr.TLabel', font=FONT_HDR, foreground=TEXT_MAIN, background=BG_MAIN)
        style.configure('Title.TLabel', font=FONT_TITLE, foreground=ACCENT, background=BG_MAIN)

        style.configure('TFrame', background=BG_MAIN)
        style.configure('TLabelframe', background=BG_MAIN, foreground=TEXT_DIM, borderwidth=0)
        style.configure('TLabelframe.Label', background=BG_MAIN, foreground=TEXT_DIM, font=FONT_SMALL)
        style.configure('TPanedwindow', background=BG_MAIN)

        style.configure('Vertical.TScrollbar', background=BG_CARD, troughcolor=BG_MAIN,
                        borderwidth=0, arrowcolor=TEXT_DIM, width=10)
        style.map('Vertical.TScrollbar', background=[('active', ACCENT_DIM)])

    # ============================== 布局 ==============================

    def _build_ui(self):
        self.root.configure(bg=BG_MAIN)

        # === 顶部栏 ===
        top = ttk.Frame(self.root, padding=(14, 10, 14, 6))
        top.pack(fill='x')

        ttk.Label(top, text="crop_tool", style='Title.TLabel').pack(side='left')
        ttk.Label(top, text=f" {VERSION}", style='Dim.TLabel').pack(side='left', padx=(2, 0))

        self.btn_select = ttk.Button(top, text="  选择图片文件夹  ", style='Accent.TButton',
                                     command=self.select_folder)
        self.btn_select.pack(side='left', padx=(20, 0))

        self.folder_label = ttk.Label(top, text="未选择文件夹", style='Dim.TLabel')
        self.folder_label.pack(side='left', padx=(12, 0))

        self.btn_help = ttk.Button(top, text="  ? 帮助  ", command=self._show_help)
        self.btn_help.pack(side='right')

        # === 三栏 ===
        main = ttk.PanedWindow(self.root, orient='horizontal')
        main.pack(fill='both', expand=True, padx=10, pady=(0, 2))

        # 左：原图
        left = ttk.Frame(main)
        main.add(left, weight=0)
        ttk.Label(left, text="原图列表", style='Hdr.TLabel').pack(anchor='w', pady=(0, 5))
        lc = ttk.Frame(left)
        lc.pack(fill='both', expand=True)
        self.thumb_canvas = tk.Canvas(lc, width=200, bg=BG_PANEL, highlightthickness=0, bd=0)
        ts = ttk.Scrollbar(lc, orient='vertical', command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=ts.set)
        ts.pack(side='right', fill='y')
        self.thumb_canvas.pack(side='left', fill='both', expand=True)
        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=BG_PANEL, bd=0)
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor='nw')
        self.thumb_inner.bind('<Configure>',
            lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox('all')))
        self.thumb_canvas.bind('<MouseWheel>',
            lambda e: self.thumb_canvas.yview_scroll(int(-e.delta / 120), 'units'))
        self.thumb_status = ttk.Label(left, text="", style='Dim.TLabel', font=FONT_SMALL)
        self.thumb_status.pack(anchor='w', pady=(4, 0))

        # 中：操作区
        center = ttk.Frame(main)
        main.add(center, weight=1)

        mbar = ttk.Frame(center)
        mbar.pack(fill='x', pady=(0, 6))
        self.btn_crop = ttk.Button(mbar, text="  裁剪 [1]  ", command=lambda: self.set_mode('crop'))
        self.btn_crop.pack(side='left', padx=(0, 5))
        self.btn_level = ttk.Button(mbar, text="  矫正 [2]  ", command=lambda: self.set_mode('level'))
        self.btn_level.pack(side='left')

        # 醒目状态横幅
        self.status_bar = tk.Canvas(center, height=48, bg=BG_BANNER, highlightthickness=0, bd=0)
        self.status_bar.pack(fill='x', pady=(0, 6))
        self.status_bar.bind('<Configure>', lambda e: self._update_status_bar())

        cf = tk.Frame(center, bg=BORDER, bd=0)
        cf.pack(fill='both', expand=True)
        self.image_canvas = tk.Canvas(cf, bg=BG_INPUT, highlightthickness=0, bd=0)
        self.image_canvas.pack(fill='both', expand=True, padx=1, pady=1)
        self.image_canvas.bind('<Button-1>', self._on_canvas_click)
        self.image_canvas.bind('<Configure>', lambda e: self._on_canvas_resize())

        abar = ttk.Frame(center)
        abar.pack(fill='x', pady=(6, 0))
        self.btn_clear = ttk.Button(abar, text=" 重画 [R] ", command=self.clear_points)
        self.btn_clear.pack(side='left', padx=(0, 5))
        self.btn_save  = ttk.Button(abar, text=" 保存 [Enter] ", style='Accent.TButton', command=self.save_current)
        self.btn_save.pack(side='left', padx=(0, 5))
        self.btn_skip  = ttk.Button(abar, text=" 跳过 [S] ", command=self.skip_current)
        self.btn_skip.pack(side='left', padx=(0, 5))
        self.btn_prev  = ttk.Button(abar, text=" 上一张 [B] ", command=self.prev_image)
        self.btn_prev.pack(side='left', padx=(0, 5))
        self.btn_next  = ttk.Button(abar, text=" 下一张 [N] ", command=self.next_image)
        self.btn_next.pack(side='left')

        # 右：已处理
        right = ttk.Frame(main)
        main.add(right, weight=0)
        ttk.Label(right, text="已处理结果", style='Hdr.TLabel').pack(anchor='w', pady=(0, 5))
        rc = ttk.Frame(right)
        rc.pack(fill='both', expand=True)
        self.result_canvas = tk.Canvas(rc, width=200, bg=BG_PANEL, highlightthickness=0, bd=0)
        rs = ttk.Scrollbar(rc, orient='vertical', command=self.result_canvas.yview)
        self.result_canvas.configure(yscrollcommand=rs.set)
        rs.pack(side='right', fill='y')
        self.result_canvas.pack(side='left', fill='both', expand=True)
        self.result_inner = tk.Frame(self.result_canvas, bg=BG_PANEL, bd=0)
        self.result_canvas.create_window((0, 0), window=self.result_inner, anchor='nw')
        self.result_inner.bind('<Configure>',
            lambda e: self.result_canvas.configure(scrollregion=self.result_canvas.bbox('all')))
        self.result_canvas.bind('<MouseWheel>',
            lambda e: self.result_canvas.yview_scroll(int(-e.delta / 120), 'units'))
        self.result_status = ttk.Label(right, text="共 0 张", style='Dim.TLabel', font=FONT_SMALL)
        self.result_status.pack(anchor='w', pady=(4, 0))

        # === 底部：输出信息 + 导出 + 日志 ===
        bottom = ttk.Frame(self.root, padding=(14, 4, 14, 10))
        bottom.pack(fill='x')

        outrow = ttk.Frame(bottom)
        outrow.pack(fill='x', pady=(2, 8))
        ttk.Label(outrow, text="保存位置:", style='Dim.TLabel').pack(side='left')
        self.output_label = ttk.Label(outrow, text="（选择文件夹后自动生成）", style='Dim.TLabel', foreground=TEXT_DIM)
        self.output_label.pack(side='left', padx=(6, 0))
        self.btn_open = ttk.Button(outrow, text="打开保存文件夹", command=self.open_output_folder)
        self.btn_open.pack(side='left', padx=(12, 0))

        # 导出靠右对齐（左→右显示 PPT / PDF / Word）
        self.btn_word = ttk.Button(outrow, text=" Word ", style='Export.TButton', command=lambda: self.do_export('word'))
        self.btn_word.pack(side='right', padx=(4, 0))
        self.btn_pdf  = ttk.Button(outrow, text=" PDF ",  style='Export.TButton', command=lambda: self.do_export('pdf'))
        self.btn_pdf.pack(side='right', padx=(4, 0))
        self.btn_ppt  = ttk.Button(outrow, text=" PPT ",  style='Export.TButton', command=lambda: self.do_export('ppt'))
        self.btn_ppt.pack(side='right', padx=(4, 0))
        ttk.Label(outrow, text="导出:", style='Dim.TLabel').pack(side='right', padx=(0, 6))

        # 分割边框
        tk.Frame(bottom, bg=BORDER, height=1, bd=0).pack(fill='x', pady=(0, 8))

        logf = ttk.LabelFrame(bottom, text="日志", padding=(8, 5))
        logf.pack(fill='x')
        self.log_text = tk.Text(logf, height=3, font=FONT_LOG, wrap='word',
                                bg=BG_INPUT, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                                state='normal', highlightthickness=0, bd=0, padx=6, pady=4)
        ls = ttk.Scrollbar(logf, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=ls.set)
        ls.pack(side='right', fill='y')
        self.log_text.pack(fill='both', expand=True)
        self.log_text.tag_config('default', foreground=TEXT_MAIN)
        self.log_text.tag_config('error', foreground=RED)
        self.log_text.tag_config('success', foreground=GREEN)
        self.log_text.tag_config('warn', foreground=YELLOW)
        self.log_text.tag_config('info', foreground=CYAN)
        self.log_text.tag_config('skip', foreground=ORANGE)

        self.all_buttons = [
            self.btn_crop, self.btn_level, self.btn_clear,
            self.btn_save, self.btn_skip, self.btn_prev, self.btn_next,
            self.btn_ppt, self.btn_pdf, self.btn_word, self.btn_open,
        ]

    # ============================== 帮助 ==============================

    def _show_help(self):
        win = tk.Toplevel(self.root)
        win.title("使用帮助")
        win.configure(bg=BG_MAIN)
        win.geometry("580x600")
        win.transient(self.root)

        tk.Label(win, text="crop_tool 使用指南", font=FONT_TITLE, fg=ACCENT, bg=BG_MAIN
                 ).pack(anchor='w', padx=22, pady=(18, 10))

        txt = tk.Text(win, font=FONT_MAIN, wrap='word', bg=BG_INPUT, fg=TEXT_MAIN,
                      bd=0, highlightthickness=0, padx=16, pady=14, spacing3=5)
        txt.pack(fill='both', expand=True, padx=22, pady=(0, 12))

        sections = [
            ('基本流程', [
                '1. 点击顶部「选择图片文件夹」载入待处理图片',
                '2. 点击左侧缩略图选择要处理的图片',
                '3. 选择模式：裁剪 [1] 或 矫正 [2]',
                '4. 在画布上按上方提示条的指引点击标记点',
                '5. 按 Enter 保存，结果显示在右侧「已处理结果」',
            ]),
            ('裁剪模式 [1]', [
                '依次点击 4 个角点：左上 → 右上 → 右下 → 左下',
                '标记完成后按 Enter，透视矫正为标准尺寸并保存',
            ]),
            ('矫正模式 [2]', [
                '点击一条应为水平的线：先点左端，再点右端',
                '程序自动计算倾斜角度并旋转矫正',
            ]),
            ('快捷键', [
                'Enter = 保存当前        S = 跳过当前',
                'B = 上一张              N = 跳过整个文件夹',
                'R = 重画（清除标记点）',
                '1 = 裁剪模式            2 = 矫正模式',
                'Esc = 返回原图 / 清除标记点',
                'Q = 退出程序',
            ]),
            ('保存与导出', [
                '每张处理后立即保存到「保存位置」显示的文件夹',
                '文件已写入磁盘，关闭窗口不会丢失已处理的图片',
                '点击「打开保存文件夹」可快速定位成品',
                '全部处理完可在右下角导出为 PPT / PDF / Word',
            ]),
        ]
        for title, lines in sections:
            txt.insert('end', title + '\n', 'h')
            for ln in lines:
                txt.insert('end', '   ' + ln + '\n', 'b')
            txt.insert('end', '\n')
        txt.tag_config('h', foreground=ACCENT, font=FONT_BOLD, spacing1=8)
        txt.tag_config('b', foreground=TEXT_MAIN)
        txt.config(state='disabled')

        ttk.Button(win, text="  知道了  ", style='Accent.TButton',
                   command=win.destroy).pack(pady=(0, 18))

    # ============================== 状态横幅 ==============================

    def _update_status_bar(self):
        self.status_bar.delete('all')
        w = self.status_bar.winfo_width() or 700
        h = 48
        cy = h // 2

        if self.viewing_result:
            text = "预览结果中  —  点击画布 或 按 Esc 返回原图继续处理"
            color = ORANGE
        elif self.current_idx < 0:
            text = "请选择图片文件夹，然后点击左侧缩略图开始"
            color = TEXT_DIM
        elif self.mode is None:
            text = f"{self.current_idx+1}/{len(self.image_list)}  —  请先选择模式：按 1 裁剪 / 按 2 矫正"
            color = YELLOW
        elif self.mode == 'crop':
            if len(self.points) == 4:
                text = f"裁剪  {self.current_idx+1}/{len(self.image_list)}  —  4 个点已标记，按 Enter 保存 / R 重画"
            else:
                text = f"裁剪  {self.current_idx+1}/{len(self.image_list)}  —  依次点击 4 个角点（左上→右上→右下→左下），还需 {4-len(self.points)} 个"
            color = ACCENT
        else:  # level
            if self.preview_result is not None:
                text = f"矫正  {self.current_idx+1}/{len(self.image_list)}  —  已预览，按 Enter 保存 / R 重画"
            elif len(self.points) == 1:
                text = f"矫正  {self.current_idx+1}/{len(self.image_list)}  —  再点击水平线的右端点"
            else:
                text = f"矫正  {self.current_idx+1}/{len(self.image_list)}  —  点击一条应水平的线：先左端，再右端"
            color = ACCENT

        # 背景 + 左侧强调条
        self.status_bar.create_rectangle(0, 0, w, h, fill=BG_BANNER, outline=BORDER)
        self.status_bar.create_rectangle(0, 0, 5, h, fill=color, outline='')
        self.status_bar.create_text(18, cy, text=text, anchor='w', fill=color, font=FONT_STATUS)

    def _on_canvas_resize(self):
        if self.viewing_result:
            return
        if self.original_img is not None:
            self._display_cv2_image(self.preview_result if self.preview_result is not None else self.original_img)
        self._update_status_bar()

    # ============================== 快捷键 ==============================

    def _on_keypress(self, event):
        if event.state & 0x4:
            return
        key = event.keysym.lower()
        char = event.char.lower()

        if key == 'escape':
            if self.viewing_result:
                self._exit_result_preview()
            else:
                self.clear_points()
        elif key == 'return':
            self.save_current()
        elif char == 's':
            self.skip_current()
        elif char == 'b':
            self.prev_image()
        elif char == 'n':
            self.skip_folder()
        elif char == 'r':
            self.clear_points()
        elif char == '1':
            self.set_mode('crop')
        elif char == '2':
            self.set_mode('level')
        elif char == 'q':
            self._on_close()

    # ============================== 文件夹与缩略图 ==============================

    def select_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if not folder:
            return

        self.input_dir = folder
        self.output_dir = str(Path(folder) / OUTPUT_SUBDIR)
        self.folder_label.config(text=folder)
        self.output_label.config(text=self.output_dir, foreground=CYAN)

        for w in self.thumb_inner.winfo_children():
            w.destroy()
        for w in self.result_inner.winfo_children():
            w.destroy()
        self.thumb_photos = []
        self.thumb_widgets = {}
        self.result_photos = {}
        self.result_data = {}
        self.result_paths = {}
        self.processed_set = set()
        self.current_idx = -1
        self.original_img = None
        self.image_canvas.delete('all')
        self.result_status.config(text="共 0 张")

        all_images = scan_images(folder)
        # 排除输出目录自身
        self.image_list = [img for img in all_images if OUTPUT_SUBDIR not in Path(img['path']).parts]

        if not self.image_list:
            print("  [提示] 所选文件夹中没有图片文件")
            self._show_canvas_hint()
            self._update_status_bar()
            return

        print(f"  [加载] 共找到 {len(self.image_list)} 张图片")
        print(f"  [输出] 处理后的图片将保存到: {self.output_dir}")
        self._load_thumbnails()

    def _load_thumbnails(self):
        def worker():
            for idx, img_info in enumerate(self.image_list):
                try:
                    pil_img = read_image_pil(img_info['path'])
                    pil_img.thumbnail(config.THUMBNAIL_SIZE)
                    self.root.after(0, lambda i=idx, p=pil_img: self._add_thumbnail(i, p))
                except Exception as e:
                    print(f"  [失败] 缩略图: {img_info['name']} - {e}")
            self.root.after(0, lambda: print("  [完成] 缩略图加载完毕，按 1=裁剪 或 2=矫正 开始"))

        threading.Thread(target=worker, daemon=True).start()

    def _add_thumbnail(self, idx, pil_img):
        photo = ImageTk.PhotoImage(pil_img)
        self.thumb_photos.append(photo)

        frame = tk.Frame(self.thumb_inner, bg=BG_PANEL, bd=0, highlightthickness=2,
                         highlightbackground=BORDER, highlightcolor=ACCENT)
        frame.grid(row=idx, column=0, sticky='ew', padx=4, pady=4)

        ilbl = tk.Label(frame, image=photo, bg=BG_CARD, bd=0)
        ilbl.pack(padx=3, pady=(3, 0))

        is_proc = idx in self.processed_set
        name = self.image_list[idx]['name']
        nlbl = tk.Label(frame, text=(("✓ " if is_proc else "") + name), font=FONT_SMALL, bg=BG_PANEL,
                        fg=(GREEN if is_proc else TEXT_DIM), bd=0, wraplength=180)
        nlbl.pack(padx=3, pady=(1, 3))

        for w in [frame, ilbl, nlbl]:
            w.bind('<Button-1>', lambda e, i=idx: self._show_image(i))
            w.bind('<Enter>', lambda e, i=idx: self.thumb_widgets[i].config(
                highlightbackground=(ACCENT if i == self.current_idx else ACCENT_DIM)))
            w.bind('<Leave>', lambda e, i=idx: self.thumb_widgets[i].config(
                highlightbackground=(ACCENT if i == self.current_idx else BORDER)))

        self.thumb_widgets[idx] = frame
        self._update_thumb_status()

    def _update_thumb_status(self):
        self.thumb_status.config(text=f"共 {len(self.image_list)} 张 | 已处理 {len(self.processed_set)} 张")

    # ============================== 图片显示 ==============================

    def _show_canvas_hint(self):
        self.image_canvas.delete('all')
        self.image_canvas.create_text(
            self.image_canvas.winfo_width() // 2 or 400,
            self.image_canvas.winfo_height() // 2 or 300,
            text="请选择图片文件夹并点击缩略图", fill=TEXT_DIM, font=FONT_MAIN)

    def _show_image(self, idx):
        if idx < 0 or idx >= len(self.image_list):
            return
        if self.viewing_result:
            self._exit_result_preview(silent=True)

        self.current_idx = idx
        self.points = []
        self.preview_result = None

        img_info = self.image_list[idx]
        print(f"  [{idx + 1}/{len(self.image_list)}] {img_info['name']}")

        try:
            pil_img = read_image_pil(img_info['path'])
            self.original_img = pil_to_cv2(pil_img)
            self._display_cv2_image(self.original_img)
        except Exception as e:
            print(f"  [错误] 加载失败: {e}")
            return

        for i, w in self.thumb_widgets.items():
            w.config(highlightbackground=(ACCENT if i == idx else BORDER))

        if idx in self.processed_set:
            print("  [已处理] 此图已处理过，可重新操作覆盖")

        if idx in self.thumb_widgets:
            self.thumb_canvas.update_idletasks()
            y = self.thumb_widgets[idx].winfo_y()
            self.thumb_canvas.yview_moveto(max(0, y - 30) / max(1, self.thumb_inner.winfo_reqheight()))

        self._update_status_bar()

    def _display_cv2_image(self, cv2_img):
        pil_img = cv2_to_pil(cv2_img)
        h, w = cv2_img.shape[:2]
        cw = self.image_canvas.winfo_width()
        ch = self.image_canvas.winfo_height()
        if cw < 10: cw = 800
        if ch < 10: ch = 600

        scale = min(cw / w, ch / h, 1.0)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        self.canvas_scale = scale
        self.display_offset_x = max(0, (cw - dw) // 2)
        self.display_offset_y = max(0, (ch - dh) // 2)

        pil_disp = pil_img.resize((dw, dh), Image.LANCZOS)
        self.current_photo = ImageTk.PhotoImage(pil_disp)
        self.image_canvas.delete('all')
        self.image_canvas.create_image(self.display_offset_x, self.display_offset_y,
                                       anchor='nw', image=self.current_photo)
        if self.points:
            self._draw_overlay()

    # ============================== 鼠标 ==============================

    def _on_canvas_click(self, event):
        if self.viewing_result:
            self._exit_result_preview()
            return
        if self.mode is None:
            print("  [提示] 请先选择模式 (1=裁剪 2=矫正)")
            return
        if self.original_img is None:
            return
        if self.preview_result is not None:
            return

        max_pts = 4 if self.mode == 'crop' else 2
        if len(self.points) >= max_pts:
            return

        self.points.append((event.x, event.y))
        self._draw_overlay()

        if self.mode == 'crop' and len(self.points) == 4:
            print("  [提示] 4个点已标记，按 Enter 保存，R 重画")
        elif self.mode == 'level' and len(self.points) == 2:
            self._show_level_preview()

        self._update_status_bar()

    def _draw_overlay(self):
        self.image_canvas.delete('overlay')
        for i, pt in enumerate(self.points):
            self.image_canvas.create_oval(pt[0]-6, pt[1]-6, pt[0]+6, pt[1]+6,
                                          fill=RED, outline='white', width=2, tags='overlay')
            if i > 0:
                prev = self.points[i-1]
                self.image_canvas.create_line(prev[0], prev[1], pt[0], pt[1],
                                              fill=GREEN, width=2, tags='overlay')
        if self.mode == 'crop' and len(self.points) == 4:
            self.image_canvas.create_line(self.points[3][0], self.points[3][1],
                                          self.points[0][0], self.points[0][1],
                                          fill=GREEN, width=2, tags='overlay')

    def _canvas_to_image_point(self, pt):
        return ((pt[0] - self.display_offset_x) / self.canvas_scale,
                (pt[1] - self.display_offset_y) / self.canvas_scale)

    def _show_level_preview(self):
        pa = self._canvas_to_image_point(self.points[0])
        pb = self._canvas_to_image_point(self.points[1])
        print(f"  [检测] 倾斜角度: {level.get_angle(pa, pb):.2f} 度")
        self.preview_result = level.apply_level(self.original_img, pa, pb)
        self._display_cv2_image(self.preview_result)
        print("  [预览] 矫正结果已预览，Enter 保存，R 重画")
        self._update_status_bar()

    # ============================== 操作 ==============================

    def set_mode(self, mode):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        self.mode = mode
        self.points = []
        self.preview_result = None

        if mode == 'crop':
            self.btn_crop.configure(style='Accent.TButton')
            self.btn_level.configure(style='TButton')
            print("  [模式] 裁剪 - 点击4个角点(左上→右上→右下→左下)，Enter 保存")
        else:
            self.btn_level.configure(style='Accent.TButton')
            self.btn_crop.configure(style='TButton')
            print("  [模式] 矫正 - 点击2个点(水平线左端→右端)，自动预览")

        if self.original_img is not None:
            self._display_cv2_image(self.original_img)
        self._update_status_bar()

    def clear_points(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
            return
        self.points = []
        self.preview_result = None
        if self.original_img is not None:
            self._display_cv2_image(self.original_img)
        print("  [重置] 已清除标记点")
        self._update_status_bar()

    def _compute_result(self):
        """根据当前模式与标记点计算处理结果，无有效标记返回 None"""
        if self.mode == 'crop':
            if len(self.points) != 4:
                print("  [提示] 请先点击4个角点")
                return None
            pts = [self._canvas_to_image_point(p) for p in self.points]
            return crop_tool.apply_crop(self.original_img, pts)
        elif self.mode == 'level':
            if self.preview_result is not None:
                return self.preview_result
            if len(self.points) == 2:
                pa = self._canvas_to_image_point(self.points[0])
                pb = self._canvas_to_image_point(self.points[1])
                return level.apply_level(self.original_img, pa, pb)
            print("  [提示] 请先点击2个点")
            return None
        return None

    def _save_result(self, result):
        """保存结果到输出目录并更新缩略图/状态。返回保存路径。"""
        img_info = self.image_list[self.current_idx]
        stem = Path(img_info['path']).stem
        sub = img_info['subfolder']
        out_dir = Path(self.output_dir) / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{stem}.png"
        save_image_cv2(result, out_path)

        self.processed_set.add(self.current_idx)
        self.result_paths[self.current_idx] = str(out_path)
        self._mark_thumb_processed(self.current_idx)
        self._upsert_result_thumbnail(self.current_idx, str(out_path))
        self._update_thumb_status()
        return out_path

    def save_current(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx < 0:
            print("  [提示] 请先选择图片")
            return
        if self.mode is None:
            print("  [提示] 请先选择模式 (1=裁剪 2=矫正)")
            return

        result = self._compute_result()
        if result is None:
            return

        out_path = self._save_result(result)
        print(f"  [保存] 已保存: {out_path.name}")

        # 清除当前标记，避免在最后一张重复按 Enter 造成重复保存
        self.points = []
        self.preview_result = None
        self.next_image()

    def skip_current(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx < 0:
            print("  [提示] 请先选择图片")
            return

        out_path = self._save_result(self.original_img)
        print(f"  [跳过] 原样保存: {out_path.name}")

        self.points = []
        self.preview_result = None
        self.next_image()

    def skip_folder(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx < 0:
            print("  [提示] 请先选择图片")
            return
        cur_sub = self.image_list[self.current_idx]['subfolder']
        idx = self.current_idx
        while idx < len(self.image_list) and self.image_list[idx]['subfolder'] == cur_sub:
            idx += 1
        if idx < len(self.image_list):
            print(f"  [跳过] 文件夹 [{cur_sub}]")
            self._show_image(idx)
        else:
            print("  [完成] 已是最后一个文件夹")

    def _mark_thumb_processed(self, idx):
        if idx in self.thumb_widgets:
            for child in self.thumb_widgets[idx].winfo_children():
                if isinstance(child, tk.Label) and child.cget('text'):
                    t = child.cget('text')
                    if not t.startswith('✓ '):
                        child.config(text='✓ ' + t, fg=GREEN)

    def _upsert_result_thumbnail(self, idx, img_path):
        """新增或更新已处理结果缩略图（按原图 idx 去重）"""
        try:
            pil_img = read_image_pil(img_path)
            pil_img.thumbnail(config.THUMBNAIL_SIZE)
            photo = ImageTk.PhotoImage(pil_img)
            self.result_photos[idx] = photo

            if idx in self.result_data:
                # 更新现有缩略图
                data = self.result_data[idx]
                data['ilbl'].config(image=photo)
                data['path'] = img_path
                return

            row = len(self.result_data)
            frame = tk.Frame(self.result_inner, bg=BG_PANEL, bd=0, highlightthickness=2,
                             highlightbackground=BORDER, highlightcolor=GREEN)
            frame.grid(row=row, column=0, sticky='ew', padx=4, pady=4)
            ilbl = tk.Label(frame, image=photo, bg=BG_CARD, bd=0)
            ilbl.pack(padx=3, pady=(3, 0))
            nlbl = tk.Label(frame, text=Path(img_path).name, font=FONT_SMALL,
                            bg=BG_PANEL, fg=GREEN, bd=0, wraplength=180)
            nlbl.pack(padx=3, pady=(1, 3))

            for w in [frame, ilbl, nlbl]:
                w.bind('<Button-1>', lambda e, i=idx: self._preview_result(i))
                w.bind('<Enter>', lambda e, f=frame: f.config(highlightbackground=ACCENT_DIM))
                w.bind('<Leave>', lambda e, f=frame: f.config(highlightbackground=BORDER))

            self.result_data[idx] = {'frame': frame, 'ilbl': ilbl, 'path': img_path}
            self.result_status.config(text=f"共 {len(self.result_data)} 张")
        except Exception as e:
            print(f"  [失败] 结果缩略图: {e}")

    def _preview_result(self, idx):
        """点击右侧结果 -> 主画布预览处理后的图"""
        path = self.result_data.get(idx, {}).get('path')
        if not path:
            return
        try:
            img = pil_to_cv2(read_image_pil(path))
            self.viewing_result = True
            self.preview_result = None
            self.image_canvas.delete('all')
            self._render_static(img)
            print(f"  [预览] 查看处理后结果: {Path(path).name}")
            self._update_status_bar()
        except Exception as e:
            print(f"  [错误] 预览失败: {e}")

    def _render_static(self, cv2_img):
        """仅渲染图片，不涉及标记点（用于结果预览）"""
        pil_img = cv2_to_pil(cv2_img)
        h, w = cv2_img.shape[:2]
        cw = self.image_canvas.winfo_width() or 800
        ch = self.image_canvas.winfo_height() or 600
        scale = min(cw / w, ch / h, 1.0)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        ox, oy = max(0, (cw - dw) // 2), max(0, (ch - dh) // 2)
        self.current_photo = ImageTk.PhotoImage(pil_img.resize((dw, dh), Image.LANCZOS))
        self.image_canvas.delete('all')
        self.image_canvas.create_image(ox, oy, anchor='nw', image=self.current_photo)

    def _exit_result_preview(self, silent=False):
        if not self.viewing_result:
            return
        self.viewing_result = False
        self.preview_result = None
        if self.original_img is not None and self.current_idx >= 0:
            self._display_cv2_image(self.original_img)
        if not silent:
            print("  [退回] 已返回原图")
        self._update_status_bar()

    def prev_image(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx > 0:
            self._show_image(self.current_idx - 1)
        else:
            print("  [提示] 已经是第一张")

    def next_image(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx < len(self.image_list) - 1:
            self._show_image(self.current_idx + 1)
        else:
            print("  [完成] 已到最后一张图片")
            self._update_status_bar()

    # ============================== 导出 / 打开文件夹 ==============================

    def open_output_folder(self):
        if not self.output_dir or not Path(self.output_dir).exists():
            print("  [提示] 还没有已保存的图片")
            return
        try:
            os.startfile(self.output_dir)
        except Exception as e:
            print(f"  [错误] 打开文件夹失败: {e}")

    def do_export(self, fmt):
        if not self.output_dir or not Path(self.output_dir).exists():
            print("  [提示] 还没有处理过的图片，请先裁剪或矫正")
            return
        has = any(f.lower().endswith('.png')
                  for _, _, files in os.walk(self.output_dir) for f in files)
        if not has:
            print("  [提示] 还没有处理过的图片，请先裁剪或矫正")
            return

        out_dir = filedialog.askdirectory(title="选择导出位置")
        if not out_dir:
            return

        fmt_name = {'ppt': 'PPT', 'pdf': 'PDF', 'word': 'Word'}[fmt]

        def worker():
            self.running = True
            self.root.after(0, self._disable_buttons)
            try:
                print(f"  [导出] {fmt_name} -> {out_dir}")
                if fmt == 'ppt':
                    export.export_ppt(self.output_dir, out_dir)
                elif fmt == 'pdf':
                    export.export_pdf(self.output_dir, out_dir)
                elif fmt == 'word':
                    export.export_word(self.output_dir, out_dir)
            except Exception as e:
                print(f"  [错误] {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.running = False
                self.root.after(0, self._enable_buttons)

        threading.Thread(target=worker, daemon=True).start()

    # ============================== 工具 ==============================

    def _disable_buttons(self):
        for b in self.all_buttons:
            b.config(state='disabled')

    def _enable_buttons(self):
        for b in self.all_buttons:
            b.config(state='normal')

    def _on_close(self):
        if self.processed_set:
            ok = messagebox.askokcancel(
                "退出确认",
                f"已处理 {len(self.processed_set)} 张图片，已自动保存到:\n\n{self.output_dir}\n\n"
                f"文件已保存到磁盘，退出不会丢失。确定退出吗？")
            if not ok:
                return
        self.root.destroy()


def main():
    root = tk.Tk()
    root.title(f"crop_tool {VERSION}")
    root.geometry("1300x820")
    root.minsize(1040, 680)
    root.configure(bg=BG_MAIN)

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
