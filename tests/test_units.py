from __future__ import annotations

import unittest

from pptui.units import AUTO, Percent, Rect, Size, Thickness, parse_length, parse_thickness, resolve_length


class LengthTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_length("1in"), 914400)
        self.assertEqual(parse_length("2.54cm"), 914400)
        self.assertEqual(parse_length("72pt"), 914400)
        self.assertEqual(parse_length("25.4mm"), 914400)
        self.assertEqual(parse_length("96px"), 914400)
        self.assertEqual(parse_length("914400emu"), 914400)

    def test_default_unit_is_point(self):
        self.assertEqual(parse_length("12"), 12 * 12700)

    def test_percent(self):
        value = parse_length("50%")
        self.assertIsInstance(value, Percent)
        self.assertEqual(resolve_length(value, 1000), 500)

    def test_auto(self):
        self.assertIs(parse_length("Auto"), AUTO)
        self.assertIs(parse_length(None), AUTO)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_length("12 fingers")
        with self.assertRaises(ValueError):
            parse_length("10%", allow_percent=False)


class ThicknessTests(unittest.TestCase):
    def test_one_value(self):
        thickness = parse_thickness("10")
        self.assertEqual(thickness, Thickness(127000, 127000, 127000, 127000))

    def test_two_values(self):
        thickness = parse_thickness("10 20")
        self.assertEqual(thickness, Thickness(254000, 127000, 254000, 127000))

    def test_four_values(self):
        thickness = parse_thickness("1pt 2pt 3pt 4pt")
        self.assertEqual(thickness, Thickness(12700, 25400, 38100, 50800))

    def test_empty(self):
        self.assertEqual(parse_thickness(None), Thickness())


class GeometryTests(unittest.TestCase):
    def test_deflate(self):
        rect = Rect(0, 0, 1000, 1000)
        inner = rect.deflate(Thickness(100, 200, 100, 200))
        self.assertEqual(inner, Rect(100, 200, 800, 600))
        self.assertEqual(inner.right, 900)
        self.assertEqual(inner.bottom, 800)

    def test_size(self):
        self.assertEqual(Size(1, 2).grow(Size(3, 1)), Size(3, 2))


if __name__ == "__main__":
    unittest.main()
