# The deckwright gate: all three phases, one entry point. Runs everything that
# must be true before a phase is done, and exits non-zero on the first failure.
#
# The uv invocation uses --no-project with explicit --with flags: project mode
# cannot resolve offline in this environment, while the ephemeral environment
# reads the same packages straight from the uv cache.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"

$PY = @("run", "--offline", "--no-project", "--with", "python-pptx", "--with", "pillow")
$PYTEST = $PY + @("--with", "pytest", "pytest")
$PYTEST_O = $PY + @("--with", "pytest", "python", "-O", "-m", "pytest")

function Step($name, $block) {
  Write-Output ""
  Write-Output "=== $name"
  # Reset before each step. $LASTEXITCODE is NOT cleared between commands, so
  # a step that fails without running a process at all - uv missing from PATH,
  # a typo, an unwritable path - would otherwise inherit the previous step's 0
  # and report success.
  $global:LASTEXITCODE = 0
  try { & $block } catch { Write-Output $_; $global:LASTEXITCODE = 1 }
  if ($LASTEXITCODE -ne 0) {
    Write-Output ""
    Write-Output "GATE FAILED at: $name"
    exit 1
  }
}

Step "unit tests"        { uv @PYTEST -q }
Step "safety checks survive python -O" { uv @PYTEST_O tests/test_fonts.py tests/test_new_version.py tests/test_deck.py tests/test_textedit.py -q }
Step "template"          { uv @PY python scripts/make_template.py --brand relay --out out/template.pptx }
Step "template contract" { uv @PY python scripts/inspect_template.py --brand relay out/template.pptx }
# The spec names "a template python-pptx accepts and PowerPoint repairs" as a
# risk of this phase, so the template faces the doubled open before anything
# is built on it.
Step "template opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/template.pptx }
Step "build furniture"   { uv @PY python examples/kit-furniture/build_furniture.py --template out/template.pptx --out out/furniture.pptx }
# Exact counts, not floors with slack: at a floor of 5 the furniture slide
# could lose its whole freeform-and-arrowhead pair and still pass. The deck is
# built on brands/relay, whose header() draws ONE wordmark picture in the
# footer where the fixture brand's header drew a two-mark lockup.
#
# The kit's matrix, pills and legend used to be covered here too, by
# examples/capability-matrix - two slides from another engagement kept alive
# only for that coverage. They are covered by the AI horizon deck's S09 now,
# through examples/ai-horizon/run.ps1 at the end of this file, and the example
# directory is deleted; docs/decisions.md, "one deck", has the ruling.
#
# furniture, derived from build_furniture.py. One slide:
#   autoshapes: 1 header rule + 1 gradient rail + 2 boxes + 1 polyline
#     freeform + 1 arrowhead triangle + 1 footer-primitive rule = 7, unchanged.
#   pictures: 1 footer wordmark + 5 conic maturity balls = 6. Was 7.
Step "furniture is native" { uv @PY python scripts/assert_native.py out/furniture.pptx --autoshapes 7 --min-freeforms 1 --min-pictures 6 --max-pictures 6 }
Step "furniture opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/furniture.pptx }
Step "export furniture png"  { powershell -NoProfile -File scripts/export_png.ps1 -Path out/furniture.pptx -Out out/png_furniture -Expect 1 }

# ---- Phase 2: integration round trip ----------------------------------------
# The donor template is a SECOND MASTER, not a second brand. Building both from
# one plain make_template.py run merges a template with itself: the copied
# master is byte-identical to the destination's, the p:sldLayoutId re-mint
# resolves no collision, and the whole master-transplant path - catalogue item
# 5, the reason merge.py exists - is exercised against the easiest possible
# input.
#
# This used to be a second brand package, brands/example2, whose only real
# difference from the host brand was its master and layout names. The
# repository now carries one brand, so --variant donor takes brands/relay's
# own contract and appends " (donor)" to both names, painting the ground in
# the brand's PANEL so the two masters differ visibly as well as by name.
# What that buys, asserted against the generated files by
# tests/test_template.py::test_a_variant_template_is_a_second_master_of_the_same_brand
# in the unit-test step above:
#   - both templates put their master at ppt/slideMasters/slideMaster1.xml,
#     so merge has to mint a free destination part name;
#   - both carry p:sldLayoutId 2147483655 (python-pptx's own), so merge's
#     re-mint resolves a real collision - OBSERVED in out/v2/final.pptx: the
#     copied master comes out as slideMaster2.xml with id 2147483657;
#   - the master and layout NAMES differ, so deck._layout can still resolve a
#     layout by name in the merged deck.
Step "template2"     { uv @PY python scripts/make_template.py --brand relay --variant donor --out out/template2.pptx }
# The second master faces the contract verifier and the doubled open too, for
# the same reason the first does: nothing is built on a template this gate has
# not checked.
Step "template2 contract" { uv @PY python scripts/inspect_template.py --brand relay --variant donor out/template2.pptx }
Step "template2 opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/template2.pptx }

