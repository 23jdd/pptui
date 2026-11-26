# pptui

用 XML 描述幻灯片，编译成真正的 `.pptx`。布局语义对齐 WPF：`Canvas`、`StackPanel`、`Grid`、`Border`、`DockPanel`，加上 `Measure/Arrange`、`Margin`、`HorizontalAlignment/VerticalAlignment`。

生成端是 `python-pptx` 建结构、`lxml` 打补丁；XML 端用 `lxml` 解析和 XSD 校验。

## 安装

作为命令行工具装到全局（需要 Python 3.14，见 `pyproject.toml` 的 `requires-python`）：

```bash
uv tool install .
pptui --help
```

或者在仓库里直接用虚拟环境：

```bash
uv sync
python -m pptui --help
```

## 快速开始

```bash
python -m pptui build examples/hello.xml -o out/hello.pptx
python -m pptui build examples/tutorial.xml -o out/tutorial.pptx
python -m pptui build examples/report.xml -o out/report.pptx
```

第一次用建议从 [docs/tutorial.md](docs/tutorial.md) 开始。

最小示例：

```xml
<Deck FontFamily="Calibri" EastAsianFontFamily="Microsoft YaHei">
  <Slide Background="@lt1">
    <Border Padding="0.8in">
      <StackPanel Spacing="0.2in">
        <TextBlock FontSize="44" FontWeight="Bold" Foreground="@dk1">Hello, pptui</TextBlock>
        <TextBlock FontSize="18" Foreground="@dk2">XML in, PowerPoint out.</TextBlock>
      </StackPanel>
    </Border>
  </Slide>
</Deck>
```

默认画布 16:9（12192000 × 6858000 EMU，即 13.333in × 7.5in），可用 `Width` / `Height` 覆盖。

## 命令行

```bash
python -m pptui build deck.xml [-o out.pptx] [--template base.pptx] [--ir layout.json] [--no-schema] [--no-check]
python -m pptui validate deck.xml      # 只做 XSD 校验
python -m pptui ir deck.xml            # 打印布局结果（绝对 EMU 矩形），不生成 pptx
python -m pptui schema                 # 打印 XSD 路径
```

`build` 默认做三件事：XSD 校验、布局、产物自检（重新打开 + 解包检查）。任何一步失败都会给出带行号的错误。

在 PyCharm / VS Code 里给根节点加一行，就能获得补全和实时校验：

```xml
<Deck xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:noNamespaceSchemaLocation="pptui/schema/pptui.xsd">
```

## 布局：WPF 那一套

| 元素 | 行为 |
|---|---|
| `Canvas` | 子元素用 `Canvas.Left` / `Canvas.Top` 绝对定位，自身不撑开 |
| `StackPanel` | `Orientation="Vertical|Horizontal"`，`Spacing` 控制间距 |
| `Grid` | `RowDefinitions` / `ColumnDefinitions`，支持 `Auto`、`*`、`2*`、`120pt` 与跨行跨列 |
| `Border` | `Padding`、`Background`、`BorderBrush/Thickness`、`RadiusX`；面板（`Grid`/`StackPanel`/`Canvas`/`DockPanel`）没有 `Padding`，与 WPF 一致 |
| `DockPanel` | `DockPanel.Dock` 与 `LastChildFill` |

所有元素共享：`Width/Height`、`MinWidth/MaxWidth`、`MinHeight/MaxHeight`、`Margin`、`HorizontalAlignment`、`VerticalAlignment`、`Name`。

栅格尺寸分配顺序与 WPF 相同：先固定值，再 Auto（量内容），剩下的按权重分给 `*`。子元素先量后排，`*` 行只在父高度确定时才有意义。

## 内容元素

