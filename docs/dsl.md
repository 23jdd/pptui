# DSL 参考

上手教程见 [tutorial.md](tutorial.md)；这份文档是逐项查属性用的。

结构定义在 [`pptui/schema/pptui.xsd`](../pptui/schema/pptui.xsd)，编辑器里给根节点加一行即可获得补全和实时校验（路径按你的文件位置调整）：

```xml
<Deck xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:noNamespaceSchemaLocation="../pptui/schema/pptui.xsd">
```

一份 deck 就是一个 XML 文件。根节点 `<Deck>`，下面是元数据、主题、样式和若干 `<Slide>`。

## 单位

长度必须带单位，也接受裸数字（按 pt 处理）：

| 写法 | 含义 |
|---|---|
| `1in` / `2.54cm` / `72pt` / `25.4mm` / `96px` / `914400emu` | 绝对长度 |
| `50%` | 相对父容器内容盒 |
| `Auto` | 由内容决定 |

`Margin="0.5in"`、`Margin="10pt 20pt"`（上下、左右）、`Margin="1,2,3,4"`（左上右下）都可以。

字号只写数字即 pt：`FontSize="18"`。

## 颜色

| 写法 | 生成 | 说明 |
|---|---|---|
| `#2563EB` | `a:srgbClr` | 固定色 |
| `#2563EBCC` | `a:srgbClr` + `a:alpha` | 末两位是透明度 |
| `@accent1` | `a:schemeClr` | 主题色，随主题变化 |
| `$brand` | 解析成命名色 | 引用 `<Styles>` 里定义的 `Color` |
| `None` / `transparent` | `a:noFill` | 仅用于填充 |

主题色键：`dk1`、`lt1`、`dk2`、`lt2`、`accent1`…`accent6`、`hlink`、`folHlink`，另可用别名 `text1`、`background1`、`text2`、`background2`。

## Deck

```xml
<Deck Width="13.333in" Height="7.5in"
      Template="templates/base.pptx"
      FontFamily="Calibri" EastAsianFontFamily="Microsoft YaHei" Foreground="@text1">
  <Meta Title="..." Author="..." Subject="..." Keywords="..." Comments="..." Category="..."/>
  <Theme MinorFont="Calibri" MinorEastAsianFont="Microsoft YaHei"
         MajorFont="Cambria" MajorEastAsianFont="Microsoft YaHei">
    <Color Key="accent1" Value="#2563EB"/>
  </Theme>
  <Styles>
    <Style Key="h1" FontSize="40" FontWeight="Bold" Foreground="@dk1"/>
    <Style TargetType="TextBlock" FontSize="16"/>
    <Color Key="brand" Value="#1E2761"/>
  </Styles>
  <Slide>...</Slide>
</Deck>
```

`Width` / `Height` 省略时是 16:9（12192000 × 6858000 EMU）。

`Template` 指定底版 `.pptx`（相对 XML 文件或绝对路径），用来带自己的母版、版式和主题；底版里不要放示例幻灯片，否则它们会一起进入产物。

`FontFamily`、`EastAsianFontFamily`、`Foreground` 会沿元素树向下继承，写在 `Deck` 上就是全局默认。

## Slide

| 属性 | 说明 |
|---|---|
| `Layout` | 版式名，匹配不到时回退 `Blank` |
| `Background` | 页面底色，颜色写法同上 |
| `Notes` | 演讲者备注 |
| `Name` | 调试用名字 |

`Slide` 可以直接放一个根布局元素，也可以放多个（多个时按整页重叠摆放，适合背景形状 + 内容）。

## 通用布局属性

所有可视元素都支持：

`Width`、`Height`、`MinWidth`、`MaxWidth`、`MinHeight`、`MaxHeight`、`Margin`、`HorizontalAlignment`（`Left|Center|Right|Stretch`）、`VerticalAlignment`（`Top|Center|Bottom|Stretch`）、`Name`、`Style`。

