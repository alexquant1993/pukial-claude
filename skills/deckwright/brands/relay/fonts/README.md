# Fonts

Relay's own three families, fetched rather than substituted. All six files
here are downloaded by `scripts/fetch_fonts.py --brand relay` against the
hashes pinned in `../fonts.toml`, and each carries its licence text
alongside.

| Role | Family | Files | Upstream | Licence |
| --- | --- | --- | --- | --- |
| display | Space Grotesk | `SpaceGrotesk-Regular.ttf`, `SpaceGrotesk-Bold.ttf` | `floriankarsten/space-grotesk` 2.0.0, `fonts/ttf/static/` | OFL 1.1, `SpaceGrotesk-OFL.txt` |
| sans | Public Sans | `PublicSans-Regular.ttf`, `PublicSans-Bold.ttf` | `uswds/public-sans` v2.001, `fonts/ttf/` | OFL 1.1, `PublicSans-LICENSE.md` |
| mono | JetBrains Mono | `JetBrainsMono-Regular.ttf`, `JetBrainsMono-Bold.ttf` | `JetBrains/JetBrainsMono` v2.304, `fonts/ttf/` | OFL 1.1, `JetBrainsMono-OFL.txt` |

Every URL is pinned to a release tag, not to a branch, so the bytes behind
it cannot move under the hash. `fetch_fonts.py` refuses any face whose
declared licence is not OFL 1.1: a proprietary face is pointed at by name in
`brand.py` and never copied into this repository.

## Static instances, not the variable file

All three families are published as variable fonts (`SpaceGrotesk[wght].ttf`
and so on), and `deck_kit.metrics.TextMetrics` addresses a family as exactly
two files - a regular and a bold - because `ImageFont.truetype` loads a
variable TTF at its default instance and nothing downstream would know the
bold was not bold. Two of the three upstreams publish the named static
instances next to the variable file; Public Sans and JetBrains Mono ship
statics only. `fontTools.varLib.instancer` was the other route and is not
available: this environment resolves Python packages from the uv cache
offline, and `fonttools` is not in it.

## What this replaced

Until this was written the brand carried `NotoSans-Regular.ttf` and
`NotoSans-Bold.ttf` - one humanist sans standing in for a geometric grotesk,
a neo-grotesque body face and a monospace, because none of Relay's three was
installed on the machine and `uv --offline` could fetch nothing. The
substitution was recorded here and argued for in `../brand.py`, and it cost
the brand most of its likeness: the tracking carried the resemblance and the
letterforms did not, and there was no mono face at all, so a kicker was
uppercase Noto Sans opened up to +0.12em.

The network was reachable the whole time. Nobody had looked.

## Rendering, which is a separate question

These files are what the **builder measures against**; they are not what
PowerPoint draws with. PowerPoint uses the faces Windows knows about, so an
export on a machine where Space Grotesk, Public Sans and JetBrains Mono are
not installed substitutes silently, and the exported PNGs stop being
evidence about where a line breaks. Installing them for the current user
needs no administrator: copy the six `.ttf` files into
`%LOCALAPPDATA%\Microsoft\Windows\Fonts` and add one string value per file
under `HKCU\Software\Microsoft\Windows NT\CurrentVersion\Fonts` naming the
path, then `AddFontResourceW` each one and broadcast `WM_FONTCHANGE` so a
running PowerPoint picks them up.

## The measurement factors

`width_factor` and `wrap_factor` are per face, and `../brand.py`'s docstring
carries the calibration: the method, the observed ratios at two sizes for
all four families, and the arithmetic from a ratio to a factor. The short
version is Space Grotesk 1.11 / 1.06, Public Sans 1.11 / 1.06, JetBrains
Mono 1.12 / 1.07.

Every non-text file in this brand is listed with its hash and provenance in
`../assets.toml`; `scripts/lint_deck.py` fails on any that is not.
