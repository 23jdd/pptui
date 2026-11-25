# 从零到一份 deck：pptui 教程

这篇教程从空目录开始，一步步做出可用的幻灯片，最后带你读一遍仓库里的完整示例 [examples/tutorial.xml](../examples/tutorial.xml)。

读完之后你应该能：

- 用 XML 写出封面、卡片页、表格页、图表页；
- 理解 WPF 那套 `Margin/Padding/对齐/Measure` 在这里怎么用；
- 知道排版没对齐时该改哪里、怎么排查；
- 知道哪些东西故意没做。


## 1. 准备环境

项目用 `uv` 管理（仓库里已有 `uv.lock` 和 `.venv`）：

```bash
uv sync
```

没有 uv 的话，用现成的虚拟环境即可：

```bash
# Windows
.venv\Scripts\python -m pptui --help

# macOS / Linux
.venv/bin/python -m pptui --help
```

下文统一写 `python -m pptui`，请替换成上面任意一种。

先确认能跑：

```bash
python -m pptui build examples/hello.xml -o out/hello.pptx
```

输出：

```text
wrote out\hello.pptx (28737 bytes)
```

用 PowerPoint 打开 `out/hello.pptx`，应该看到一张白底、左上角三行文字的页面。到此环境就通了。


## 2. 第一份 deck

把下面这段存成 `hello.xml`：

```xml
<Deck FontFamily="Calibri" EastAsianFontFamily="Microsoft YaHei">
  <Meta Title="Hello pptui"/>
  <Styles>
    <Style Key="eyebrow" FontSize="12" FontWeight="Bold" Foreground="@accent2" LetterSpacing="2"/>
    <Style Key="h1" FontSize="36" FontWeight="Bold" Foreground="@dk1" FontFamily="Cambria"/>
    <Style Key="body" FontSize="15" Foreground="@dk2" LineHeight="24"/>
  </Styles>

  <Slide Background="@dk1">
    <Canvas>
      <TextBlock Canvas.Left="0.9in" Canvas.Top="2.4in" Width="9in" Style="h1" Foreground="@lt1">季度复盘</TextBlock>
      <TextBlock Canvas.Left="0.9in" Canvas.Top="3.5in" Width="9in" FontSize="16" Foreground="#B9C7E6">2026 Q4 · 产品团队</TextBlock>
    </Canvas>
  </Slide>

  <Slide>
    <Border Padding="0.7in">
      <Grid>
        <Grid.RowDefinitions>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
        </Grid.RowDefinitions>
        <StackPanel Grid.Row="0" Spacing="0.08in" Margin="0 0 0 0.4in">
          <TextBlock Style="eyebrow">SUMMARY</TextBlock>
          <TextBlock Style="h1">三件事</TextBlock>
        </StackPanel>
        <StackPanel Grid.Row="1" Spacing="0.2in">
          <TextBlock Style="body">1. 交付周期缩短 30%</TextBlock>
          <TextBlock Style="body">2. 客单价提升 12%</TextBlock>
          <TextBlock Style="body">3. 流失率降到 2.4%</TextBlock>
        </StackPanel>
      </Grid>
    </Border>
  </Slide>
</Deck>
```

```bash
python -m pptui build hello.xml -o out/hello.pptx
```

### 这份 XML 在说什么

| 行 | 作用 |
|---|---|
| `<Deck>` | 文档根。不写 `Width/Height` 时是 16:9（13.333in × 7.5in） |
| `FontFamily` / `EastAsianFontFamily` | 全局拉丁字体 / 中文字体，沿树向下继承 |
| `<Meta>` | 写进 `docProps/core.xml` 的标题、作者等 |
| `<Styles>` | 命名样式，`Style="h1"` 引用 |
| `<Slide>` | 一页。`Background="@dk1"` 是主题深蓝 |
| `<Canvas>` | 绝对定位容器，子元素用 `Canvas.Left/Top` |
| `<Border Padding="0.7in">` | 给整页内容留 0.7in 内边距 |
| `<Grid>` | 两行：标题 `Auto`、正文 `*` |
| `<StackPanel Spacing="...">` | 竖排，固定间距 |