| 元素 | 说明 |
|---|---|
| `TextBlock` | 文本、富文本 `<Run>`、`<LineBreak/>`；`TextWrapping`、`TextAlignment`、`LineHeight`、`AutoFit="Shrink"` |
| `List` + `Item` | 项目符号或编号，`Bullet="Disc|Circle|Square|Number|None"` |
| `Image` | `Source`、`Stretch="Uniform|UniformToFill|Fill|None"` |
| `Rectangle` / `Ellipse` / `RoundedRectangle` | `Fill`、`Stroke`、`StrokeThickness`、`RadiusX` |
| `Table` | 列宽、行高、`ColSpan/RowSpan`、单元格底色与边框 |
| `Chart` | `Column`、`Bar`、`Line`、`Area`、`Pie`、`Doughnut`，原生可编辑 |

## 文本与中文

`TextBlock` 的字体分拉丁和东亚两个属性：`FontFamily` 写 `a:latin`，`EastAsianFontFamily` 写 `a:ea`。只设前者的话，PowerPoint 会拿一个你不知道的字体去渲染中文，所以两个都写。

排版测量用真实字体文件（`PIL.ImageFont`），中文按全角计量，西文按词计量，断行遵守简单的标点禁则。测量结果只用于算高度和判断溢出；文字本身交给 PowerPoint 自己换行。

放不下时 `AutoFit="Shrink"` 会写入 `a:normAutofit fontScale`，让 PowerPoint 按比例缩字号，而不是把文字溢出到框外。

`TextBlock` / `List` 的 `Padding` 和 WPF 一样是文本相对边框的内缩：先扣掉左右内边距再换行，高度也把内边距算进去，渲染时写成文本框的 `a:bodyPr` 四边 inset。

## 颜色与主题

```xml
<Deck>
  <Theme MinorFont="Calibri" MinorEastAsianFont="Microsoft YaHei">
    <Color Key="accent1" Value="#2563EB"/>
  </Theme>
  <Styles>
    <Style Key="h1" FontSize="40" FontWeight="Bold" Foreground="@dk1"/>
    <Color Key="brand" Value="#1E2761"/>
  </Styles>
  ...
</Deck>
```

* `@dk1`、`@lt1`、`@accent1` 等是主题色，生成 `a:schemeClr`，改主题就能全局换色。
* `#RRGGBB` 是固定色，生成 `a:srgbClr`；`#RRGGBBAA` 会额外写 `a:alpha`。
* `$brand` 引用 `<Styles>` 里的命名色。

`<Theme>` 会同时改写 `ppt/theme/theme1.xml` 的配色和字体方案，所以 PowerPoint 的取色器、图表默认色也跟着变。

## 生成质量

每次 `build` 都会自检：zip 结构、`[Content_Types].xml`、每页 XML 可解析、关系可达、`python-pptx` 能重新打开、每页至少有一个形状。

仓库里的 `examples/report.xml` 是一份 6 页的经营分析示例，已用 PowerPoint 打开并逐页导出图片检查过。


## 测试

```bash
python -m unittest discover -s tests
```

56 个用例，覆盖单位换算、断行、栅格/堆叠/画布/停靠布局、样式优先级、XSD 结构校验、主题注入、东亚字体、图片裁剪、表格与图表结构。

## 已知限制

* 不支持动画、切换、SmartArt、组合形状（`Group`）和自定义母版；版式仍来自内置底版。
* 文本测量与 PowerPoint 的实际断行可能有 1–2 像素差异，靠 `AutoFit="Shrink"` 兜底。
* `Canvas` 里的子元素没有宽度约束，长文本会不换行，需要显式给 `Width`。
* 表格只支持单元格内的单一文本块样式，不支持单元格内嵌套布局。
* 导出预览依赖本机安装的 PowerPoint（`tools/export_png.ps1`）。

## 下一步

1. 用 `--template` 接入设计给的 `.pptx` 底版，按名称填充占位符。
2. 增加 `Group` 与连接线，覆盖流程图。
3. 输出 `LayoutResult` 的 SVG 预览，做“改 XML 立即看”的编辑器。
