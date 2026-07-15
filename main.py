"""
图片裁剪矫正与导出工具 - 主入口

统一菜单界面，引导用户按流水线顺序操作：
  1. 图片透视裁剪（自动转换格式 -> 裁剪）
  2. 图片水平矫正（自动转换格式 -> 矫正）
  3. 文件夹对账检查
  4. 导出为 PPT
  5. 导出为 PDF
  6. 导出为 Word

推荐流程: 1/2 -> 4/5/6
（格式转换已内置到裁剪/矫正流程中，无需单独操作）

运行: python main.py
"""

import config


def print_banner():
    print()
    print("=" * 50)
    print("        图片裁剪矫正与导出工具")
    print("=" * 50)
    print(f"  项目目录: {config.PROJECT_ROOT}")
    print(f"  源文件:   {config.SOURCE_DIR}")
    print(f"  裁剪后:   {config.CROPPED_DIR}")
    print(f"  矫正后:   {config.LEVELED_DIR}")
    print(f"  导出至:   {config.EXPORT_DIR}")
    print("=" * 50)


def print_menu():
    print()
    print("-" * 50)
    print("  请选择操作：")
    print("    [1] 图片透视裁剪（自动转换格式 -> 裁剪）")
    print("    [2] 图片水平矫正（自动转换格式 -> 矫正）")
    print("    [3] 文件夹对账检查")
    print("    [4] 导出为 PPT")
    print("    [5] 导出为 PDF")
    print("    [6] 导出为 Word")
    print("    [0] 退出")
    print("-" * 50)
    print("  推荐流程: 1/2 -> 4/5/6")
    print("  （格式转换已内置到裁剪/矫正流程中，无需单独操作）")
    print("-" * 50)


def main():
    while True:
        print_banner()
        print_menu()
        choice = input("\n  请输入选项 [0-6]: ").strip()

        if choice == '1':
            print("\n" + "=" * 50)
            print("  [1] 图片透视裁剪")
            print("=" * 50)
            import crop_tool
            crop_tool.process_images()

        elif choice == '2':
            print("\n" + "=" * 50)
            print("  [2] 图片水平矫正")
            print("=" * 50)
            import level
            level.process_images()

        elif choice == '3':
            print("\n" + "=" * 50)
            print("  [3] 文件夹对账检查")
            print("=" * 50)
            import check_folders
            check_folders.check_folders()

        elif choice == '4':
            print("\n" + "=" * 50)
            print("  [4] 导出为 PPT")
            print("=" * 50)
            import export
            export.export_ppt()

        elif choice == '5':
            print("\n" + "=" * 50)
            print("  [5] 导出为 PDF")
            print("=" * 50)
            import export
            export.export_pdf()

        elif choice == '6':
            print("\n" + "=" * 50)
            print("  [6] 导出为 Word")
            print("=" * 50)
            import export
            export.export_word()

        elif choice == '0':
            print("\n  再见！")
            break

        else:
            print("\n  [错误] 无效选项，请重新输入。")

        # 操作完成后暂停，等用户确认
        print("\n" + "-" * 50)
        input("  按回车键返回菜单...")


if __name__ == "__main__":
    main()