### 产物是什么

`out/hello.pptx` 是一个正常的 pptx：文本是真文本、颜色走主题、字体同时写了 `a:latin` 和 `a:ea`。在 PowerPoint 里可以直接改字、换色、加动画。

生成时还会自检一遍：zip 结构、每页 XML、关系、能否被 `python-pptx` 重开。自检失败会直接报错，不会悄悄给你一个坏文件。


## 3. 坐标与单位

内部全部用 EMU（1in = 914400，1pt = 12700）。写 XML 时可以用更顺手的单位：

| 写法 | 含义 |
|---|---|
| `0.7in` | 英寸 |
| `2.54cm` / `25.4mm` | 厘米 / 毫米 |
| `18pt` | 磅，字号、线宽常用 |
| `96px` | 像素（按 96dpi） |
| `50%` | 相对父容器内容盒 |
| `Auto` | 由内容决定（尺寸类属性） |
| `18` | 裸数字按 pt 处理 |

`Margin` / `Padding` 支持 1、2、4 个值：

```xml
<Border Margin="0.5in"/>                 <!-- 四边 -->
<Border Margin="10pt 20pt"/>             <!-- 上下、左右 -->
<Border Margin="1,2,3,4"/>               <!-- 左、上、右、下 -->
```

字号只写数字就是 pt：`FontSize="15"`。


## 4. 布局：把 WPF 那套搬过来

### 4.1 先记住三条规则

1. **Margin 在元素外面，由父容器扣掉；Padding 在元素里面，由元素自己扣掉。**
2. **默认对齐是 `Stretch`**，会铺满父容器给的槽位；一旦写了 `Width`/`Height`，就按写死的尺寸，不再拉伸。
3. **先量后排**：父容器先问子元素“你要多大”，再决定每个人的位置。所以 `Auto` 能贴合内容，`*` 只能分“剩下的”。

### 4.2 StackPanel：从上往下排

```xml
<StackPanel Spacing="0.2in">
  <TextBlock FontSize="24" FontWeight="Bold">标题</TextBlock>
  <TextBlock FontSize="15" Foreground="@dk2">说明文字</TextBlock>
</StackPanel>
```

- `Orientation="Horizontal"` 改成横排。
- `Spacing` 是子元素之间的固定间距，不是外边距。
- 主轴方向给子元素无限空间，交叉轴拉伸到面板宽度。

### 4.3 Grid：两栏、三栏、页眉正文

```xml
<Grid>
  <Grid.RowDefinitions>
    <RowDefinition Height="Auto"/>
    <RowDefinition Height="*"/>
  </Grid.RowDefinitions>
  <Grid.ColumnDefinitions>
    <ColumnDefinition Width="1.2*"/>
    <ColumnDefinition Width="1*"/>
  </Grid.ColumnDefinitions>

  <TextBlock Grid.Row="0" Grid.ColumnSpan="2" Text="标题"/>
  <Chart Grid.Row="1" Grid.Column="0" .../>
  <StackPanel Grid.Row="1" Grid.Column="1" .../>
</Grid>
```

尺寸三种写法：

| 写法 | 行为 |
|---|---|
| `Auto` | 按内容量出来 |
| `*` / `2*` | 分剩余空间的权重 |
| `1.2in` / `80pt` | 固定 |

分配顺序：**固定 → Auto → 星号**。星号只在父高度确定时才有意义：

```xml
<!-- 错误示范：StackPanel 里没有确定高度，* 行会塌成 0 -->
<StackPanel>
  <Grid>
    <Grid.RowDefinitions><RowDefinition Height="*"/></Grid.RowDefinitions>
    ...
  </Grid>
</StackPanel>
```

这种场景改用 `Auto`，或者外面套 `Border Padding` 让高度定下来。

跨行跨列用 `Grid.RowSpan` / `Grid.ColumnSpan`，从 0 开始数。