默认对齐是 `Stretch`，和 WPF 一致；但显式给了 `Width`/`Height` 时按给定尺寸，不再拉伸。

## 容器

### Canvas

绝对定位。子元素用 `Canvas.Left` / `Canvas.Top`，可以给负数，超出页面的部分由幻灯片边界裁掉。

```xml
<Canvas>
  <Ellipse Canvas.Left="10.1in" Canvas.Top="-1.9in" Width="5.6in" Height="5.6in" Fill="#22356B"/>
  <TextBlock Canvas.Left="0.9in" Canvas.Top="2in" Width="8in" FontSize="54">标题</TextBlock>
</Canvas>
```

`Canvas` 自身不产生尺寸（和 WPF 一样），作为根元素时会拉满整页。里面的文本没有宽度约束，长文本不会换行，记得给 `Width`。

### StackPanel

`Orientation="Vertical"`（默认）或 `Horizontal`，`Spacing` 是子元素之间的固定间距。

```xml
<StackPanel Spacing="0.2in">
  <TextBlock FontSize="20">第一行</TextBlock>
  <TextBlock FontSize="14">第二行</TextBlock>
</StackPanel>
```

主轴方向给子元素无限空间，交叉轴拉伸到面板宽度。

### Grid

```xml
<Grid>
  <Grid.RowDefinitions>
    <RowDefinition Height="Auto"/>
    <RowDefinition Height="*"/>
  </Grid.RowDefinitions>
  <Grid.ColumnDefinitions>
    <ColumnDefinition Width="1.15*"/>
    <ColumnDefinition Width="1*"/>
  </Grid.ColumnDefinitions>
  <TextBlock Grid.Row="0" Grid.Column="0" Text="标题"/>
  <Chart Grid.Row="1" Grid.Column="1" Grid.ColumnSpan="2" .../>
</Grid>
```

尺寸类型：`Auto`（量内容）、`*` / `2*`（按权重分配剩余空间）、固定长度。没有写定义时是单行单列 `*`。跨行跨列用 `Grid.RowSpan` / `Grid.ColumnSpan`。

分配顺序：固定 → Auto → 剩余空间按 `*` 权重分。`*` 行需要父高度确定；放在高度不受限的 `StackPanel` 里会塌成 0，这种场景请用 `Auto` 或 `Border + Padding`。

### Border

`Padding` 内缩子元素，`Background` 画底、`BorderBrush` + `BorderThickness` 画描边，常用来做卡片：

```xml
<Border Padding="0.34in" Background="@lt2" RadiusX="0.14in">
  <StackPanel Spacing="0.12in">
    <TextBlock FontSize="30" FontWeight="Bold" Foreground="@accent1">01</TextBlock>
    <TextBlock FontSize="20" FontWeight="Bold">需求侧回暖</TextBlock>
    <TextBlock FontSize="15">正文…</TextBlock>
  </StackPanel>
</Border>
```

`RadiusX` 转成圆角矩形的 `adjustments[0]`。

### Padding 到底谁能用

WPF 里 `Padding` 不是面板的属性：`Grid`、`StackPanel`、`Canvas`、`DockPanel`、`WrapPanel` 都没有，`Padding` 属于 `Border`、`Control` 和 `TextBlock`。这里按同样规则支持四类：

| 元素 | 语义 |
|---|---|
| `Border` | 内缩唯一子元素；`BorderThickness` 在外、`Padding` 在内 |
| `TextBlock` | 文本相对文本框的内缩；换行宽度 = 可用宽度 − 左右 Padding，期望高度把上下 Padding 算进去；渲染成 `a:bodyPr` 的四边 inset |
| `List` | 同上，项目符号和文本一起内缩 |
| `Cell` | 单元格内边距，覆盖表格的 `CellPadding` |

面板上写 `Padding` 会直接报错而不是静默忽略，提示套一层 `Border`：

```text
deck.xml:12: Padding is not supported on <Grid>; wrap it in a <Border> or use Margin <Grid>
```

### DockPanel

