param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [int]$Width = 1600,
    [int]$Height = 900
)

$ErrorActionPreference = 'Stop'
$source = (Resolve-Path $Pptx).Path
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$target = (Resolve-Path $OutDir).Path

$app = New-Object -ComObject PowerPoint.Application
try {
    $pres = $app.Presentations.Open($source, $true, $false, $false)
    $count = $pres.Slides.Count
    for ($i = 1; $i -le $count; $i++) {
        $path = Join-Path $target ('slide-{0:00}.png' -f $i)
        $pres.Slides.Item($i).Export($path, 'PNG', $Width, $Height)
    }
    $pres.Close()
    Write-Output "exported $count slides to $target"
}
finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
