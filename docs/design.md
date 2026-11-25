# 设计说明

## 目标

把“排版”从 Python 代码里拿出来，放进 XML；Python 只负责编译。输入是一份可读、可 diff、可被编辑器校验的 XML，输出是 PowerPoint 能正常打开、可继续编辑的 `.pptx`。

约束：

* 只用 `lxml` + `python-pptx` + `Pillow`，不引入排版引擎或渲染库。
* 布局模型与 WPF 对齐，写惯了 XAML 的人不需要重新学一套盒模型。
* 生成的文件必须是“真”文件：文本框是真文本框、图表是原生图表、表格是可编辑表格。

## 流水线

```
deck.xml
  │
  ├─ parse      lxml 安全解析（禁外部实体/网络），保留 sourceline
  ├─ model      Element 树 + 样式级联 + 单位/颜色/资源解析
  ├─ schema     XSD 校验（可关闭）
  ├─ layout     Measure/Arrange → 每个元素的绝对 EMU 矩形
  ├─ render     python-pptx 建形状 → lxml 打长尾补丁
  ├─ theme      改写 theme1.xml 的 clrScheme / fontScheme
  ├─ verify     重新打开、解包、逐页检查
  └─ deck.pptx
```

关键点在 `layout` 和 `render` 之间：布局只产出几何和已解析样式，完全不碰 pptx。这样几何可以单测（`ir` 命令能直接打印），渲染层也能换成别的后端。

## 模块

| 模块 | 职责 |
|---|---|
| `parse.py` | XML → `Element` 树；处理属性元素（`Grid.RowDefinitions`）、`Run`、表格行、图表序列；解析单位、颜色、字体、图片路径 |
| `model.py` | `Element`、`RunSpec`、`Theme`、`Deck`；`prepare()` 把 `Margin/Width/Alignment` 等解析成布局可用的值 |
| `schema.py` | XSD 校验，错误带行号 |
| `metrics.py` | 字体文件查找与文本宽度；拉丁、东亚两套字体混合计量 |
| `textlayout.py` | 分词（西文按词、中文按字）、断行、行高、段落高度 |
| `layout.py` | WPF 语义的 Measure/Arrange，五种容器 + 文本/表格/图片/图表 |
| `render/` | `python-pptx` 渲染与 `lxml` 补丁；`text.py` 负责段落/run，`table.py`、`chart.py`、`image.py` 各自独立 |
| `build.py` | 对外入口 `build(source, output)` |
| `verify.py` | 产物自检 |

## 布局

### Measure / Arrange

每个元素两趟：

1. `measure(avail)`：减去 `Margin` 得到内容盒，量出内容尺寸，套上显式 `Width/Height`、`Min/Max`，返回“含 Margin 的期望尺寸”。
2. `arrange(slot)`：父给一个矩形，减 Margin，按 `HorizontalAlignment/VerticalAlignment` 在内部定位，写入 `el.rect`，再递归排子元素。

对齐规则和 WPF 一致：`Stretch` 只在没有显式 `Width/Height` 时铺满；显式尺寸时不再拉伸，`Stretch` 按左上摆放。

### 尺寸分配

* `StackPanel`：主轴给子元素无限空间，交叉轴给可用尺寸；子元素自己决定主轴长度。
* `Grid`：先固定值，再 `Auto`（用子元素量出来的大小），剩下的按 `*` 权重分配；行在列宽确定之后再量，这样 `Auto` 行里的文本能按真实宽度换行。
* `Canvas`：子元素量完后按 `Canvas.Left/Top` 放在指定位置，自身期望尺寸为 0。
* `Border`：内容盒减去 `Padding` 和 `BorderThickness`，加上子元素尺寸。
* `TextBlock` / `List`：`Padding` 先扣宽度再断行，高度加上下内边距；渲染成文本框四边 inset。
* 面板没有 `Padding`（WPF 同样没有），解析阶段直接报错，避免静默忽略。
* `DockPanel`：按顺序切走一条边，最后一个子元素填满剩余。

所有几何都是整数 EMU，百分比在解析后按父内容盒实时换算，避免浮点漂移。

### 文本测量

PowerPoint 不把换行结果写回文件，自动高度只能自己算：

* 用 `PIL.ImageFont` 读真实字体文件（Calibri、Cambria、Arial、微软雅黑、黑体、宋体等），按 64px 探测后线性缩放到目标字号。
* 中文/全角标点用 `EastAsianFontFamily` 量，西文用 `FontFamily` 量；两者混排时逐段切换，否则中文会被当成缺字的西文字体，宽度严重偏小。
* 断行是贪心算法：西文按词、中文按字，行首禁则（`，。）】` 等不落行首）；超长单词按字符硬切。
* 行高 = `LineHeight`，没写就是 `1.2 × 字号`，与 PowerPoint 单倍行距一致。

### 溢出