### 4.4 Border：卡片和内边距

```xml
<Border Padding="0.3in" Background="@lt2" RadiusX="0.12in">
  <StackPanel Spacing="0.12in">
    <TextBlock FontSize="26" FontWeight="Bold" Foreground="@accent1">01</TextBlock>
    <TextBlock FontSize="19" FontWeight="Bold">内测</TextBlock>
    <TextBlock FontSize="15" Foreground="@dk2">12 月完成种子客户内测。</TextBlock>
  </StackPanel>
</Border>
```

`RadiusX` 控制圆角，`BorderBrush` + `BorderThickness` 画描边。

`Padding` 不是所有元素都有。WPF 里它属于 `Border`、`Control`、`TextBlock`，面板没有。这里对应支持四类：

| 元素 | 语义 |
|---|---|
| `Border` | 内缩子元素 |
| `TextBlock` | 文本内缩，参与换行宽度和高度 |
| `List` | 同上，项目符号一起内缩 |
| `Cell` | 单元格内边距，覆盖表格的 `CellPadding` |

在 `Grid`/`StackPanel`/`Canvas`/`DockPanel` 上写 `Padding` 会直接报错：

```text
hello.xml:12: Padding is not supported on <Grid>; wrap it in a <Border> or use Margin
```

这不是限制，是避免“写了没效果”的静默失败。

### 4.5 Canvas：封面和装饰

```xml
<Canvas>
  <Ellipse Canvas.Left="10.1in" Canvas.Top="-1.9in" Width="5.6in" Height="5.6in" Fill="#22356B"/>
  <TextBlock Canvas.Left="0.9in" Canvas.Top="2.1in" Width="8.8in"
             FontSize="54" FontWeight="Bold" Foreground="@lt1">把增长做厚</TextBlock>
</Canvas>
```

- 坐标可以负数，超出页面的部分会被幻灯片边界裁掉。
- `Canvas` 自己不算尺寸，作为根元素时铺满整页。
- **子元素不会被拉伸**：文本必须给 `Width`，否则会以单行无限宽度去量，长文本不换行。

### 4.6 DockPanel：页眉页脚

```xml
<DockPanel>
  <StackPanel DockPanel.Dock="Top">...</StackPanel>
  <TextBlock DockPanel.Dock="Bottom" Text="页脚"/>
  <Grid>...</Grid>   <!-- 最后一个自动填满剩余空间 -->
</DockPanel>
```

`LastChildFill="False"` 可以关掉最后一项的填充行为。

### 4.7 怎么选

| 想做的事 | 用 |
|---|---|
| 从上到下 / 从左到右排 | `StackPanel` |
| 两栏、三栏、页眉正文 | `Grid` |
| 卡片、内边距、圆角底 | `Border` |
| 封面、绝对定位、出血装饰 | `Canvas` |
| 页眉 + 页脚 + 中间内容 | `DockPanel` |

一个页面可以混着用：`Border` 负责留白，里面放 `Grid`，格子里再放 `StackPanel` 和 `Border` 做卡片。


## 5. 文本

### 5.1 基本属性

```xml
<TextBlock Width="6in" FontSize="16" Foreground="@dk2" LineHeight="24"
           TextAlignment="Left" TextWrapping="Wrap" AutoFit="Shrink">
  正文内容
</TextBlock>
```

| 属性 | 说明 |
|---|---|
| `FontSize` | pt；默认 18 |
| `Foreground` | 默认 `@text1`（主题深色） |
| `FontWeight` | `Bold`、`SemiBold`、`700`–`900` |
| `TextAlignment` | `Left` / `Center` / `Right` / `Justify` |
| `VerticalContentAlignment` | `Top` / `Center` / `Bottom` |
| `LineHeight` | 固定行距，pt；不写按 1.2 倍字号 |
| `TextWrapping` | `Wrap`（默认）/ `NoWrap` |
| `AutoFit` | `Shrink`：放不下时按比例缩字号 |

