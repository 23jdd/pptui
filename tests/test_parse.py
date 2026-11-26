from __future__ import annotations

import unittest
from pathlib import Path

from pptui.errors import DslError
from pptui.parse import parse_deck
from pptui.schema import validate_source

ROOT = Path(__file__).resolve().parent.parent
IN = 914400


class ParseTests(unittest.TestCase):
    def test_defaults_and_inheritance(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in" FontFamily="Cambria"
                 EastAsianFontFamily="Microsoft YaHei">
                 <Slide><TextBlock Text="hi"/></Slide></Deck>"""
        )
        runs = deck.slides[0].children[0].runs
        self.assertEqual(runs[0].family, "Cambria")
        self.assertEqual(runs[0].ea, "Microsoft YaHei")

    def test_style_precedence(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in">
                 <Styles>
                   <Style Key="title" FontSize="40" Foreground="#112233"/>
                   <Style TargetType="TextBlock" FontSize="18"/>
                 </Styles>
                 <Slide>
                   <TextBlock Text="styled" Style="title"/>
                   <TextBlock Text="plain"/>
                 </Slide>
               </Deck>"""
        )
        styled = deck.slides[0].children[0].runs[0]
        plain = deck.slides[0].children[1].runs[0]
        self.assertEqual(styled.size, 40)
        self.assertEqual(styled.color.value, "112233")
        self.assertEqual(plain.size, 18)

    def test_element_attribute_beats_style(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in">
                 <Styles><Style Key="body" FontSize="20" Foreground="#000000"/></Styles>
                 <Slide><TextBlock Text="x" Style="body" FontSize="12"/></Slide>
               </Deck>"""
        )
        self.assertEqual(deck.slides[0].children[0].runs[0].size, 12)

    def test_named_colors(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in">
                 <Styles><Color Key="brand" Value="#2563EB"/></Styles>
                 <Slide><TextBlock Text="x" Foreground="$brand"/></Slide>
               </Deck>"""
        )
        color = deck.slides[0].children[0].runs[0].color
        self.assertEqual((color.kind, color.value), ("srgb", "2563EB"))

    def test_theme_colors(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in">
                 <Theme><Color Key="accent1" Value="#FF0000"/></Theme>
                 <Slide><TextBlock Text="x" Foreground="@accent1"/></Slide>
               </Deck>"""
        )
        color = deck.slides[0].children[0].runs[0].color
        self.assertEqual(color.kind, "scheme")
        self.assertEqual(deck.theme.colors["accent1"], "FF0000")

    def test_unknown_element(self):
        with self.assertRaises(DslError) as caught:
            parse_deck('<Deck Width="10in" Height="7.5in"><Slide><Nope/></Slide></Deck>')
        self.assertIn("Nope", str(caught.exception))

    def test_invalid_length(self):
        with self.assertRaises(DslError) as caught:
            parse_deck('<Deck Width="10in" Height="7.5in"><Slide><TextBlock Width="wide"/></Slide></Deck>')
        self.assertIn("Width", str(caught.exception))

    def test_run_children(self):
        deck = parse_deck(
            """<Deck Width="10in" Height="7.5in"><Slide>
                 <TextBlock>plain <Run FontWeight="Bold">bold</Run> tail</TextBlock>
               </Slide></Deck>"""
        )
        runs = deck.slides[0].children[0].runs
        self.assertEqual("".join(run.text for run in runs), "plain bold tail")
        self.assertTrue(runs[1].bold)

    def test_xml_space_preserve_inherits(self):
        deck = parse_deck('<Deck><Slide xml:space="preserve"><TextBlock>a  b</TextBlock></Slide></Deck>')
        self.assertEqual(deck.slides[0].children[0].runs[0].text, "a  b")

    def test_xml_space_default_collapses(self):
        deck = parse_deck('<Deck><Slide xml:space="default"><TextBlock>a  b</TextBlock></Slide></Deck>')
        self.assertEqual(deck.slides[0].children[0].runs[0].text, "a b")

    def test_xml_space_preserve_drops_layout_indent(self):
        deck = parse_deck('<Deck><Slide xml:space="preserve"><TextBlock>\n   a  b\n </TextBlock></Slide></Deck>')
        self.assertEqual(deck.slides[0].children[0].runs[0].text, "a  b")

    def test_xml_space_local_override(self):
        deck = parse_deck(
            '<Deck xml:space="preserve"><Slide><TextBlock xml:space="default">a  b</TextBlock></Slide></Deck>'
        )
        self.assertEqual(deck.slides[0].children[0].runs[0].text, "a b")

    def test_schema_accepts_examples(self):
        for name in ("hello.xml", "tutorial.xml", "example.xml", "report.xml"):
            self.assertTrue(validate_source(ROOT / "examples" / name))

    def test_schema_rejects_unknown_attribute(self):
        source = ROOT / "out" / "bad.xml"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('<Deck Width="10in" Height="7.5in"><Slide Background2="#fff"/></Deck>', encoding="utf-8")
        with self.assertRaises(DslError):
            validate_source(source)

    def _validate(self, body):
        source = ROOT / "out" / "schema-case.xml"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(body, encoding="utf-8")
        return validate_source(source)

    def test_schema_rejects_padding_on_panel(self):
        with self.assertRaises(DslError):
            self._validate('<Deck><Slide><Grid Padding="10"/></Slide></Deck>')

    def test_schema_accepts_table_rows_wrapper(self):
        self.assertTrue(
            self._validate(
                '<Deck><Slide><Table><Table.Rows><Row><Cell Text="x"/></Row></Table.Rows></Table></Slide></Deck>'
            )
        )

    def test_schema_accepts_text_attribute(self):
        self.assertTrue(
            self._validate(
                '<Deck><Slide><TextBlock Text="hi"/><List><Item Text="one"/></List></Slide></Deck>'
            )
        )

    def test_schema_rejects_radius_on_rectangle(self):
        with self.assertRaises(DslError):
            self._validate('<Deck><Slide><Rectangle RadiusX="1"/></Slide></Deck>')

    def test_schema_declares_every_visual_tag(self):
        from pptui.parse import VISUAL_TAGS

        text = (ROOT / "pptui" / "schema" / "pptui.xsd").read_text(encoding="utf-8")
        for tag in VISUAL_TAGS:
            self.assertIn(f'<xs:element name="{tag}">', text)


if __name__ == "__main__":
    unittest.main()
