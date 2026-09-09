# The AI horizon deck, spec section 6 as a script: template, contract, open
# twice, build, assert, lint, dump, open twice again, export, and three
# composed strips asserted row by row. Same shape as scripts/gate.ps1, on one
# deck. Exit non-zero on the first failure.
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
  if ($LASTEXITCODE -ne 0) { Write-Output ""; Write-Output "AI HORIZON FAILED at: $name"; exit 1 }
}

# The template faces its own contract and the doubled open before anything is
# built on it: this is the only template in the repository generated from a
# real design system rather than from the test fixture, and "a template
# python-pptx accepts and PowerPoint repairs" is exactly the risk that brings.
Step "template"          { uv @PY python scripts/make_template.py --brand relay --out out/ai-horizon/template.pptx }
Step "template contract" { uv @PY python scripts/inspect_template.py --brand relay out/ai-horizon/template.pptx }
Step "template opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/ai-horizon/template.pptx }

# Shape counts come from the builder's docstring, and its own check() refuses
# to report OK if the saved package disagrees with them.
Step "build"         { uv @PY python examples/ai-horizon/build_ai_horizon.py --template out/ai-horizon/template.pptx --out out/ai-horizon/deck.pptx --notes both --teleprompter out/ai-horizon/teleprompter.html }
# 145 autoshapes and 32 pictures, derived in the builder's docstring and
# confirmed by its own check() against the saved package. What moved when S09
# arrived: one more header rule (9 content slides, not 8), matrix_frame's 3
# column rules and 12 cell rects, 16 capability pills, 3 enabler pills and the
# legend box = +36; one more wordmark and four more row icons = +5.
# Exact, not a ceiling: --min-pictures as well as --max-pictures, so a row
# icon that stops resolving cannot pass under the ceiling.
Step "is native"     { uv @PY python scripts/assert_native.py out/ai-horizon/deck.pptx --autoshapes 145 --min-pictures 32 --max-pictures 32 --no-dangling }
Step "lint"          { uv @PY python scripts/lint_deck.py --deck out/ai-horizon/deck.pptx --rules examples/ai-horizon/lint.toml --expect-checks 8 }
# 387 paragraphs: every text box, every autoshape's own frame (one paragraph
# each, empty or not), the cover's second title paragraph, the nine page
# markers. S09 added 64 of them, derived before the deck was built and
# confirmed by the dump: 36 autoshapes at one paragraph each, plus 7 second
# paragraphs for the amber pills' sublabels, plus 21 text boxes - kicker,
# title, sub, copyright, page marker, 3 column heads, 3 column sublabels, 4
# two-line row labels at 2 paragraphs each, the empty cell's dash and the
# "Enablers" label. Exact, so a deck that dumps nothing fails.
Step "text dump"     { uv @PY python scripts/dump_text.py --deck out/ai-horizon/deck.pptx --out out/ai-horizon/text.txt --expect-paragraphs 387 }
Step "opens twice"   { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/ai-horizon/deck.pptx }
Step "export png"    { powershell -NoProfile -File scripts/export_png.ps1 -Path out/ai-horizon/deck.pptx -Out out/ai-horizon/png -Expect 10 }

# The footer band, design y 672..688, PNG 840..860. Every slide carries it,
# the cover included: Relay puts the wordmark in the footer of every slide
# type, so there is no blank row here. Ten rows now, not nine.
Step "compose band"  { uv @PY python scripts/compose_qa.py band --png-dir out/ai-horizon/png --box 0,836,1600,900 --expect 10 --out out/ai-horizon/qa/band.png }
Step "band shows the footer on every slide" { uv @PY python scripts/compose_qa.py ink --image out/ai-horizon/qa/band.png --rows 10 --gutter 200 --inked 1,2,3,4,5,6,7,8,9,10 }
# The page marker, design x 1140..1200, PNG 1425..1500. The cover carries no
# printed number and its ground is #0A0A0A, so its crop is uniformly one
# colour and reads blank; every content slide must not.
Step "compose page marker" { uv @PY python scripts/compose_qa.py zoom --png-dir out/ai-horizon/png --slides 1,2,3,4,5,6,7,8,9,10 --box 1400,840,1600,900 --scale 2 --out out/ai-horizon/qa/page.png }
Step "the cover is unnumbered and every other slide is not" { uv @PY python scripts/compose_qa.py ink --image out/ai-horizon/qa/page.png --rows 10 --gutter 130 --blank 1 --inked 2,3,4,5,6,7,8,9,10 }
# The four horizon slides share one layout: the 3 px statement rule sits at
# design y 190 (PNG 237) and the oversized numeral under it on all four, so
# the same crop must carry ink on every row.
Step "compose statement row" { uv @PY python scripts/compose_qa.py zoom --png-dir out/ai-horizon/png --slides 4,5,6,7 --box 100,230,1500,340 --scale 1 --out out/ai-horizon/qa/statement.png }
Step "the statement row is drawn on all four" { uv @PY python scripts/compose_qa.py ink --image out/ai-horizon/qa/statement.png --rows 4 --gutter 130 --inked 1,2,3,4 }

Write-Output ""
Write-Output "AI HORIZON PASSED"
