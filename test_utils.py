"""crop_tool - utils 排序逻辑测试

锁定 get_sort_key 的行为，作为各模块统一排序基准的 characterization 测试。
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import utils  # noqa: E402


class TestGetSortKey(unittest.TestCase):
    def test_numeric_prefix_orders_by_number(self):
        """数字前缀按数值比较：02_ 应排在 10_ 之前（字典序会判 10_ < 02_，错误）。"""
        with tempfile.TemporaryDirectory() as tmp:
            p2 = os.path.join(tmp, "02_b.jpg")
            p10 = os.path.join(tmp, "10_a.jpg")
            Path(p2).touch()
            Path(p10).touch()
            ordered = sorted([p10, p2], key=utils.get_sort_key)
            self.assertEqual(ordered, [p2, p10])

    def test_no_prefix_falls_back_to_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.path.join(tmp, "old.jpg")
            new = os.path.join(tmp, "new.jpg")
            Path(old).touch()
            Path(new).touch()
            os.utime(old, (1000, 1000))
            os.utime(new, (2000, 2000))
            ordered = sorted([new, old], key=utils.get_sort_key)
            self.assertEqual(ordered, [old, new])

    def test_numeric_prefix_takes_precedence_over_mtime(self):
        """有数字前缀的文件优先于无前缀文件，即使前者的 mtime 更晚。"""
        with tempfile.TemporaryDirectory() as tmp:
            prefixed = os.path.join(tmp, "001_x.jpg")
            bare = os.path.join(tmp, "z.jpg")
            Path(prefixed).touch()
            Path(bare).touch()
            os.utime(prefixed, (5000, 5000))
            os.utime(bare, (1000, 1000))
            ordered = sorted([bare, prefixed], key=utils.get_sort_key)
            # 前缀文件 (0, ...) 优先于无前缀文件 (1, 0, mtime)
            self.assertEqual(ordered, [prefixed, bare])


if __name__ == "__main__":
    unittest.main()