# The font donor for this whole phase is written by deck_kit.fonts.embed, not
# by scripts/embed_fonts.ps1 (COM). The COM route needs $pr.EmbedTrueTypeFonts,
# which this machine's PowerPoint build does not expose on the Presentation
# COM object at all (DISP_E_UNKNOWNNAME, confirmed independently in Task 3 -
# see docs/decisions.md); embed_fonts.ps1 throws immediately and would fail
# the gate on every run regardless of anything Task 9 does. Task 9 measured
# the alternative instead: transplant a deck_kit.fonts.embed donor into a
# plain deck and run the doubled COM check. It passed both opens with no
# repair, so the round trip's font stage stays in, gated on --expect-fonts 2.
# Catalogue item 1 (what PowerPoint does when a human saves) is measured
# separately, below, against the round trip's own final.pptx - not against
# this donor, which the round trip already consumes as an input.
Step "font donor"    { uv @PY python scripts/embed_fonts.py --brand relay --deck out/template.pptx --out out/fontdonor.pptx }
Step "donor opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/fontdonor.pptx }

Step "build host"    { uv @PY python examples/integration/build_host.py --template out/template.pptx --out out/host.pptx }
Step "build donor"   { uv @PY python examples/integration/build_donor.py --template out/template2.pptx --out out/donor.pptx }
Step "round trip"    { uv @PY python examples/integration/version.py --host out/host.pptx --donor out/donor.pptx --fonts out/fontdonor.pptx --work out/v2 }

# Every intermediate faces the integrity check, not only the final file. Phase 1
# skipped the template, which its own risk section had named.
Step "intermediates open" {
  # An exact count first: a glob that matches nothing passes a loop silently,
  # which is the floor-with-slack this phase forbids. step_input.pptx is
  # excluded by the [0-9] class - it is a plain copy of the source, not a step.
  $files = @(Get-ChildItem out/v2/step[0-9]*_*.pptx)
  if ($files.Count -ne 5) { throw "expected 5 intermediates, found $($files.Count)" }
  $files | ForEach-Object {
    powershell -NoProfile -File scripts/check_pptx.ps1 -Path $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "intermediate failed: $($_.Name)" }
  }
}
Step "final opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/v2/final.pptx }
# Shape-count arithmetic, derived before running anything:
#   autoshapes: host slide 6 draws one pill (an rrect, MSO_SHAPE_TYPE.AUTO_SHAPE)
#     behind its text box; nothing else in host slides 1-4 or 6, and nothing in
#     donor slides 1-2, draws an autoshape or a freeform. Total: 1.
#   pictures: donor slide 1 places one picture (Relay's wordmark, the brand's
#     logo_primary); nothing else in host slides 1-4/6 or donor slide 2 adds
#     one - neither builder calls style.header(), which is what would put a
#     wordmark on every slide. Total: 1 - so
#     --min-pictures 1 as well as --max-pictures 1: a ceiling alone would
#     still pass with the donor's picture deleted, which is Phase 1's
#     --min-autoshapes 6 mistake mirrored.
Step "final is native"   { uv @PY python scripts/assert_native.py out/v2/final.pptx --autoshapes 1 --min-pictures 1 --max-pictures 1 --expect-fonts 2 --no-dangling }

# Catalogue item 1 is a claim about what PowerPoint does when a human saves a
# package that carries embedded fonts. An earlier version of this step
# measured nothing: it opened a file and called .Save() straight away, but a
# freshly-opened, unmodified presentation already reports Saved = msoTrue and
# .Save() on a clean presentation is a no-op - the file on disk came back
# byte-identical, and "CHECK PASSED" was proof only that a copy is a copy.
# check_pptx.ps1 -Save now forces the presentation dirty before saving and
# fails outright if that did not work, which makes this a real measurement:
# copy out/v2/final.pptx (7 slides, 2 .fntdata parts, built in this run) and
# save it through COM. OBSERVED (docs/decisions.md): the fonts do not
# survive - 2 parts become 0. --expect-fonts 0 pins that observed result,
# not the round trip's own count.
Step "PowerPoint strips embedded fonts on a real save" {
  Copy-Item out/v2/final.pptx out/saved_by_ppt.pptx -Force
  powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/saved_by_ppt.pptx -Save
  uv @PY python scripts/assert_native.py out/saved_by_ppt.pptx --autoshapes 1 --max-pictures 1 --expect-fonts 0
}

