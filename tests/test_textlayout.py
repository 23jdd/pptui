from __future__ import annotations

import unittest

from pptui.model import RunSpec
from pptui.textlayout import measure_runs, tokens_for
from pptui.units import INF


class FixedMetrics:
    def width_emu(self, text, family, size_pt, bold=False, italic=False, ea=None):
        return len(text) * 10000


class WrapTests(unittest.TestCase):
    def setUp(self):
        self.metrics = FixedMetrics()

    def run_with(self, text, size=10.0):
        return [RunSpec(text=text, size=size)]

    def test_latin_wraps_on_words(self):
        runs = self.run_with("alpha beta gamma delta")
        size = measure_runs(runs, 11 * 10000, self.metrics, wrap=True)
        self.assertEqual(size.h, 2 * int(10 * 1.2 * 12700))

    def test_cjk_wraps_per_character(self):
        runs = self.run_with("一二三四五六七八九十")
        size = measure_runs(runs, 5 * 10000, self.metrics, wrap=True)
        self.assertEqual(size.h, 2 * int(10 * 1.2 * 12700))

    def test_long_word_is_split(self):
        runs = self.run_with("abcdefghij")
        size = measure_runs(runs, 4 * 10000, self.metrics, wrap=True)
        self.assertGreaterEqual(size.h, 3 * int(10 * 1.2 * 12700))

    def test_nowrap(self):
        runs = self.run_with("alpha beta gamma")
        size = measure_runs(runs, 1 * 10000, self.metrics, wrap=False)
        self.assertEqual(size.h, int(10 * 1.2 * 12700))

    def test_newlines_create_paragraphs(self):
        runs = self.run_with("one\ntwo\nthree")
        size = measure_runs(runs, INF, self.metrics, wrap=True)
        self.assertEqual(size.h, 3 * int(10 * 1.2 * 12700))

    def test_explicit_line_height(self):
        runs = self.run_with("one\ntwo", size=10.0)
        size = measure_runs(runs, INF, self.metrics, wrap=True, line_height_pt=30)
        self.assertEqual(size.h, 2 * 30 * 12700)

    def test_tokens_types(self):
        tokens = tokens_for([RunSpec(text="A中 B", size=10.0)], self.metrics)
        kinds = [token.kind for token in tokens]
        self.assertEqual(kinds, ["word", "cjk", "space", "word"])


if __name__ == "__main__":
    unittest.main()
