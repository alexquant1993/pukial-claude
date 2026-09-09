# The AI horizon deck as an HTML deliverable: the loop a spec whose
# **Output:** line says `html` runs. Same drafts, no PowerPoint, no Windows.
#
#   stage page  -> out/ai-horizon/html/index.html, navigable and printable
#   lint        -> the same rules file the PPTX deck uses, seven checks
#                  (notes_only is skipped: drafts carry no speaker notes)
#   capture     -> one sNN.png per draft, through whichever browser route works
#   compose     -> the same footer band and page marker asserted row by row
#
# No step here is allowed to skip. The capture used to be: it printed a
# browser instruction and exited 0 when Playwright was not importable, and
# the two composition steps then reported SKIPPED while this script still
# said PASSED - ten drafts nobody had looked at, and a green gate.
# capture_drafts.py now drives any Chromium-family binary it can find
# (references/02-html-stage.md#capturing), so on a machine with a browser
# this step PASSES by actually capturing, and on a machine with none it
# FAILS with CAPTURE UNAVAILABLE and three remedies.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$PY = @("run", "--offline", "--no-project", "--with", "python-pptx", "--with", "pillow")

function Step($name, $block) {
  Write-Output ""
  Write-Output "=== $name"
  $global:LASTEXITCODE = 0
  try { & $block } catch { Write-Output $_; $global:LASTEXITCODE = 1 }
  if ($LASTEXITCODE -ne 0) { Write-Output ""; Write-Output "AI HORIZON HTML FAILED at: $name"; exit 1 }
}

# --expect-slides 10 is exact: a glob that matched four drafts of ten builds
# a four-slide deck that looks exactly like a successful build.
Step "stage page" { uv @PY python scripts/build_html_deck.py --drafts examples/ai-horizon/drafts --out out/ai-horizon/html --title "AI and humanity, 2026 to 2050 and beyond" --expect-slides 10 }

# The stage page must carry every slide, no external resource, and the print
# rule. Asserted here rather than trusted, because "it wrote a file" is what
# a broken build looks like too.
Step "stage page is a deck" {
  $page = Get-Content out/ai-horizon/html/index.html -Raw
  $slides = ([regex]::Matches($page, 'class="dw-slide"')).Count
  if ($slides -ne 10) { throw "expected 10 slides on the stage page, found $slides" }
  if ($page -match 'src="https?:' -or $page -match 'href="https?:' -or $page -match 'url\(\s*["'']?https?:') {
    throw "the stage page links an external resource"
  }
  if ($page -notmatch '@page') { throw "the stage page carries no print rule" }
}

# Seven, not eight: notes_only is skipped with a reason on a drafts
# directory. The rules file is the deck's own - one set of content
# constraints, whichever output is being shipped.
Step "lint the drafts" { uv @PY python scripts/lint_deck.py --deck examples/ai-horizon/drafts --rules examples/ai-horizon/lint.toml --expect-checks 7 }

Step "capture the drafts" { uv @PY python scripts/capture_drafts.py --drafts examples/ai-horizon/drafts --out out/ai-horizon/png_html --root . --expect 10 }

# Exact, not a floor. capture_drafts.py verifies each PNG's size before it
# counts it, so this is the count check the composition steps below assume.
Step "ten captures exist" {
  $pngs = @(Get-ChildItem out/ai-horizon/png_html/s[0-9][0-9].png -ErrorAction SilentlyContinue)
  if ($pngs.Count -ne 10) { throw "expected 10 captures in out/ai-horizon/png_html, found $($pngs.Count)" }
}

# Identical boxes to examples/ai-horizon/run.ps1's, because the captures
# are the same 1600x900 the PPTX export writes: design y 672..688 is PNG
# 840..860, and the page marker's design x 1140..1200 is PNG 1425..1500.
Step "compose band"  { uv @PY python scripts/compose_qa.py band --png-dir out/ai-horizon/png_html --box 0,836,1600,900 --expect 10 --out out/ai-horizon/qa_html/band.png }
Step "band shows the footer on every slide" { uv @PY python scripts/compose_qa.py ink --image out/ai-horizon/qa_html/band.png --rows 10 --gutter 200 --inked 1,2,3,4,5,6,7,8,9,10 }
Step "compose page marker" { uv @PY python scripts/compose_qa.py zoom --png-dir out/ai-horizon/png_html --slides 1,2,3,4,5,6,7,8,9,10 --box 1400,840,1600,900 --scale 2 --out out/ai-horizon/qa_html/page.png }
Step "the cover is unnumbered and every other slide is not" { uv @PY python scripts/compose_qa.py ink --image out/ai-horizon/qa_html/page.png --rows 10 --gutter 130 --blank 1 --inked 2,3,4,5,6,7,8,9,10 }

Write-Output ""
Write-Output "AI HORIZON HTML PASSED"
