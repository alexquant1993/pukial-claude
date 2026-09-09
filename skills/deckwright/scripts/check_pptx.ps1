# Open a deck twice through PowerPoint COM. Opening once proves little: a
# package PowerPoint silently repairs opens fine the first time. In the
# source engagement this was a manual practice - the script opened once and
# was invoked twice. Here the second open is the script's job.
#
# Requires Windows with PowerPoint installed.
#
# -Save: on pass 1 only, open writable, force the presentation DIRTY, save,
# then close - so the gate can observe what PowerPoint actually does to a
# package a human has "edited" (catalogue item 1), rather than assert it.
#
# The force-dirty step is not optional theatre. A freshly-opened, unmodified
# presentation already reports Saved = msoTrue, and Presentation.Save() on a
# clean presentation is a no-op: it writes nothing and the file on disk is
# byte-identical afterwards. An earlier version of this switch called
# .Save() straight after Open() and reported CHECK PASSED against exactly
# that no-op, which is how a false "fonts survive a PowerPoint save" ruling
# made it into docs/decisions.md - .Saved never went to msoFalse before
# .Save() was called, so nothing was ever written. This version reports
# .Saved before and after, and fails outright if the dirty-forcing step did
# not actually leave the presentation dirty, so a silent no-op cannot pass
# again. Pass 2 always opens read-only, so the doubled-open contract this
# script exists for is unchanged.
param([Parameter(Mandatory=$true)][string]$Path, [switch]$Save)
$ErrorActionPreference = "Stop"
$full = (Resolve-Path $Path).Path

for ($pass = 1; $pass -le 2; $pass++) {
  $pp = New-Object -ComObject PowerPoint.Application
  $pr = $null
  $failed = $false
  try {
    $writable = $Save -and ($pass -eq 1)
    $pr = $pp.Presentations.Open($full, (-not $writable), $false, $false)
    if ($writable) {
      Write-Output ("pass {0}: Saved before force-dirty = {1}" -f $pass, $pr.Saved)
      # The canonical way to force dirty. If .Saved turns out to be
      # read-only on some build - EmbedTrueTypeFonts was, on this one, so
      # nothing about this COM surface is assumed present - fall back to a
      # real, reversed edit: add a shape and delete it again.
      try {
        $pr.Saved = $false
      } catch {
        $shp = $pr.Slides.Item(1).Shapes.AddTextbox(1, 0, 0, 10, 10)
        $shp.Delete()
      }
      if ($pr.Saved -ne 0) {
        throw ("could not force the presentation dirty before -Save; " +
               "Saved is still {0} - Save() would be a no-op and this check " +
               "would silently pass a save that never happened" -f $pr.Saved)
      }
      $pr.Save()
      Write-Output ("pass {0}: Saved after Save() = {1}" -f $pass, $pr.Saved)
    }
    $hidden = @()
    for ($i = 1; $i -le $pr.Slides.Count; $i++) {
      if ($pr.Slides.Item($i).SlideShowTransition.Hidden -ne 0) { $hidden += $i }
    }
    Write-Output ("pass {0}: OPEN_OK slides={1} hidden={2}" -f $pass, $pr.Slides.Count, ($hidden -join ","))
  } catch {
    Write-Output ("pass {0}: FAILED {1}" -f $pass, $_.Exception.Message)
    $failed = $true
  } finally {
    # Under -Save the presentation is deliberately left dirty by design, so
    # a plain Close() (or Quit() below) can raise the interactive "Save
    # changes?" prompt - which a -NonInteractive gate cannot answer and
    # would hang on forever. Forcing Saved back to true before closing
    # means the close is always silent, on both the success and the
    # failure path - a throw between Open() and the normal Close() above
    # (the force-dirty throw, or a failing Save()) must not reach here with
    # the presentation still dirty.
    if ($pr) {
      try { $pr.Saved = $true } catch {}
      try { $pr.Close() } catch {}
    }
    $pp.Quit()
  }
  if ($failed) { exit 1 }
}
Write-Output "CHECK PASSED"
