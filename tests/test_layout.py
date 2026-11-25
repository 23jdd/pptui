from __future__ import annotations

import unittest

from pptui.layout import LayoutEngine
from pptui.parse import parse_deck

IN = 914400


def layout(xml):
    deck = parse_deck(xml)
    LayoutEngine(deck).run()
    return deck


def find(node, name):
    if node.get("Name") == name:
        return node
    for child in node.children:
        found = find(child, name)
        if found is not None:
            return found
    return None


class LayoutTests(unittest.TestCase):
    def test_grid_fixed_and_star(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Grid>
            <Grid.ColumnDefinitions><ColumnDefinition Width="2in"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
            <Grid.RowDefinitions><RowDefinition Height="1in"/><RowDefinition Height="*"/></Grid.RowDefinitions>
            <TextBlock Name="a" Grid.Row="0" Grid.Column="0" Text="A"/>
            <Border Name="b" Grid.Row="1" Grid.Column="1" Padding="0.5in"><Rectangle Name="c"/></Border>
            </Grid></Slide></Deck>"""
        )
        slide = deck.slides[0]
        a = find(slide, "a")
        b = find(slide, "b")
        c = find(slide, "c")
        self.assertEqual(a.rect, (0, 0, 2 * IN, 1 * IN))
        self.assertEqual(b.rect, (2 * IN, 1 * IN, 8 * IN, int(6.5 * IN)))
        self.assertEqual(c.rect, (int(2.5 * IN), int(1.5 * IN), 7 * IN, int(5.5 * IN)))

    def test_stack_panel_spacing(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><StackPanel Name="s" Spacing="10">
            <TextBlock Name="a" Width="1in" Height="0.5in"/>
            <TextBlock Name="b" Width="2in" Height="1in" HorizontalAlignment="Right"/>
            </StackPanel></Slide></Deck>"""
        )
        a = find(deck.slides[0], "a")
        b = find(deck.slides[0], "b")
        self.assertEqual(a.rect, (0, 0, 1 * IN, IN // 2))
        self.assertEqual(b.rect.x, 8 * IN)
        self.assertEqual(b.rect.y, IN // 2 + 10 * 12700)
        self.assertEqual(b.rect.w, 2 * IN)

    def test_canvas_position(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Canvas Width="10in" Height="7.5in">
            <Ellipse Name="e" Canvas.Left="1in" Canvas.Top="2in" Width="3in" Height="2in" Fill="#FF0000"/>
            </Canvas></Slide></Deck>"""
        )
        e = find(deck.slides[0], "e")
        self.assertEqual(e.rect, (1 * IN, 2 * IN, 3 * IN, 2 * IN))

    def test_border_padding_and_margin(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Border Padding="0.25in" Margin="0.5in">
            <TextBlock Name="t" Width="2in" Height="1in" HorizontalAlignment="Center" VerticalAlignment="Center"/>
            </Border></Slide></Deck>"""
        )
        t = find(deck.slides[0], "t")
        self.assertEqual(t.rect.x, 4 * IN)
        self.assertEqual(t.rect.y, int(3.25 * IN))
        self.assertEqual(t.rect.w, 2 * IN)

    def test_dock_panel(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><DockPanel>
            <TextBlock Name="top" DockPanel.Dock="Top" Height="1in"/>
            <TextBlock Name="left" DockPanel.Dock="Left" Width="2in"/>
            <TextBlock Name="fill"/>
            </DockPanel></Slide></Deck>"""
        )
        top = find(deck.slides[0], "top")
        left = find(deck.slides[0], "left")
        fill = find(deck.slides[0], "fill")
        self.assertEqual(top.rect, (0, 0, 10 * IN, 1 * IN))
        self.assertEqual(left.rect, (0, 1 * IN, 2 * IN, int(6.5 * IN)))
        self.assertEqual(fill.rect, (2 * IN, 1 * IN, 8 * IN, int(6.5 * IN)))

    def test_percent_width(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><StackPanel>
            <TextBlock Name="a" Width="50%" Height="1in"/>
            </StackPanel></Slide></Deck>"""
        )
        a = find(deck.slides[0], "a")
        self.assertEqual(a.rect.w, 5 * IN)

    def test_text_intrinsic_height(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><TextBlock Name="a" Text="hello" FontSize="20"/></Slide></Deck>"""
        )
        a = find(deck.slides[0], "a")
        self.assertEqual(a.measured.h, 20 * 12700 * 12 // 10)

    def test_grid_auto_column(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Grid>
            <Grid.ColumnDefinitions><ColumnDefinition Width="Auto"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
            <TextBlock Name="a" Grid.Column="0" Width="1.5in" Height="0.4in"/>
            <TextBlock Name="b" Grid.Column="1"/>
            </Grid></Slide></Deck>"""
        )
        a = find(deck.slides[0], "a")
        b = find(deck.slides[0], "b")
        self.assertEqual(a.rect.w, int(1.5 * IN))
        self.assertEqual(b.rect.x, int(1.5 * IN))
        self.assertEqual(b.rect.w, int(8.5 * IN))

    def test_margin_offsets_child(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Canvas Width="10in" Height="7.5in">
            <Rectangle Name="r" Canvas.Left="1in" Canvas.Top="1in" Width="2in" Height="2in" Margin="0.25in"/>
            </Canvas></Slide></Deck>"""
        )
        r = find(deck.slides[0], "r")
        self.assertEqual(r.rect.x, int(1.25 * IN))
        self.assertEqual(r.rect.y, int(1.25 * IN))
        self.assertEqual(r.rect.w, int(1.5 * IN))

    def test_text_padding_narrows_wrap_width(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><StackPanel>
            <TextBlock Name="a" Width="2in" FontSize="20" Padding="0.5in">abcdefghijklmnopqrstuvwxyz</TextBlock>
            <TextBlock Name="b" Width="2in" FontSize="20">abcdefghijklmnopqrstuvwxyz</TextBlock>
            </StackPanel></Slide></Deck>"""
        )
        padded = find(deck.slides[0], "a")
        plain = find(deck.slides[0], "b")
        self.assertGreater(padded.measured.h, plain.measured.h)

    def test_padding_rejected_on_panel(self):
        from pptui.errors import DslError

        with self.assertRaises(DslError):
            layout('<Deck Width="10in" Height="7.5in"><Slide><StackPanel Padding="10"/></Slide></Deck>')

    def test_table_fills_star_row(self):
        deck = layout(
            """<Deck Width="10in" Height="7.5in"><Slide><Grid>
            <Grid.RowDefinitions><RowDefinition Height="*"/></Grid.RowDefinitions>
            <Table><Table.Columns><Column Width="*"/></Table.Columns>
              <Row Height="0.5in"><Cell>x</Cell></Row>
            </Table>
            </Grid></Slide></Deck>"""
        )
        table = deck.slides[0].children[0].children[0]
        self.assertEqual(table.rect.h, 7 * IN + IN // 2)
        self.assertLess(table.measured.h, table.rect.h)


if __name__ == "__main__":
    unittest.main()