# -Expect 7, not 6: export_png.ps1 sets $count = $pr.Slides.Count and exports
# by index (Slide.Export), which renders hidden slides too - only a
# presentation-level export would skip them, and this script does not do that.
Step "export final png"  { powershell -NoProfile -File scripts/export_png.ps1 -Path out/v2/final.pptx -Out out/png_v2 -Expect 7 }

# ---- Phase 3: the walkthrough - templates filled, notes in both outputs, lint, composition
# Exact values derived from build_walkthrough.py's shape arithmetic before running it.
Step "walkthrough" { uv @PY python examples/walkthrough/build_walkthrough.py --template out/template.pptx --out out/walk/deck.pptx --notes both --teleprompter out/walk/teleprompter.html }
Step "walkthrough is native" { uv @PY python scripts/assert_native.py out/walk/deck.pptx --autoshapes 1 --max-pictures 0 --no-dangling }
Step "walkthrough opens twice" { powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/walk/deck.pptx }
# --expect-paragraphs 10, derived from build_walkthrough.py before running it:
#   cover: 2 text boxes (title, subtitle) = 2
#   slide 2: kicker, title, two body boxes, the rrect pill's own text frame
#     (one empty paragraph, which dump_text emits), the pill label box, the
#     copyright box, and the page marker renumber adds = 8
# Exact, not a floor: without it the step proved only that the script exited
# 0, which a deck that dumps nothing also does.
Step "walkthrough text dump" { uv @PY python scripts/dump_text.py --deck out/walk/deck.pptx --out out/walk/text.txt --expect-paragraphs 10 }
Step "walkthrough lint" { uv @PY python scripts/lint_deck.py --deck out/walk/deck.pptx --rules examples/walkthrough/lint.toml --expect-checks 8 }
Step "export walkthrough png" { powershell -NoProfile -File scripts/export_png.ps1 -Path out/walk/deck.pptx -Out out/png_walk -Expect 2 }
Step "compose band" { uv @PY python scripts/compose_qa.py band --png-dir out/png_walk --box 0,836,1600,900 --expect 2 --out out/qa/band.png }
Step "compose zoom" { uv @PY python scripts/compose_qa.py zoom --png-dir out/png_walk --slides 1,2 --box 1400,840,1600,900 --scale 2 --out out/qa/zoom.png }
Step "band shows the footer" { uv @PY python scripts/compose_qa.py ink --image out/qa/band.png --rows 2 --gutter 200 --blank 1 --inked 2 }
Step "zoom shows the page marker" { uv @PY python scripts/compose_qa.py ink --image out/qa/zoom.png --rows 2 --gutter 130 --blank 1 --inked 2 }

# ---- The AI horizon deck: ten slides in brands/relay ---------------------------
# The longest deck in the repository. Its own script runs the whole of spec
# section 6 -
# template, the contract verifier and the doubled COM open BEFORE anything is
# built on that template, then build with notes, exact shape counts, eight lint
# checks, an exact text dump, the doubled open again, the export, and three
# composed strips asserted row by row - and exits non-zero on the first
# failure, so one step here is the whole run.
#
# There used to be two steps: the same slides in the fixture brand and
# again in brands/relay. The placeholder-brand build was deleted, because two
# builds of one deck proved that a builder can be ported and nothing else.
# The fixture brands themselves are gone now too, so every step in this file
# runs on brands/relay - "the only deck built on a brand that is not the test
# fixture" stopped being a distinction on 2026-09-09.
Step "ai-horizon" { powershell -NoProfile -File examples/ai-horizon/run.ps1 }

# ---- The same deck as an HTML deliverable -------------------------------------
# The spec's **Output:** line can say `html`, and then the drafts ARE the deck:
# build_html_deck.py turns them into one navigable, printable stage page,
# lint_deck.py lints the drafts directory the way it lints a .pptx, and
# capture_drafts.py feeds compose_qa.py the same sNN.png names export_png.ps1
# writes. Nothing in it is allowed to skip. The capture step used to be: it
# exited 0 printing a browser instruction when Playwright was not importable,
# so this step went green over ten drafts nobody had looked at.
# capture_drafts.py now drives whatever Chromium-family binary the machine
# holds - on this one, the ms-playwright build the Playwright MCP server
# installed - and fails with CAPTURE UNAVAILABLE when there is none.
# `python scripts/doctor.py` reports the same requirement before a deck is
# started; docs/decisions.md, "capture is a requirement", has the ruling.
Step "ai-horizon html" { powershell -NoProfile -File examples/ai-horizon/run_html.ps1 }

Write-Output ""
Write-Output "GATE PASSED"
