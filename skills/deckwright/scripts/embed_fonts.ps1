# Embed all TrueType fonts, full character set, through PowerPoint itself.
# The alternative to scripts/embed_fonts.py: correct by construction, but it
# needs the faces installed on the machine and it edits the file in place.
# Usage: powershell -NoProfile -File scripts/embed_fonts.ps1 <path.pptx>
param([Parameter(Mandatory=$true)][string]$Path)
$ErrorActionPreference = "Stop"
$full = (Resolve-Path $Path).Path
$pp = New-Object -ComObject PowerPoint.Application
$pr = $null
try {
  $pr = $pp.Presentations.Open($full, $false, $false, $false)
  $pr.EmbedTrueTypeFonts = $true
  $pr.SaveSubsetFonts = $false   # embed ALL characters, not just the used subset
  $pr.Save()
} finally {
  # A throwing Close() under ErrorActionPreference = "Stop" would skip
  # Quit() below and orphan POWERPNT.EXE - the mirror of check_pptx.ps1's
  # doubled-Quit()/never-Close() problem. Force the presentation clean
  # first (a throw between Open() and Save() above can leave it dirty,
  # which would otherwise raise the interactive "Save changes?" prompt),
  # and never let a failing Close() prevent Quit().
  if ($pr) {
    try { $pr.Saved = $true } catch {}
    try { $pr.Close() } catch {}
  }
  $pp.Quit()
}
Write-Output "embedded fonts -> $full"