### 5.2 混排和换行

```xml
<TextBlock FontSize="16">
  普通文字，<Run FontWeight="Bold" Foreground="@accent1">这里是强调</Run>，
  需要断行时用<LineBreak/>这个标签。
</TextBlock>
```

`<Run>` 继承 `TextBlock` 的字体、字号、颜色，只覆盖自己写的属性。

空白处理：连续空白折叠成一个空格，块首尾空格去掉；需要保留时加 `xml:space="preserve"`。

### 5.3 放不下怎么办

PowerPoint 不会把换行结果写回文件，自动高度只能靠字体度量估算。默认 `AutoFit="Shrink"`：测量发现高度或最长单词超框时，写入 `a:normAutofit fontScale`，PowerPoint 打开后按比例缩字号，而不是让文字溢出。

想要更保险：关键页面把框放宽 5%，或者干脆减少字数。文本测量和 PowerPoint 的实际断行可能差一行。

### 5.4 列表

```xml
<List Bullet="Disc" FontSize="15" Indent="0.28in" ItemSpacing="10pt">
  <Item>第一条</Item>
  <Item Level="1">缩进的第二条</Item>
  <Item>第三条</Item>
</List>
```

`Bullet` 支持 `Disc`、`Circle`、`Square`、`Number`、`None`，也可以直接给一个字符。项目符号是原始 XML 的 `a:buChar` / `a:buAutoNum`，因为 python-pptx 没有对应 API。

### 5.5 中文字体

一定要同时写两个字体：

```xml
<Deck FontFamily="Calibri" EastAsianFontFamily="Microsoft YaHei">
```

只写 `FontFamily` 的话，`a:latin` 是 Calibri，中文会走 PowerPoint 的回退逻辑，结果取决于打开文件的机器。两个都写，中文才能稳定用雅黑。

测量时也是分开的：中文按东亚字体量宽度，西文按拉丁字体量。这就是为什么中文排版的换行位置比较准。


## 6. 样式与主题

### 6.1 样式

```xml
<Styles>
  <Style Key="h1" FontSize="38" FontWeight="Bold" Foreground="@dk1" FontFamily="Cambria"/>
  <Style TargetType="TextBlock" FontSize="15" Foreground="@dk2"/>
</Styles>
```

- 有 `Key`：命名样式，元素写 `Style="h1"`（也接受 `{StaticResource h1}`）。
- 只有 `TargetType`：隐式样式，对所有该类型元素生效。
- `Style` 里可以写任意属性，包括 `Margin`、`Width`。

优先级从低到高：

```text
内置默认值 → 父元素继承（字体/字号/前景/行高/换行）→ TargetType 隐式样式 → Style="key" → 元素自身属性
```

所以 `<TextBlock Style="body" FontSize="12">` 最终是 12pt。

### 6.2 主题色

```xml
<TextBlock Foreground="@accent1">蓝色</TextBlock>
<Border Background="@lt2">浅底</Border>
```

`@dk1`、`@lt1`、`@dk2`、`@lt2`、`@accent1`…`@accent6` 会写成 `a:schemeClr`，跟着主题走。也可以用别名 `@text1`、`@background1`。

`#2563EB` 是固定色（`a:srgbClr`），`#2563EBCC` 会额外写透明度。

### 6.3 换主题

```xml
<Theme MajorFont="Cambria" MajorEastAsianFont="Microsoft YaHei"
       MinorFont="Calibri" MinorEastAsianFont="Microsoft YaHei">
  <Color Key="accent1" Value="#2563EB"/>
  <Color Key="accent2" Value="#0EA5E9"/>
</Theme>
```

构建时会改写 `ppt/theme/theme1.xml` 的配色和字体方案，所以 PowerPoint 的取色器、图表默认色、母版都会跟着变。

命名色则是另一套：

```xml
<Styles>
  <Color Key="brand" Value="#1E2761"/>
</Styles>
<TextBlock Foreground="$brand">品牌色</TextBlock>
```


## 7. 图片

