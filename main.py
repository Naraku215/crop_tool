"""
crop_tool - 命令行入口

CLI 工具，提供格式转换、对账检查等独立功能。
GUI 用户请直接运行 gui.py。

运行: python main.py
"""

import config


def print_banner():
    print()
    print("=" * 50)
    print("        crop_tool")
    print("=" * 50)
    print(f"  项目目录: {config.PROJECT_ROOT}")
    print("=" * 50)


def print_menu():
    print()
    print("-" * 50)
    print("  请选择操作：")
    print("    [1] 格式转换（任意格式 -> PNG）")
    print("    [2] 文件夹对账检查")
    print("    [3] 导出为 PPT/PDF/Word")
    print("    [0] 退出")
    print("-" * 50)
    print("  提示: 推荐使用 GUI 界面 (python gui.py)")
    print("-" * 50)


def main():
    while True:
        print_banner()
        print_menu()
        choice = input("\n  请输入选项 [0-3]: ").strip()

        if choice == '1':
            print("\n" + "=" * 50)
            print("  [1] 格式转换")
            print("=" * 50)
            import trans_png
            input_dir = input("  输入目录: ").strip()
            output_dir = input("  输出目录: ").strip()
            if input_dir and output_dir:
                trans_png.convert_to_png(input_dir, output_dir)
            else:
                print("  [错误] 路径不能为空")

        elif choice == '2':
            print("\n" + "=" * 50)
            print("  [2] 文件夹对账检查")
            print("=" * 50)
            import check_folders
            input_dir = input("  原始目录: ").strip()
            processed_dir = input("  处理后目录: ").strip()
            if input_dir and processed_dir:
                check_folders.check_folders(input_dir, processed_dir)
            else:
                print("  [错误] 路径不能为空")

        elif choice == '3':
            print("\n" + "=" * 50)
            print("  [3] 导出为 PPT/PDF/Word")
            print("=" * 50)
            import export
            input_dir = input("  输入目录: ").strip()
            output_dir = input("  输出目录: ").strip()
            fmt = input("  格式 (ppt/pdf/word/all): ").strip() or "all"
            if input_dir and output_dir:
                if fmt in ("ppt", "all"):
                    export.export_ppt(input_dir, output_dir)
                if fmt in ("pdf", "all"):
                    export.export_pdf(input_dir, output_dir)
                if fmt in ("word", "all"):
                    export.export_word(input_dir, output_dir)
            else:
                print("  [错误] 路径不能为空")

        elif choice == '0':
            print("\n  再见！")
            break

        else:
            print("\n  [错误] 无效选项，请重新输入。")

        print("\n" + "-" * 50)
        input("  按回车键返回菜单...")


if __name__ == "__main__":
    main()
