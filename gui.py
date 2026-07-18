"""
crop_tool - GUI v2.6

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

VERSION = "v2.6"
OUTPUT_SUBDIR = "crop_tool_已处理"

# ============================== 交互参数 ==============================
HANDLE_R    = 7       # 标记点句柄半径（画布像素）
HANDLE_HIT  = 12      # 命中拖拽的判定半径（画布像素）
ZOOM_MIN    = 0.2
ZOOM_MAX    = 8.0
ZOOM_STEP   = 1.25
LOUPE_SIZE  = 130     # 放大镜边长（画布像素）
LOUPE_ZOOM  = 4       # 放大倍数

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
FONT_LOG    = ('Consolas', 11)


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
        self.tw.config(state='normal')
        self.tw.insert('end', line, tag)
        self.tw.see('end')
        self.tw.config(state='disabled')

    def flush(self):
        pass


class Tooltip:
    """轻量悬停提示：鼠标停留在控件上时弹出深色小浮层。"""
    def __init__(self, widget, text, delay=450):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip = None
        self._after = None
        widget.bind('<Enter>', self._schedule, add='+')
        widget.bind('<Leave>', self._hide, add='+')
        widget.bind('<ButtonPress>', self._hide, add='+')

    def _schedule(self, _e=None):
        self._cancel()
        self._after = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after is not None:
            self.widget.after_cancel(self._after)
            self._after = None

    def _show(self):
        if self.tip is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.configure(bg=BORDER)
        tk.Label(self.tip, text=self.text, font=FONT_SMALL, justify='left',
                 bg=BG_CARD, fg=TEXT_MAIN, bd=0, padx=9, pady=6,
                 wraplength=300).pack(padx=1, pady=1)

    def _hide(self, _e=None):
        self._cancel()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class App:
    def __init__(self, root):
        self.root = root
        self.root.title(f"crop_tool {VERSION}")

        self.input_dir = None
        self.output_dir = None
        self.image_list = []
        self.current_idx = -1
        self.mode = None
        self.points = []              # 存原图坐标 (x, y)
        self.canvas_scale = 1.0       # 有效缩放 = fit_scale * user_zoom
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.fit_scale = 1.0
        self.user_zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.selected_point = -1      # 当前选中的标记点索引
        self.dragging_point = -1      # 正在拖拽的标记点索引
        self.panning = False
        self.space_held = False
        self._pan_start = None
        self.undo_stack = []
        self.redo_stack = []
        self.last_points = None       # (mode, [pts]) 记忆上一张
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
        self.session_outputs = set()  # 本次会话写入磁盘的成品路径（用于退出时可选删除）

        # 交互开关（可在动作条即时切换）
        self.auto_carry = tk.BooleanVar(value=False)  # 自动沿用上一张标记点（默认关）
        self.magnet = tk.BooleanVar(value=True)        # 裁剪角点磁性吸附（默认开）

        self._setup_style()
        self._build_ui()
        sys.stdout = ColoredLogRedirector(self.log_text)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind('<KeyPress>', self._on_keypress)
        self.root.bind('<KeyRelease-space>', self._on_space_release)

        self._show_canvas_hint()
        self._update_status_bar()
        print("crop_tool " + VERSION)
        print("=" * 50)
        print("快捷键: Enter=保存 S=跳过 B=上一张 N=跳过文件夹 R=重画 A=批量套用 P=粘贴点 D=自动框选")
        print("        1=裁剪 2=矫正 Ctrl+Z/Y=撤销/重做 方向键=微调 滚轮/+/-/0=缩放 空格拖拽=平移")

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

        # 醒目帮助按钮
        style.configure('Help.TButton', font=('Microsoft YaHei UI', 11, 'bold'),
                        foreground='#0b0d12', background=ORANGE,
                        borderwidth=0, focusthickness=0, padding=(16, 8))
        style.map('Help.TButton',
                   background=[('active', '#fdba74'), ('pressed', '#ea7c2b')])

        # 胶囊式开/关切换按钮
        style.configure('ToggleOn.TButton', font=FONT_BOLD, foreground='#0b0d12',
                        background=ACCENT, borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map('ToggleOn.TButton', background=[('active', ACCENT_HI), ('pressed', ACCENT_DIM)])
        style.configure('ToggleOff.TButton', font=FONT_MAIN, foreground=TEXT_DIM,
                        background=BG_CARD, borderwidth=0, focusthickness=0, padding=(12, 6))
        style.map('ToggleOff.TButton', background=[('active', BG_HOVER), ('pressed', ACCENT_DIM)])

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

        self.btn_help = ttk.Button(top, text="  ❓ 使用帮助  ", style='Help.TButton',
                                   command=self._show_help)
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
        self.image_canvas.bind('<B1-Motion>', self._on_canvas_drag)
        self.image_canvas.bind('<ButtonRelease-1>', self._on_canvas_release)
        self.image_canvas.bind('<Motion>', self._on_canvas_motion)
        self.image_canvas.bind('<Button-2>', self._on_pan_start)
        self.image_canvas.bind('<B2-Motion>', self._on_pan_move)
        self.image_canvas.bind('<MouseWheel>', self._on_canvas_wheel)
        self.image_canvas.bind('<Configure>', lambda e: self._on_canvas_resize())
        self.image_canvas.bind('<Leave>', lambda e: self._hide_loupe())

        # 放大镜浮层（默认隐藏，随光标显示）
        self.loupe = tk.Canvas(self.image_canvas, width=LOUPE_SIZE, height=LOUPE_SIZE,
                               bg=BG_INPUT, highlightthickness=1, highlightbackground=ACCENT, bd=0)
        self.loupe_photo = None

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
        self.btn_next.pack(side='left', padx=(0, 5))
        self.btn_apply = ttk.Button(abar, text=" 批量套用 [A] ", command=self.apply_to_folder)
        self.btn_apply.pack(side='left')
        self.btn_suggest = ttk.Button(abar, text=" 自动框选 [D] ", command=self.suggest_quad)
        self.btn_suggest.pack(side='left', padx=(5, 0))

        Tooltip(self.btn_clear, "清除当前标记点，重新点选")
        Tooltip(self.btn_save, "处理并保存当前图，自动跳到下一张未处理")
        Tooltip(self.btn_skip, "不处理当前图，跳到下一张未处理")
        Tooltip(self.btn_prev, "回到上一张")
        Tooltip(self.btn_next, "前往下一张")
        Tooltip(self.btn_apply, "把当前选区套用到本文件夹其余同机位图片")
        Tooltip(self.btn_suggest, "自动识别边框并摆好四角作为起点，再拖拽微调（仅当前图）")

        # 辅助开关独立一行，左对齐，任意宽度均完整可见
        tbar = ttk.Frame(center)
        tbar.pack(fill='x', pady=(6, 0))
        ttk.Label(tbar, text="辅助功能：", style='Dim.TLabel').pack(side='left', padx=(0, 8))
        self.btn_magnet = self._make_toggle(tbar, "自动吸边", self.magnet)
        self.btn_magnet.pack(side='left', padx=(0, 8))
        self.btn_carry = self._make_toggle(tbar, "沿用上张选区", self.auto_carry)
        self.btn_carry.pack(side='left', padx=(0, 8))
        Tooltip(self.btn_magnet, "落点自动吸附到附近真实边角，点不准也贴准（仅裁剪）")
        Tooltip(self.btn_carry, "开启后，切到下一张自动带入上一张选区作为起点")

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
        self.log_text = tk.Text(logf, height=4, font=FONT_LOG, wrap='word',
                                bg=BG_INPUT, fg=TEXT_MAIN,
                                state='disabled', highlightthickness=0, bd=0, padx=8, pady=6,
                                spacing1=2, spacing3=2)
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
            self.btn_save, self.btn_skip, self.btn_prev, self.btn_next, self.btn_apply,
            self.btn_suggest,
            self.btn_ppt, self.btn_pdf, self.btn_word, self.btn_open,
        ]

    # ============================== 开关 ==============================

    def _make_toggle(self, parent, label, var):
        """创建胶囊式开/关按钮，点击翻转 var 并刷新样式/文案。"""
        btn = ttk.Button(parent)
        btn.configure(command=lambda: self._toggle_var(btn, label, var))
        self._refresh_toggle(btn, label, var)
        return btn

    def _toggle_var(self, btn, label, var):
        var.set(not var.get())
        self._refresh_toggle(btn, label, var)

    def _refresh_toggle(self, btn, label, var):
        on = var.get()
        btn.configure(text=f" {label} · {'开' if on else '关'} ",
                      style='ToggleOn.TButton' if on else 'ToggleOff.TButton')

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
            ('精细编辑', [
                '标记点可直接拖拽微调，选中后可用方向键像素级移动（Shift 为 10px）',
                '滚轮缩放、空格或中键拖拽平移，配合放大镜精确点选',
                '开启「自动吸边」后，裁剪角点会自动吸附到附近真实角，点不准也能贴准',
                '按 D（或“自动框选”）自动摆好四角作起点，再拖拽微调（仅当前图）',
                '开启「沿用上张选区」后，切到下一张会自动带入上张选区作起点',
                '同机位连拍：标好一张后按 A 一键批量套用到本文件夹剩余图片',
                '按 P 可粘贴上一张的标记点作为起点，Ctrl+Z/Y 撤销/重做',
            ]),
            ('快捷键', [
                'Enter = 保存当前        S = 跳过当前',
                'B = 上一张              N = 跳过整个文件夹',
                'R = 重画（清除标记点）   A = 批量套用到本文件夹剩余',
                'P = 粘贴上次标记点       D = 自动框选（自动检测边框）',
                '1 = 裁剪模式            2 = 矫正模式',
                'Ctrl+Z = 撤销           Ctrl+Y = 重做',
                '方向键 = 微调选中点（Shift 为 10px）',
                '滚轮 = 缩放    + / - = 缩放    0 = 复位视图',
                '空格+拖拽 或 中键拖拽 = 平移画布',
                'Esc = 返回原图 / 清除标记点    Q = 退出程序',
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
                text = f"裁剪  {self.current_idx+1}/{len(self.image_list)}  —  4 个点已标记，可拖拽/方向键微调，Enter 保存 / A 套用整个文件夹 / R 重画"
            else:
                text = f"裁剪  {self.current_idx+1}/{len(self.image_list)}  —  依次点击 4 个角点（左上→右上→右下→左下），还需 {4-len(self.points)} 个"
            color = ACCENT
        else:  # level
            if self.preview_result is not None:
                text = f"矫正  {self.current_idx+1}/{len(self.image_list)}  —  已预览，可拖拽端点微调，Enter 保存 / A 套用整个文件夹 / R 重画"
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
        ctrl = bool(event.state & 0x4)
        shift = bool(event.state & 0x1)
        key = event.keysym.lower()
        char = event.char.lower()

        if ctrl:
            if key == 'z':
                self.redo() if shift else self.undo()
            elif key == 'y':
                self.redo()
            return

        if key in ('left', 'right', 'up', 'down'):
            self._nudge_selected(key, event.state)
            return
        if key == 'space':
            self.space_held = True
            return

        if key == 'escape':
            if self.viewing_result:
                self._exit_result_preview()
            else:
                self.clear_points()
        elif key == 'return':
            self.save_current()
        elif char in ('+', '='):
            self._apply_zoom(ZOOM_STEP, self._cx(), self._cy())
        elif char == '-':
            self._apply_zoom(1 / ZOOM_STEP, self._cx(), self._cy())
        elif char == '0':
            self._reset_view()
            self._redisplay_current()
            self._update_status_bar()
        elif char == 's':
            self.skip_current()
        elif char == 'b':
            self.prev_image()
        elif char == 'n':
            self.skip_folder()
        elif char == 'r':
            self.clear_points()
        elif char == 'a':
            self.apply_to_folder()
        elif char == 'p':
            self.paste_last_points()
        elif char == 'd':
            self.suggest_quad()
        elif char == '1':
            self.set_mode('crop')
        elif char == '2':
            self.set_mode('level')
        elif char == 'q':
            self._on_close()

    def _on_space_release(self, event):
        self.space_held = False
        self.panning = False
        self._pan_start = None

    def _cx(self):
        return (self.image_canvas.winfo_width() or 800) // 2

    def _cy(self):
        return (self.image_canvas.winfo_height() or 600) // 2

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
        self._restore_progress()
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

    def _restore_progress(self):
        """重开时扫描输出目录，恢复已处理状态与右侧结果。"""
        if not self.output_dir:
            return
        to_restore = []
        for idx, info in enumerate(self.image_list):
            out_path = Path(self.output_dir) / info['subfolder'] / f"{Path(info['path']).stem}.png"
            if out_path.exists():
                self.processed_set.add(idx)
                self.result_paths[idx] = str(out_path)
                to_restore.append((idx, str(out_path)))
        if to_restore:
            print(f"  [加载] 恢复已处理进度: {len(to_restore)} 张")
            for idx, p in to_restore:
                self.root.after(0, self._upsert_result_thumbnail, idx, p)

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
        self.selected_point = -1
        self.dragging_point = -1
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._reset_view()
        self._hide_loupe()

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

        # 自动沿用上一张标记点作为起点（同机位/相似构图）
        if (self.auto_carry.get() and self.last_points
                and self.original_img is not None):
            cmode, cpts = self.last_points
            if self.mode == cmode:
                self.points = list(cpts)
                if self.mode == 'level' and len(self.points) == 2:
                    self._show_level_preview()
                else:
                    self._draw_overlay()
                print("  [模式] 已自动沿用上张标记点，可拖拽微调")

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

        self.fit_scale = min(cw / w, ch / h, 1.0)
        scale = self.fit_scale * self.user_zoom
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        self.canvas_scale = scale
        self.display_offset_x = (cw - dw) // 2 + self.pan_x
        self.display_offset_y = (ch - dh) // 2 + self.pan_y

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
        if self.original_img is None:
            return

        # 空格 + 左键 = 平移
        if self.space_held:
            self.panning = True
            self._pan_start = (event.x, event.y, self.pan_x, self.pan_y)
            return

        # 命中已有标记点 -> 拖拽微调
        hit = self._hit_test_point(event.x, event.y)
        if hit >= 0:
            self._push_undo()
            self.dragging_point = hit
            self.selected_point = hit
            if self.mode == 'level' and self.preview_result is not None:
                self.preview_result = None
                self._display_cv2_image(self.original_img)
            self._draw_overlay()
            self._show_loupe(event.x, event.y)
            return

        if self.mode is None:
            print("  [提示] 请先选择模式 (1=裁剪 2=矫正)")
            return
        if self.preview_result is not None:
            return

        max_pts = 4 if self.mode == 'crop' else 2
        if len(self.points) >= max_pts:
            return

        self._push_undo()
        ix, iy = self._canvas_to_image_point((event.x, event.y))
        ix, iy = self._snap_point(ix, iy)
        self.points.append((ix, iy))
        self.selected_point = len(self.points) - 1
        self._draw_overlay()

        if self.mode == 'crop' and len(self.points) == 4:
            self._hide_loupe()
            print("  [提示] 4个点已标记，可拖拽微调，按 Enter 保存，R 重画")
        elif self.mode == 'level' and len(self.points) == 2:
            self._hide_loupe()
            self._show_level_preview()

        self._update_status_bar()

    def _on_canvas_drag(self, event):
        if self.panning:
            if self._pan_start:
                sx, sy, px, py = self._pan_start
                self.pan_x = px + (event.x - sx)
                self.pan_y = py + (event.y - sy)
                self._redisplay_current()
            return
        if self.dragging_point >= 0:
            self.points[self.dragging_point] = self._canvas_to_image_point((event.x, event.y))
            self._draw_overlay()
            self._show_loupe(event.x, event.y)

    def _on_canvas_release(self, event):
        if self.panning:
            self.panning = False
            self._pan_start = None
            return
        if self.dragging_point >= 0:
            di = self.dragging_point
            ix, iy = self.points[di]
            self.points[di] = self._snap_point(ix, iy)
            self.dragging_point = -1
            self._hide_loupe()
            self._draw_overlay()
            if self.mode == 'level' and len(self.points) == 2:
                self._show_level_preview()
            self._update_status_bar()

    def _on_canvas_motion(self, event):
        if self.viewing_result or self.original_img is None or self.mode is None:
            self._hide_loupe()
            return
        if self.dragging_point >= 0 or self.panning:
            return
        max_pts = 4 if self.mode == 'crop' else 2
        if len(self.points) < max_pts and self.preview_result is None:
            self._show_loupe(event.x, event.y)
        else:
            self._hide_loupe()

    def _on_pan_start(self, event):
        self._pan_start = (event.x, event.y, self.pan_x, self.pan_y)

    def _on_pan_move(self, event):
        if not self._pan_start:
            return
        sx, sy, px, py = self._pan_start
        self.pan_x = px + (event.x - sx)
        self.pan_y = py + (event.y - sy)
        self._redisplay_current()

    def _on_canvas_wheel(self, event):
        if self.viewing_result or self.original_img is None:
            return
        factor = ZOOM_STEP if event.delta > 0 else 1 / ZOOM_STEP
        self._apply_zoom(factor, event.x, event.y)

    def _apply_zoom(self, factor, cx, cy):
        if self.original_img is None:
            return
        new_zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.user_zoom * factor))
        if abs(new_zoom - self.user_zoom) < 1e-6:
            return
        # 以光标为锚点，保持锚点下的原图位置不动
        ix, iy = self._canvas_to_image_point((cx, cy))
        self.user_zoom = new_zoom
        h, w = self.original_img.shape[:2]
        cw = self.image_canvas.winfo_width() or 800
        ch = self.image_canvas.winfo_height() or 600
        scale = self.fit_scale * self.user_zoom
        dw, dh = int(w * scale), int(h * scale)
        self.pan_x = int(cx - ix * scale - (cw - dw) // 2)
        self.pan_y = int(cy - iy * scale - (ch - dh) // 2)
        self._redisplay_current()
        self._update_status_bar()

    def _reset_view(self):
        self.user_zoom = 1.0
        self.pan_x = 0
        self.pan_y = 0

    def _redisplay_current(self):
        if self.original_img is None:
            return
        img = self.preview_result if self.preview_result is not None else self.original_img
        self._display_cv2_image(img)

    def _hit_test_point(self, cx, cy):
        best, best_d = -1, HANDLE_HIT
        for i, p in enumerate(self.points):
            px, py = self._image_to_canvas_point(p)
            d = ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5
            if d <= best_d:
                best, best_d = i, d
        return best

    def _draw_overlay(self):
        self.image_canvas.delete('overlay')
        cpts = [self._image_to_canvas_point(p) for p in self.points]
        for i in range(1, len(cpts)):
            self.image_canvas.create_line(cpts[i-1][0], cpts[i-1][1], cpts[i][0], cpts[i][1],
                                          fill=GREEN, width=2, tags='overlay')
        if self.mode == 'crop' and len(cpts) == 4:
            self.image_canvas.create_line(cpts[3][0], cpts[3][1], cpts[0][0], cpts[0][1],
                                          fill=GREEN, width=2, tags='overlay')
        for i, (cx, cy) in enumerate(cpts):
            sel = (i == self.selected_point)
            r = HANDLE_R + (2 if sel else 0)
            self.image_canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                          fill=(YELLOW if sel else RED),
                                          outline='white', width=2, tags='overlay')
            self.image_canvas.create_text(cx, cy-r-8, text=str(i+1),
                                          fill='white', font=FONT_SMALL, tags='overlay')

    def _image_to_canvas_point(self, pt):
        return (pt[0] * self.canvas_scale + self.display_offset_x,
                pt[1] * self.canvas_scale + self.display_offset_y)

    def _canvas_to_image_point(self, pt):
        return ((pt[0] - self.display_offset_x) / self.canvas_scale,
                (pt[1] - self.display_offset_y) / self.canvas_scale)

    def _snap_point(self, ix, iy):
        """裁剪模式下开启磁吸时，将落点吸附到附近真实角点。"""
        if (self.mode == 'crop' and self.magnet.get()
                and self.original_img is not None):
            r = max(6, int(round(18 / self.canvas_scale)))
            return crop_tool.snap_corner(self.original_img, ix, iy, r)
        return (ix, iy)

    def _show_loupe(self, cx, cy):
        if self.original_img is None:
            return
        ix, iy = self._canvas_to_image_point((cx, cy))
        h, w = self.original_img.shape[:2]
        src = max(4, LOUPE_SIZE // LOUPE_ZOOM)   # 源区域边长（原图像素）
        x0 = int(ix - src / 2)
        y0 = int(iy - src / 2)
        x0 = max(0, min(x0, w - src)) if w > src else 0
        y0 = max(0, min(y0, h - src)) if h > src else 0
        crop = self.original_img[y0:y0 + src, x0:x0 + src]
        if crop.size == 0:
            self._hide_loupe()
            return
        pil = cv2_to_pil(crop).resize((LOUPE_SIZE, LOUPE_SIZE), Image.NEAREST)
        self.loupe_photo = ImageTk.PhotoImage(pil)
        self.loupe.delete('all')
        self.loupe.create_image(0, 0, anchor='nw', image=self.loupe_photo)
        rel_x = (ix - x0) / src * LOUPE_SIZE
        rel_y = (iy - y0) / src * LOUPE_SIZE
        self.loupe.create_line(rel_x, 0, rel_x, LOUPE_SIZE, fill=ACCENT, width=1)
        self.loupe.create_line(0, rel_y, LOUPE_SIZE, rel_y, fill=ACCENT, width=1)
        self.loupe.create_oval(rel_x-4, rel_y-4, rel_x+4, rel_y+4, outline=RED, width=2)
        # 定位：默认光标右下，靠近边缘时翻到对侧
        cw = self.image_canvas.winfo_width() or 800
        ch = self.image_canvas.winfo_height() or 600
        lx = cx + 20 if cx + 20 + LOUPE_SIZE <= cw else cx - 20 - LOUPE_SIZE
        ly = cy + 20 if cy + 20 + LOUPE_SIZE <= ch else cy - 20 - LOUPE_SIZE
        self.loupe.place(x=max(0, lx), y=max(0, ly))

    def _hide_loupe(self):
        if getattr(self, 'loupe', None) is not None:
            self.loupe.place_forget()

    def _show_level_preview(self):
        pa = self.points[0]
        pb = self.points[1]
        print(f"  [检测] 倾斜角度: {level.get_angle(pa, pb):.2f} 度")
        self.preview_result = level.apply_level(self.original_img, pa, pb)
        self._display_cv2_image(self.preview_result)
        print("  [预览] 矫正结果已预览，Enter 保存，R 重画")
        self._update_status_bar()

    # ============================== 撤销 / 重做 / 微调 ==============================

    def _push_undo(self):
        self.undo_stack.append(list(self.points))
        if len(self.undo_stack) > 50:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            print("  [提示] 没有可撤销的操作")
            return
        self.redo_stack.append(list(self.points))
        self.points = self.undo_stack.pop()
        self.selected_point = -1
        self._refresh_after_points_change()
        print("  [重置] 已撤销")

    def redo(self):
        if not self.redo_stack:
            print("  [提示] 没有可重做的操作")
            return
        self.undo_stack.append(list(self.points))
        self.points = self.redo_stack.pop()
        self.selected_point = -1
        self._refresh_after_points_change()
        print("  [重置] 已重做")

    def _refresh_after_points_change(self):
        self.preview_result = None
        if self.mode == 'level' and len(self.points) == 2:
            self._show_level_preview()
        else:
            self._redisplay_current()
        self._update_status_bar()

    def _nudge_selected(self, key, state):
        if self.selected_point < 0 or self.selected_point >= len(self.points):
            return
        step = 10 if (state & 0x1) else 1   # Shift = 10px
        dx = {'left': -step, 'right': step}.get(key, 0)
        dy = {'up': -step, 'down': step}.get(key, 0)
        if dx == 0 and dy == 0:
            return
        self._push_undo()
        x, y = self.points[self.selected_point]
        self.points[self.selected_point] = (x + dx, y + dy)
        if self.mode == 'level' and len(self.points) == 2:
            self.preview_result = None
            self._show_level_preview()
        else:
            self._draw_overlay()
        self._update_status_bar()

    # ============================== 操作 ==============================

    def set_mode(self, mode):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        self.mode = mode
        self.points = []
        self.preview_result = None
        self.selected_point = -1
        self.undo_stack.clear()
        self.redo_stack.clear()

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

    def suggest_quad(self):
        """一键建议四角：自动检测当前图最明显的四边形作为起点（可拖拽微调）。"""
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.original_img is None:
            print("  [提示] 请先选择图片")
            return
        if self.mode != 'crop':
            self.set_mode('crop')
        quad = crop_tool.detect_quad(self.original_img)
        if quad is None:
            print("  [提示] 未检测到明显四边形，请手动点选")
            return
        self._push_undo()
        self.points = list(quad)
        self.preview_result = None
        self.selected_point = -1
        self._redisplay_current()
        print("  [模式] 已建议四角，可拖拽微调，Enter 保存")
        self._update_status_bar()

    def clear_points(self):
        if self.viewing_result:
            self._exit_result_preview(silent=True)
            return
        if self.points:
            self._push_undo()
        self.points = []
        self.preview_result = None
        self.selected_point = -1
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
            return crop_tool.apply_crop(self.original_img, self.points)
        elif self.mode == 'level':
            if self.preview_result is not None:
                return self.preview_result
            if len(self.points) == 2:
                return level.apply_level(self.original_img, self.points[0], self.points[1])
            print("  [提示] 请先点击2个点")
            return None
        return None

    def _save_file_only(self, idx, result):
        """仅将结果写入磁盘，返回保存路径字符串（线程安全，不触碰 UI）。"""
        img_info = self.image_list[idx]
        stem = Path(img_info['path']).stem
        sub = img_info['subfolder']
        out_dir = Path(self.output_dir) / sub
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{stem}.png"
        save_image_cv2(result, out_path)
        self.session_outputs.add(str(out_path))
        return str(out_path)

    def _register_saved(self, idx, out_path):
        """登记已保存结果并更新缩略图/状态（须在主线程调用）。"""
        self.processed_set.add(idx)
        self.result_paths[idx] = out_path
        self._mark_thumb_processed(idx)
        self._upsert_result_thumbnail(idx, out_path)
        self._update_thumb_status()

    def _save_result(self, result):
        """保存当前图片结果并更新 UI。返回保存路径 Path。"""
        out_path = self._save_file_only(self.current_idx, result)
        self._register_saved(self.current_idx, out_path)
        return Path(out_path)

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

        # 记忆本次标记点，供下一张粘贴复用
        if self.points:
            self.last_points = (self.mode, list(self.points))

        # 清除当前标记，避免在最后一张重复按 Enter 造成重复保存
        self.points = []
        self.preview_result = None
        self.selected_point = -1
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._goto_next_unprocessed()

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
        self.selected_point = -1
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._goto_next_unprocessed()

    def apply_to_folder(self):
        """用当前标记点批量处理本子文件夹中从当前图起的所有图片（同机位场景）。"""
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.current_idx < 0 or self.original_img is None:
            print("  [提示] 请先选择图片")
            return
        if self.mode is None:
            print("  [提示] 请先选择模式 (1=裁剪 2=矫正)")
            return
        need = 4 if self.mode == 'crop' else 2
        if len(self.points) != need:
            print(f"  [提示] 请先标记 {need} 个点再套用")
            return
        if self.running:
            return

        cur_sub = self.image_list[self.current_idx]['subfolder']
        targets = [i for i in range(self.current_idx, len(self.image_list))
                   if self.image_list[i]['subfolder'] == cur_sub]
        if not targets:
            return

        already = sum(1 for i in targets if i in self.processed_set)
        msg = f"将用当前标记点处理文件夹 [{cur_sub}] 中的 {len(targets)} 张图片"
        if already:
            msg += f"\n其中 {already} 张已处理，将被覆盖"
        msg += "\n\n适用于同一机位连拍的照片，确定继续吗？"
        if not messagebox.askyesno("批量套用", msg):
            return

        mode = self.mode
        pts = list(self.points)

        def worker():
            self.running = True
            self.root.after(0, self._disable_buttons)
            ok, fail = 0, 0
            try:
                print(f"  [模式] 批量套用{'裁剪' if mode == 'crop' else '矫正'}到 [{cur_sub}] 共 {len(targets)} 张")
                for n, idx in enumerate(targets, 1):
                    info = self.image_list[idx]
                    try:
                        img = pil_to_cv2(read_image_pil(info['path']))
                        if mode == 'crop':
                            result = crop_tool.apply_crop(img, pts)
                        else:
                            result = level.apply_level(img, pts[0], pts[1])
                        out_path = self._save_file_only(idx, result)
                        self.root.after(0, self._register_saved, idx, out_path)
                        print(f"    {n}/{len(targets)}  [保存] {info['name']}")
                        ok += 1
                    except Exception as e:
                        print(f"    {n}/{len(targets)}  [失败] {info['name']} - {e}")
                        fail += 1
                print(f"  [完成] 批量套用完毕：成功 {ok} 张，失败 {fail} 张")
            finally:
                self.running = False
                self.root.after(0, self._enable_buttons)

        threading.Thread(target=worker, daemon=True).start()

    def paste_last_points(self):
        """粘贴上一张保存时使用的标记点作为起点（同机位场景）。"""
        if self.viewing_result:
            self._exit_result_preview(silent=True)
        if self.original_img is None:
            print("  [提示] 请先选择图片")
            return
        if not self.last_points:
            print("  [提示] 还没有可复用的标记点")
            return
        mode, pts = self.last_points
        if self.mode is None:
            self.set_mode(mode)
        elif self.mode != mode:
            print("  [提示] 当前模式与上次不一致，无法粘贴")
            return
        self._push_undo()
        self.points = list(pts)
        self.preview_result = None
        self.selected_point = -1
        print("  [模式] 已粘贴上次标记点，可拖拽微调")
        if self.mode == 'level' and len(self.points) == 2:
            self._show_level_preview()
        else:
            self._redisplay_current()
        self._update_status_bar()

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

    def _next_unprocessed(self, start):
        """从 start+1 向后找首个未处理索引，无则返回 -1。"""
        for i in range(start + 1, len(self.image_list)):
            if i not in self.processed_set:
                return i
        return -1

    def _goto_next_unprocessed(self):
        nxt = self._next_unprocessed(self.current_idx)
        if nxt >= 0:
            self._show_image(nxt)
        else:
            print("  [完成] 已到末尾，后面没有未处理的图了")
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
        if self.running:
            messagebox.showinfo("请稍候", "批量处理正在进行中，请等待完成后再退出。")
            return
        if not self.session_outputs:
            self.root.destroy()
            return
        choice = self._confirm_exit(len(self.session_outputs))
        if choice == 'cancel':
            return
        if choice == 'discard':
            self._delete_session_outputs()
        self.root.destroy()

    def _delete_session_outputs(self):
        """删除本次会话写入的成品，并清理变空的目录（不影响已有旧成品）。"""
        dirs = set()
        removed = 0
        for p in list(self.session_outputs):
            try:
                if os.path.exists(p):
                    os.remove(p)
                    removed += 1
                dirs.add(os.path.dirname(p))
            except Exception:
                pass
        # 清理变空的子目录与输出根目录
        for d in sorted(dirs, key=len, reverse=True):
            try:
                if os.path.isdir(d) and not os.listdir(d):
                    os.rmdir(d)
            except Exception:
                pass
        try:
            if (self.output_dir and os.path.isdir(self.output_dir)
                    and not os.listdir(self.output_dir)):
                os.rmdir(self.output_dir)
        except Exception:
            pass
        print(f"  [重置] 已删除本次处理的 {removed} 张成品")

    def _confirm_exit(self, count):
        """退出确认对话框，返回 'save' / 'discard' / 'cancel'。"""
        win = tk.Toplevel(self.root)
        win.title("退出确认")
        win.configure(bg=BG_MAIN)
        win.transient(self.root)
        win.resizable(False, False)
        result = {'v': 'cancel'}

        tk.Label(win, text="确定要退出吗？", font=FONT_TITLE, fg=ACCENT, bg=BG_MAIN
                 ).pack(anchor='w', padx=24, pady=(20, 6))
        msg = (f"本次已处理并保存 {count} 张成品到：\n{self.output_dir}\n\n"
               "· 保存并退出：保留这些成品\n"
               "· 不保存并退出：删除本次处理生成的成品（之前已存在的不受影响）")
        tk.Label(win, text=msg, font=FONT_MAIN, fg=TEXT_MAIN, bg=BG_MAIN, justify='left'
                 ).pack(anchor='w', padx=24, pady=(0, 16))

        btnrow = ttk.Frame(win)
        btnrow.pack(fill='x', padx=24, pady=(0, 20))

        def choose(v):
            result['v'] = v
            win.destroy()

        ttk.Button(btnrow, text="  取消  ", command=lambda: choose('cancel')
                   ).pack(side='right')
        tk.Button(btnrow, text=f"  不保存并退出（删除本次 {count} 张成品）  ",
                  font=FONT_MAIN, fg='#0b0d12', bg=RED, activebackground='#fca5a5',
                  bd=0, padx=12, pady=6, cursor='hand2',
                  command=lambda: choose('discard')).pack(side='right', padx=(0, 8))
        ttk.Button(btnrow, text="  保存并退出  ", style='Accent.TButton',
                   command=lambda: choose('save')).pack(side='right', padx=(0, 8))

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        rx = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        ry = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        win.geometry(f"+{max(0, rx)}+{max(0, ry)}")
        win.grab_set()
        win.protocol("WM_DELETE_WINDOW", lambda: choose('cancel'))
        self.root.wait_window(win)
        return result['v']


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