```xml
<Image Source="assets/logo.png" Width="2in" Height="0.6in" Stretch="Uniform"/>
```

- `Source` 相对 XML 文件所在目录，找不到会直接报错并给出行号。
- `Stretch`：
  - `Uniform`：等比放进框里，居中（默认）；
  - `UniformToFill`：等比填满，超出部分裁剪；
  - `Fill`：拉伸变形；
  - `None`：按原始尺寸居中。
- 支持 PNG / JPEG / GIF / BMP / TIFF；**SVG 和 WebP 不支持**，需要先转 PNG。
- 图片本身可以带 alpha（透明 PNG），PowerPoint 会保留；XML 层没有额外的透明度属性。


## 8. 表格

```xml
<Table BorderBrush="@lt2" BorderThickness="1pt" CellPadding="0.12in" FontSize="14">
  <Table.Columns>
    <Column Width="2.6*"/>
    <Column Width="1.3*"/>
    <Column Width="1.1*"/>
  </Table.Columns>

  <Row Height="0.6in">
    <Cell Background="@dk1" Foreground="@lt1" FontWeight="Bold">业务线</Cell>
    <Cell Background="@dk1" Foreground="@lt1" FontWeight="Bold" TextAlignment="Right">收入</Cell>
    <Cell Background="@dk1" Foreground="@lt1" FontWeight="Bold">负责人</Cell>
  </Row>
  <Row>
    <Cell FontWeight="Bold">企业服务</Cell>
    <Cell TextAlignment="Right">4,280</Cell>
    <Cell>陈默</Cell>
  </Row>
</Table>
```

要点：

- 列宽支持 `Auto`、`*`、固定值，按和 Grid 一样的顺序分配。
- 行高 `Auto` 时按单元格文本量出来；给了 `Height` 就用固定值。
- 表格默认拉伸填满所在格子，行高会按比例放大。想要紧凑表格，加 `VerticalAlignment="Top"`。
- 单元格支持 `Background`、`ColSpan`、`RowSpan`、`TextAlignment`、`VerticalAlignment`、`BorderBrush`、`BorderThickness`、`Padding`。
- 单元格只渲染文本（可以带 `Run`），不能嵌套布局。
- 行也可以包在 `<Table.Rows>` 里，两种写法等价。

合并示例：

```xml
<Row>
  <Cell RowSpan="2" FontWeight="Bold">企业服务</Cell>
  <Cell>上半年</Cell>
  <Cell TextAlignment="Right">2,100</Cell>
</Row>
<Row>
  <Cell>下半年</Cell>
  <Cell TextAlignment="Right">2,180</Cell>
</Row>
```


## 9. 图表

```xml
<Chart Type="Column" Title="月度营收（万元）" Legend="Bottom" FontSize="12">
  <Category>7月</Category>
  <Category>8月</Category>
  <Category>9月</Category>
  <Series Name="目标" Color="@lt2">860,900,940</Series>
  <Series Name="实际" Color="@accent1">905,932,918</Series>
</Chart>
```

- `Type`：`Column`、`Bar`、`Line`、`Area`、`Pie`、`Doughnut`。
- `Legend`：`Bottom` / `Top` / `Left` / `Right` / `None`。
- `DataLabels="True"` 显示数值；饼图和环形图默认显示百分比。
- 数值用逗号或空格分隔，也可以写 `Values="860,900,940"`。
- 生成的是**原生图表**，双击就能在 PowerPoint 里改数据，不是图片。
- 图表会填满所在格子；不给尺寸时，默认高度是宽度的 0.6 倍。

两栏布局里常用的写法：

```xml
<Grid>
  <Grid.ColumnDefinitions>
    <ColumnDefinition Width="1.15*"/>
    <ColumnDefinition Width="1*"/>
  </Grid.ColumnDefinitions>
  <Chart Grid.Column="0" Margin="0 0 0.4in 0" .../>
  <StackPanel Grid.Column="1">...</StackPanel>
</Grid>
```


