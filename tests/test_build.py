from __future__ import annotations

import contextlib
import io
import shutil
import uuid
import unittest
import zipfile
from pathlib import Path

from PIL import Image
from pptx import Presentation

from pptui.build import build
from pptui.errors import DslError
from pptui.parse import parse_deck
from pptui.pipeline import render_presentation

ROOT = Path(__file__).resolve().parent.parent
TMP_ROOT = ROOT / "out" / "test-tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)
IN = 914400


@contextlib.contextmanager
def case_dir():
    path = TMP_ROOT / uuid.uuid4().hex
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def unzip_part(data, name):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read(name).decode("utf-8")


class BuildTests(unittest.TestCase):
    def test_hello(self):
        data = build(ROOT / "examples" / "hello.xml")
        prs = Presentation(io.BytesIO(data))
        self.assertEqual(len(prs.slides), 1)
        texts = [shape.text_frame.text for shape in prs.slides[0].shapes if shape.has_text_frame]
        self.assertIn("Hello, pptui", texts)

    def test_report_structure(self):
        data = build(ROOT / "examples" / "report.xml")
        prs = Presentation(io.BytesIO(data))
        self.assertEqual(len(prs.slides), 6)
        tables = [shape for shape in prs.slides[3].shapes if shape.has_table]
        self.assertEqual(len(tables), 1)
        self.assertEqual(len(tables[0].table.rows), 6)
        charts = [shape for shape in prs.slides[2].shapes if shape.has_chart]
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0].chart.plots[0].series[0].name, "目标")

    def test_notes(self):
        data = build(ROOT / "examples" / "report.xml")
        prs = Presentation(io.BytesIO(data))
        notes = prs.slides[0].notes_slide.notes_text_frame.text
        self.assertIn("开场", notes)

    def test_theme_is_patched(self):
        data = build(ROOT / "examples" / "report.xml")
        theme = unzip_part(data, "ppt/theme/theme1.xml")
        self.assertIn('val="2563EB"', theme)
        self.assertIn('typeface="Microsoft YaHei"', theme)
        self.assertIn('name="pptui"', theme)

    def test_east_asian_font_written(self):
        data = build(ROOT / "examples" / "hello.xml")
        slide = unzip_part(data, "ppt/slides/slide1.xml")
        self.assertIn('typeface="Microsoft YaHei"', slide)

    def test_image_uniform_to_fill_crops(self):
        with case_dir() as directory:
            directory = Path(directory)
            image = Image.new("RGB", (400, 200), (200, 30, 30))
            image.save(directory / "pic.png")
            (directory / "deck.xml").write_text(
                """<Deck Width="10in" Height="7.5in"><Slide>
                     <Image Source="pic.png" Width="4in" Height="1in" Stretch="UniformToFill"/>
                   </Slide></Deck>""",
                encoding="utf-8",
            )
            data = build(directory / "deck.xml")
            prs = Presentation(io.BytesIO(data))
            pictures = [shape for shape in prs.slides[0].shapes if shape.shape_type == 13]
            self.assertEqual(len(pictures), 1)
            picture = pictures[0]
            self.assertAlmostEqual(picture.crop_top, 0.25, places=2)
            self.assertEqual(picture.width, 4 * IN)

    def test_image_missing_raises(self):
        with case_dir() as directory:
            directory = Path(directory)
            (directory / "deck.xml").write_text(
                '<Deck Width="10in" Height="7.5in"><Slide><Image Source="none.png"/></Slide></Deck>',
                encoding="utf-8",
            )
            with self.assertRaises(DslError):
                parse_deck(directory / "deck.xml")

    def test_empty_slide_builds(self):
        data = build("<Deck><Slide/></Deck>")
        prs = Presentation(io.BytesIO(data))
        self.assertEqual(len(prs.slides), 1)
        self.assertEqual(len(prs.slides[0].shapes), 0)

    def test_text_padding_writes_frame_margins(self):
        deck = parse_deck(
            '<Deck Width="10in" Height="7.5in"><Slide><TextBlock Padding="0.25in" Text="hi"/></Slide></Deck>'
        )
        prs, _ = render_presentation(deck)
        frame = prs.slides[0].shapes[0].text_frame
        self.assertEqual(frame.margin_left, int(0.25 * IN))
        self.assertEqual(frame.margin_top, int(0.25 * IN))

    def test_auto_sized_text_never_rewraps(self):
        deck = parse_deck(
            """<Deck Width="13.333in" Height="7.5in"><Slide><StackPanel>
                 <Border Background="#ff0000"><TextBlock FontSize="30" Text="PPT UI WITH XAML"/></Border>
                 <TextBlock>Let's Go</TextBlock>
               </StackPanel></Slide></Deck>"""
        )
        prs, _ = render_presentation(deck)
        frames = [
            shape.text_frame
            for shape in prs.slides[0].shapes
            if shape.has_text_frame and shape.text_frame.text
        ]
        self.assertEqual([frame.text for frame in frames], ["PPT UI WITH XAML", "Let's Go"])
        for frame in frames:
            self.assertFalse(frame.word_wrap)

    def test_constrained_text_still_wraps(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in"><Slide>
                 <TextBlock Width="1in" Text="alpha beta gamma delta"/>
               </Slide></Deck>"""
        )
        prs, _ = render_presentation(deck)
        self.assertTrue(prs.slides[0].shapes[0].text_frame.word_wrap)

    def test_table_cell_padding_survives_text_rendering(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in"><Slide><Table CellPadding="0.1in">
                 <Table.Columns><Column Width="1in"/></Table.Columns>
                 <Row><Cell>x</Cell></Row>
               </Table></Slide></Deck>"""
        )
        prs, _ = render_presentation(deck)
        table = [shape for shape in prs.slides[0].shapes if shape.has_table][0].table
        self.assertEqual(table.cell(0, 0).margin_left, int(0.1 * IN))

    def test_unsupported_chart_type(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in"><Slide>
                 <Chart Type="sankey"><Category>A</Category><Series Name="s">1</Series></Chart>
               </Slide></Deck>"""
        )
        with self.assertRaises(DslError):
            render_presentation(deck)

    def test_star_grid_inside_finite_parent(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in"><Slide><Grid>
                 <Grid.RowDefinitions><RowDefinition Height="*"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                 <TextBlock Name="a" Grid.Row="0" Text="one"/>
                 <TextBlock Name="b" Grid.Row="1" Text="two"/>
               </Grid></Slide></Deck>"""
        )
        from pptui.layout import LayoutEngine

        LayoutEngine(deck).run()
        a, b = deck.slides[0].children[0].children
        self.assertEqual(a.rect.h, b.rect.h)
        self.assertEqual(a.rect.y, 0)
        self.assertEqual(b.rect.y, a.rect.h)


if __name__ == "__main__":
    unittest.main()