`DockPanel.Dock="Top|Bottom|Left|Right"`，最后一个子元素默认填满剩余空间（`LastChildFill="True"`）。做页眉页脚、侧边栏比较方便。

## 文本

```xml
<TextBlock Width="6in" FontSize="16" Foreground="@dk2" LineHeight="24"
           TextWrapping="Wrap" TextAlignment="Left" AutoFit="Shrink">
  正文，可以写 <Run FontWeight="Bold" Foreground="@accent1">强调</Run>，
  也可以换行<LineBreak/>继续。
</TextBlock>
```

| 属性 | 说明 |
|---|---|
| `Text` | 直接给文本，等价于写在元素内容里 |
| `Padding` | 文本内缩，参与换行宽度和高度计算 |
| `FontFamily` / `EastAsianFontFamily` | 拉丁字体 / 东亚字体，分别写 `a:latin`、`a:ea` |
| `FontSize` | pt |
| `FontWeight` | `Bold`、`SemiBold`、`700`–`900` 视为粗体 |
| `FontStyle` | `Italic` |
| `Foreground` | 文字颜色 |
| `TextAlignment` | `Left|Center|Right|Justify` |
| `TextWrapping` | `Wrap`（默认）/ `NoWrap`。自动宽度（未写 `Width`）且一行放得下时不会换行：这类文本框按测量宽度输出，PowerPoint 的字体度量略有差异就会把最后一个词挤到第二行，所以渲染时写 `wrap="none"`。写了 `Width`、或布局阶段确实折过行的元素仍然按 `Wrap` 输出 |
| `LineHeight` | 固定行距，pt |
| `LetterSpacing` | 字间距，pt |
| `AutoFit` | `Shrink`：溢出时写 `a:normAutofit` 缩字号 |
| `VerticalContentAlignment` | `Top|Center|Bottom` |

空白处理：默认折叠连续空白并去掉块首尾空格；`xml:space="preserve"` 保留原样。该属性沿 XML 树继承，可以写在 `Deck`、`Slide` 或任意元素上，子元素可用 `xml:space="default"` 局部恢复折叠。

`xml:space` 只影响字符数据，不影响 `Margin`、`Padding`、字距和换行。`preserve` 模式下 XML 缩进也可能被当成文本，但以换行开头/结尾的纯排版空白会被去掉。

## 列表

```xml
<List Bullet="Disc" FontSize="15" Indent="0.28in" ItemSpacing="10pt">
  <Item>第一条</Item>
  <Item Level="1">缩进的第二条</Item>
  <Item>第三条</Item>
</List>
```

`Bullet` 取值 `Disc`、`Circle`、`Square`、`Number`、`None`，也可以直接给一个字符。项目符号用原始 XML 写 `a:buChar` / `a:buAutoNum`，python-pptx 没有对应 API。

## 图片

```xml
<Image Source="assets/logo.png" Width="2in" Height="0.6in" Stretch="Uniform"/>
```

`Source` 相对 XML 文件所在目录解析。`Stretch`：`Uniform`（等比放入）、`UniformToFill`（等比填满并裁剪）、`Fill`（拉伸变形）、`None`（原始尺寸居中）。

## 形状

```xml
<Rectangle Fill="@lt2" Stroke="@accent1" StrokeThickness="2pt" RadiusX="0.1in"/>
<Ellipse Fill="#22356B"/>
<RoundedRectangle Fill="@accent1" RadiusX="0.2in"/>
```

不写 `Fill` 就是无填充，不写 `Stroke` 就是无边框（WPF 默认行为）。

## 表格