## 10. 备注、背景和版式

```xml
<Slide Background="@dk1" Notes="开场 30 秒，先抛结论。" Layout="Blank">
```

- `Notes` 写演讲者备注，进 PowerPoint 的备注栏。
- `Background` 是页面底色，接受主题色和固定色。
- `Layout` 按名称匹配内置版式，找不到就回退 `Blank`。目前所有内容都是自己画的，版式主要影响母版背景。
- 想换整套母版/主题，用 `Template` 指向设计给的 `.pptx`（见下一节）。


## 11. 用设计给的底版

```xml
<Deck Template="templates/brand.pptx">
```

或：

```bash
python -m pptui build deck.xml -o out.pptx --template templates/brand.pptx
```

底版里的母版、版式、主题色会被继承，`<Theme>` 的覆盖仍然生效。**底版里不要放示例幻灯片**，它们会一起进入产物。


## 12. 排查：布局不对时看什么

### 12.1 打印布局结果

```bash
python -m pptui ir hello.xml
```

输出每页每个元素的绝对矩形（EMU）和测量尺寸：

```json
{
  "tag": "Table",
  "rect": [640080, 1840992, 5801801, 3630168],
  "measured": [5801801, 2468880]
}
```

`rect` 是最终位置，`measured` 是内容想要的尺寸。上面这行说明表格被父容器拉高了（2.70in → 3.63in），所以行高会按比例放大。两者差很多时，通常是：

- 父容器没给够空间（`*` 行塌了、`Auto` 被别的内容撑开）；
- 元素写了显式 `Width/Height`；
- 对齐方式不是 `Stretch`。

### 12.2 常见错误信息

```text
deck.xml:12: Width: invalid length 'wide' <TextBlock>
deck.xml:8: unknown element <Vstack>
deck.xml:21: Padding is not supported on <Grid>; wrap it in a <Border> or use Margin
deck.xml:5: Image requires Source <Image>
deck.xml:14: unsupported chart type 'sankey' <Chart>
```

行号来自 XML 解析器，元素名来自模型，改起来很快。

### 12.3 三个高频“看起来没生效”

| 现象 | 原因 |
|---|---|
| 文字不换行、冲出页面 | 在 `Canvas` 里没写 `Width` |
| 卡片高度是 0 / 内容叠在一起 | `*` 行放在了高度不受限的 `StackPanel` 里 |
| `Padding` 写了没反应 | 面板（`Grid`/`StackPanel`/`Canvas`/`DockPanel`）没有 `Padding`，应该用 `Border` |


## 13. 校验与编辑器

XSD 在 [schema/pptui.xsd](../schema/pptui.xsd)。给根节点加一行：

```xml
<Deck xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:noNamespaceSchemaLocation="../schema/pptui.xsd">
```

PyCharm 内置支持；VS Code 需要装 XML 扩展（如 Red Hat XML）才会读取 XSD。编辑器会补全属性名、标出未知元素和属性。命令行侧：

```bash
python -m pptui validate hello.xml     # 只校验，不生成
python -m pptui schema                 # 打印 XSD 路径
```

`build` 默认先做 XSD 校验；调试期想跳过用 `--no-schema`，想连产物自检一起跳过用 `--no-check`。


## 14. 测试和预览

跑单元测试：

```bash
python -m unittest discover -s tests
```

覆盖单位、断行、五种容器的几何、样式优先级、XSD、主题注入、东亚字体、图片裁剪、表格和图表结构。

Windows 上装了 PowerPoint 的话，可以把每页导出 PNG 做视觉检查：

```powershell
powershell -ExecutionPolicy Bypass -File tools/export_png.ps1 -Pptx out/tutorial.pptx -OutDir out/tutorial-png
```

这个脚本走 PowerPoint COM，渲染结果就是用户看到的结果，比 LibreOffice 更可信。


## 15. 完整案例导览

[examples/tutorial.xml](../examples/tutorial.xml) 是一份 5 页的发布计划 deck，把前面所有东西都用了一遍：

