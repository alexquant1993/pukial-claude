# Export every slide to PNG for visual review.
#
# -Expect is the number of slides that must come out. Without it a broken
# export writes nothing, leaves the previous run's images in place, and looks
# exactly like a successful one.
#
# Requires Windows with PowerPoint installed.
param([Parameter(Mandatory=$true)][string]$Path,
      [Parameter(Mandatory=$true)][string]$Out,
      [int]$Expect = 0)
$ErrorActionPreference = "Stop"
$full = (Resolve-Path $Path).Path
if (Test-Path $Out) { Remove-Item -Recurse -Force $Out }
New-Item -ItemType Directory -Force $Out | Out-Null
$outFull = (Resolve-Path $Out).Path

$pp = New-Object -ComObject PowerPoint.Application
try {
  $pr = $pp.Presentations.Open($full, $true, $false, $false)
  $count = $pr.Slides.Count
  for ($i = 1; $i -le $count; $i++) {
    $f = Join-Path $outFull ("s{0:d2}.png" -f $i)
    $pr.Slides.Item($i).Export($f, "PNG", 1600, 900)
  }
  $pr.Close()
} finally { $pp.Quit() }

$written = @(Get-ChildItem -Path $outFull -Filter *.png)
Write-Output ("EXPORTED " + $written.Count + " -> " + $outFull)
if ($written.Count -ne $count) {
  Write-Output ("FAIL: {0} slides but {1} png written" -f $count, $written.Count)
  exit 1
}
if ($Expect -gt 0 -and $count -ne $Expect) {
  Write-Output ("FAIL: expected {0} slides, found {1}" -f $Expect, $count)
  exit 1
}
if ($count -eq 0) { Write-Output "FAIL: nothing exported"; exit 1 }