```xml
<Table BorderBrush="@lt2" BorderThickness="1pt" CellPadding="0.12in" FontSize="15">
  <Table.Columns>
    <Column Width="2.6*"/>
    <Column Width="1.3*"/>
    <Column Width="1.1*"/>
  </Table.Columns>
  <Row Height="0.62in">
    <Cell Background="@dk1" Foreground="@lt1" FontWeight="Bold">业务线</Cell>
    <Cell Background="@dk1" Foreground="@lt1" FontWeight="Bold" TextAlignment="Right">收入</Cell>
    <Cell>负责人</Cell>
  </Row>
  <Row>
    <Cell RowSpan="2" FontWeight="Bold">企业服务</Cell>
    <Cell TextAlignment="Right">4,280</Cell>
    <Cell>陈默</Cell>
  </Row>
</Table>
```

列宽支持 `Auto`、`*`、固定值；行高 `Auto` 时按单元格文本量出来。单元格支持 `Background`、`ColSpan`/`RowSpan`、`TextAlignment`、`VerticalAlignment`、`BorderBrush`、`BorderThickness`、`Padding`，文字样式和 `TextBlock` 相同（`FontSize`、`FontWeight`、`Foreground`、`LineHeight` 等）。

单元格边框 python-pptx 没有 API，按 `a:lnL/lnR/lnT/lnB` 直接写。

## 图表

```xml
<Chart Type="Column" Title="月度营收（万元）" Legend="Bottom" FontSize="12" DataLabels="True">
  <Category>7月</Category>
  <Category>8月</Category>
  <Series Name="目标" Color="@lt2">860,900</Series>
  <Series Name="实际" Color="@accent1">905,932</Series>
</Chart>
```

`Type`：`Column`、`Bar`、`Line`、`Area`、`Pie`、`Doughnut`。`Legend`：`Bottom|Top|Left|Right|None`。数值用逗号或空格分隔；`Series` 也可以写 `Values="1,2,3"`。生成的是原生可编辑图表，不是图片。

饼图/环形图默认显示百分比标签。

## 样式与继承

```xml
<Styles>
  <Style Key="h1" FontSize="40" FontWeight="Bold" Foreground="@dk1" FontFamily="Cambria"/>
  <Style TargetType="TextBlock" FontSize="16"/>
</Styles>
```

优先级从低到高：内置默认值 → 父元素继承（仅字体、字号、前景色、行高、换行、字间距）→ `TargetType` 隐式样式 → `Style="key"` 命名样式 → 元素自身属性。

`Style` 也可以写成 `{StaticResource h1}`。

## 一个完整页面

```xml
<Slide Background="@dk1" Notes="开场 30 秒">
  <Canvas>
    <Ellipse Canvas.Left="10.1in" Canvas.Top="-1.9in" Width="5.6in" Height="5.6in" Fill="#22356B"/>
    <TextBlock Canvas.Left="0.9in" Canvas.Top="1.45in" Width="8in"
               FontSize="12" FontWeight="Bold" Foreground="@accent2" LetterSpacing="2">ANNUAL REVIEW</TextBlock>
    <TextBlock Canvas.Left="0.9in" Canvas.Top="2.05in" Width="8.8in"
               FontFamily="Cambria" FontSize="54" FontWeight="Bold" Foreground="@lt1" LineHeight="68">把增长做厚<LineBreak/>把效率做实</TextBlock>
  </Canvas>
</Slide>
```

## 容易踩的点

* `*` 行/列在高度不受限的父容器里会塌掉，用 `Auto` 或给父一级固定高度。
* `Canvas` 里的文本不换行，必须给 `Width`。
* 百分比宽度相对父容器内容盒，不是页面；嵌套时逐层计算。
* 只写 `FontFamily` 不写 `EastAsianFontFamily`，中文会回退到别的字体。
* `Padding` 只对 `Border`、`TextBlock`、`List`、`Cell` 生效；`Grid`/`StackPanel`/`Canvas`/`DockPanel` 在 WPF 里没有这个属性，写了会直接报错，改用 `Margin` 或外面套一层 `Border`。
* 文本高度是估算的，PowerPoint 的实际断行可能多一行；关键页面留 5% 余量或用 `AutoFit="Shrink"`。
* `Cell` 的 `Padding` 会覆盖表格的 `CellPadding`，两者只影响单元格内边距，不影响列宽。