| 页 | 内容 | 用到的能力 |
|---|---|---|
| 1 | 封面 | `Canvas` + 负坐标 `Ellipse` + 深色背景 + `LineBreak` 标题 |
| 2 | 三步路线 | `DockPanel` 页眉/页脚 + `Grid` 三列 + `Border` 卡片 |
| 3 | 交付表 + 风险 | `Table` 拉伸填满 + `List` + 底部通栏结论 |
| 4 | 指标 | `Chart`（Line，双系列）+ 右侧大数字 |
| 5 | 结束页 | `Canvas` 绝对定位 |

生成并查看：

```bash
python -m pptui build examples/tutorial.xml -o out/tutorial.pptx
```

第 2 页的关键结构：

```xml
<Border Padding="0.7in">
  <DockPanel>
    <StackPanel DockPanel.Dock="Top">页眉</StackPanel>
    <TextBlock DockPanel.Dock="Bottom">页脚</TextBlock>
    <Grid>                           <!-- 自动填满中间 -->
      <Grid.ColumnDefinitions>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="*"/>
        <ColumnDefinition Width="*"/>
      </Grid.ColumnDefinitions>
      <Border Grid.Column="0" Margin="0 0 0.26in 0" Padding="0.3in" Background="@lt2" RadiusX="0.12in">
        <StackPanel Spacing="0.12in" VerticalAlignment="Center">...</StackPanel>
      </Border>
      ...
    </Grid>
  </DockPanel>
</Border>
```

第 3 页把表格和风险并排，底部再放一条通栏结论：

```xml
<Grid>
  <Grid.RowDefinitions>
    <RowDefinition Height="Auto"/>
    <RowDefinition Height="*"/>
    <RowDefinition Height="Auto"/>
  </Grid.RowDefinitions>
  <Grid.ColumnDefinitions>
    <ColumnDefinition Width="1.3*"/>
    <ColumnDefinition Width="1*"/>
  </Grid.ColumnDefinitions>
  <!-- 标题跨两列，正文两栏，底栏跨两列 -->
  <Table Grid.Row="1" Grid.Column="0" Margin="0 0 0.4in 0.2in" .../>
  <StackPanel Grid.Row="1" Grid.Column="1">...</StackPanel>
  <Border Grid.Row="2" Grid.ColumnSpan="2" ...>关键路径：...</Border>
</Grid>
```

更完整的经营分析示例见 [examples/report.xml](../examples/report.xml)，6 页，包含柱状图、合计行、封面和结束页。


## 16. 常见坑清单

1. `*` 行/列在高度不受限的父容器里会塌成 0；用 `Auto` 或给父级确定高度。
2. `Canvas` 里的文本必须给 `Width`，否则不换行。
3. 百分比宽度相对父容器内容盒，嵌套时逐层计算；父高度 `Auto` 时百分比高度等于内容高度。
4. 只写 `FontFamily` 不写 `EastAsianFontFamily`，中文会回退到不可控字体。
5. `Padding` 只对 `Border`、`TextBlock`、`List`、`Cell` 生效，面板上写会报错。
6. 文本高度是估算的，关键页面留 5% 余量，或者依赖 `AutoFit="Shrink"`。
7. 表格默认拉伸，行高会放大；想紧凑就 `VerticalAlignment="Top"`。
8. 图片路径相对 XML 文件，不是相对当前目录。
9. 底版里不要留示例页。
10. 生成后自检失败通常说明 XML 里有非法值，先看报错行号，不要直接改 pptx。


## 17. 下一步

- 想系统查每个属性：看 [docs/dsl.md](dsl.md)。
- 想知道内部怎么实现、为什么这么选：看 [docs/design.md](design.md)。
- 想扩展新元素：在 `render/slide.py::render_element` 加分支，布局在 `layout.py::_measure_content` / `_arrange_content` 加对应实现。
- 想加实时预览：`ir` 输出的几何已经和 pptx 解耦，可以接一个 SVG/HTML 预览器。