默认 `AutoFit="Shrink"`。渲染时比较测量高度和实际框高，也检查最长的不可断词是否超宽；需要缩小时写 `a:normAutofit fontScale`，由 PowerPoint 按比例缩小，而不是让文字溢出。这个策略比“截断加省略号”更接近 PowerPoint 自身行为。

## 渲染

### python-pptx 与 lxml 的分工

原则：**结构归 python-pptx，长尾归 lxml；先建对象，后打补丁，不在两者之间来回读。**

| 能力 | 实现 |
|---|---|
| 幻灯片、版式、备注、图片、表格、图表、形状 | python-pptx |
| 主题色 `schemeClr` | lxml（`RGBColor` 只能写 `srgbClr`） |
| 东亚字体 `a:ea`、`a:cs` | lxml（`font.name` 只写 `a:latin`） |
| 单元格边框 `a:lnL/lnR/lnT/lnB` | lxml |
| 项目符号 `a:buChar` / `a:buAutoNum` | lxml |
| `a:normAutofit` | lxml |
| 主题配色/字体方案 | lxml 改写 `theme1.xml` |
| 页面背景为主题色时 | lxml 替换 `p:bgPr` 里的填充 |

`render/xmlutil.py` 里所有插入都按 DrawingML 的子元素顺序插到正确位置（`spPr`、`rPr`、`tcPr`、`bgPr` 各有自己的顺序），不是简单 append。这一点错了 PowerPoint 会直接报“文件已损坏”。

### 形状样式

`shapes.add_shape()` 默认带一个 `<p:style>` 引用（描边、阴影、字体色都来自主题）。我们显式设置填充和描边后会把 `p:style` 删掉，避免跑出设计之外的阴影和边线。

### 主题

`Presentation()` 打开底版后，取出 `ppt/theme/theme1.xml` 的字节流，用 lxml 改 `clrScheme` 的十二个色槽和 `fontScheme` 的 `majorFont/minorFont`（`latin` + `ea`），再写回部件。这样 `@accent1` 之类的 `schemeClr`、图表默认色、取色器面板都会一致。

## 错误处理

`DslError` 携带元素、行号、文件路径，输出形如：

```
examples/bad.xml:12: Width: invalid length 'wide' <TextBlock>
```

解析阶段能定位的错误：未知元素、未知属性（XSD）、非法单位、未知样式名、未知颜色、图片不存在、图表没有序列。布局阶段能定位的错误：非法对齐值、非法厚度。

## 质量保障

1. **XSD** 保证结构和属性名正确，编辑器里能实时提示。
2. **单元测试** 覆盖单位换算、断行、五种容器的几何、样式优先级、XSD、主题注入、东亚字体、图片裁剪。
3. **产物自检** 每次 build 都跑：zip 完整、`[Content_Types].xml`、每页 XML 可解析、媒体非空、`python-pptx` 可重开、每页至少一个形状。
4. **视觉回归** 用本机 PowerPoint COM 把每页导出 PNG（`tools/export_png.ps1`），人工或截图对比。这一步抓到过表格边框 `schemeClr` 大小写错误、卡片文字溢出、数字跨列重叠等问题。

## 决策记录

**为什么在 Python 里实现 WPF 布局，而不是跑一个 .NET host。** 项目本身是 Python 工具链，布局 IR 已经和渲染解耦；同语义重写能单测、无运行时依赖、跨平台。如果以后需要像素级对齐 WPF，可以把 `layout` 的输出换成 .NET 侧算好的 JSON，其余不用动。

**为什么不做 flexbox。** 目标场景是固定画布上的版式，WPF 的 Grid/StackPanel 已经够用，而且 `*`/`Auto` 的语义比 flex 的 `grow/shrink/basis` 更贴近 PowerPoint 的使用习惯。

**为什么百分比只相对父内容盒。** 嵌套百分比在高度不确定时会变成循环依赖；WPF 也没有百分比尺寸，这里只作为便利功能，父高度为 `Auto` 时百分比高度直接退化为内容高度。

**为什么保留 `Canvas`。** 封面、装饰、背景形状需要绝对定位，`Grid` 表达不了负偏移和出血。

## 扩展点

* `render/slide.py::render_element`：新增元素类型只需要在这里加一个分支。
* `layout.py::_measure_content` / `_arrange_content`：新增容器只需要实现这两处。
* `pipeline.py`：布局结果可以序列化成 JSON/SVG，做预览或 golden 测试。
* `Theme`：支持多套预设主题，或者从外部 JSON 读设计 token。

## 已知风险

* 字体度量依赖本机字体文件；缺字体时退化为启发式宽度，中文版式会偏。
* 文本测量与 PowerPoint 的断行有细微差异，关键页面需要留余量。
* `*` 行在高度不受限的父级里会塌陷，这是 WPF 语义本身的行为，需要文档提示。
* 表格单元格不支持嵌套布局（只渲染文本）。
* 组合形状（`Group`）没有实现，`p:grpSp` 的子坐标系处理成本较高。
