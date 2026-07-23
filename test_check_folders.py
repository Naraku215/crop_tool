"""crop_tool - check_folders 对账逻辑测试

校验核心不变量：输入文件顺序 == 输出文件顺序。
覆盖纯函数 get_original_stem_from_png 与 compare_folder。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_folders  # noqa: E402


def _touch(path, mtime):
    """创建空文件并设置 mtime（秒，epoch）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    os.utime(path, (mtime, mtime))


class TestGetOriginalStemFromPng(unittest.TestCase):
    def test_strips_numeric_prefix(self):
        self.assertEqual(
            check_folders.get_original_stem_from_png("001_IMG_1234.png"), "IMG_1234"
        )

    def test_case_insensitive_ext(self):
        self.assertEqual(check_folders.get_original_stem_from_png("002_photo.PNG"), "photo")

    def test_no_prefix_falls_back_to_stem(self):
        self.assertEqual(check_folders.get_original_stem_from_png("plain.png"), "plain")

    def test_non_png_returns_stem(self):
        self.assertEqual(check_folders.get_original_stem_from_png("readme.txt"), "readme")


class TestCompareFolder(unittest.TestCase):
    def _make(self, tmp, layout):
        """layout: {relpath: mtime}。创建空文件并设 mtime，返回路径列表。"""
        paths = []
        for rel, mt in layout.items():
            full = os.path.join(tmp, rel)
            _touch(full, mt)
            paths.append(full)
        return paths

    def test_perfect_match(self):
        """输入输出同名且 mtime 顺序一致 -> perfect。"""
        with tempfile.TemporaryDirectory() as tmp:
            orig = self._make(tmp, {"a.jpg": 1000, "b.jpg": 2000})
            png = self._make(tmp, {"out/a.png": 1000, "out/b.png": 2000})
            r = check_folders.compare_folder(orig, png)
            self.assertEqual(r["status"], "perfect")
            self.assertEqual(r["orig_count"], 2)
            self.assertEqual(r["crop_count"], 2)

    def test_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig = self._make(tmp, {"a.jpg": 1000, "b.jpg": 2000, "c.jpg": 3000})
            png = self._make(tmp, {"out/a.png": 1000, "out/b.png": 2000})
            r = check_folders.compare_folder(orig, png)
            self.assertEqual(r["status"], "count_mismatch")
            self.assertEqual(r["orig_count"], 3)
            self.assertEqual(r["crop_count"], 2)

    def test_order_mismatch_when_output_order_differs(self):
        """复现核心 bug：输入顺序 != 输出顺序（跳跃处理）。

        原图 a(mtime早) b(mtime晚) -> 输入扫描顺序 [a, b]
        PNG  b(mtime早,先保存) a(mtime晚,后保存) -> 输出顺序 [b, a]
        旧逻辑按文件名字典序排 PNG -> [a, b] -> 误判 perfect（漏报）
        新逻辑两侧统一 get_sort_key -> 抓到 order_mismatch
        """
        with tempfile.TemporaryDirectory() as tmp:
            orig = self._make(tmp, {"a.jpg": 1000, "b.jpg": 2000})
            png = self._make(tmp, {"out/a.png": 3000, "out/b.png": 1500})
            r = check_folders.compare_folder(orig, png)
            self.assertEqual(r["status"], "order_mismatch")

    def test_numeric_prefix_orders_by_number_not_lex(self):
        """数字前缀按数值比较：02_ 应排在 10_ 之前。"""
        with tempfile.TemporaryDirectory() as tmp:
            orig = self._make(tmp, {"02_b.jpg": 1000, "10_a.jpg": 1000})
            png = self._make(tmp, {"out/02_b.png": 1000, "out/10_a.png": 1000})
            r = check_folders.compare_folder(orig, png)
            self.assertEqual(r["status"], "perfect")
            self.assertEqual(r["orig_stems"], ["02_b", "10_a"])
            self.assertEqual(r["crop_stems"], ["02_b", "10_a"])


if __name__ == "__main__":
    unittest.main()
