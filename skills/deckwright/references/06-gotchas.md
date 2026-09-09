# Failure catalogue

Twenty-two failures the source engagement actually paid for (spec section 8),
and one this repository met on its own (item 23).
Each entry is Symptom / Cause / Fix / Pinned by. `Pinned by` names the exact
test or gate step that would fail if the fix were removed - and where nothing
pins an item, it says so instead of naming a plausible-looking test.
`references/04-integration.md` explains the mechanisms these items describe
in prose; this file is the lookup table.

## Fonts and packaging

### 1. PowerPoint strips embedded fonts when a human saves the file

**Symptom:** a deck that opened fine, and rendered in the right typeface,
falls back to a substitute font after the author saves it once in PowerPoint.
**Cause:** `Presentation.Save()` on a package carrying embedded fonts
re-derives the embedded-font list from what PowerPoint can itself re-embed
from locally installed faces; it does not pass foreign font bytes through
unchanged, and for a raw-sfnt donor it discards the whole apparatus rather
than repairing or ignoring it. **Fix:** every generated version re-embeds
fonts as its last step (`fonts.transplant`), because the file the author
saves next will strip them again. **Pinned by:** the `scripts/gate.ps1` step
`"PowerPoint strips embedded fonts on a real save"` - not a pytest test. It
copies the round trip's own `out/v2/final.pptx` (2 `.fntdata` parts), forces
it dirty through `scripts/check_pptx.ps1 -Save` (a real COM save, not the
no-op an unmodified `.Save()` would be), and asserts the saved copy carries
`--expect-fonts 0` via `scripts/assert_native.py`. This was measured, not
assumed: an earlier version of this step called `.Save()` on a
freshly-opened, unmodified file and observed nothing, because `.Saved` was
already `msoTrue` and `.Save()` is a documented no-op on a clean
presentation - that version is the corrected ruling in `docs/decisions.md`.
On the corrected measurement, raw-sfnt donor parts go 2 -> 0 on a real save;
a control run against a copy of the source engagement's own deck, carrying
21 genuine PowerPoint-EOT font parts, goes 21 -> 16 with every surviving part
rewritten - PowerPoint parses real EOT parts and regenerates the list from
what it can re-embed locally, but does not parse raw sfnt at all.

### 2. Font transplant is not a file copy

**Symptom:** a hand-built or naively-scripted transplant produces a package
PowerPoint repairs, or silently ignores the copied fonts. **Cause:** the
`<p:embeddedFontLst>` block has to land at a specific point in
`ppt/presentation.xml`, its relationship ids are donor-local and collide with
the destination's own numbering if copied verbatim, and
`[Content_Types].xml` needs a `Default` for the `fntdata` extension or the
parts have no declared content type at all. **Fix:** `fonts.transplant`
splices the block immediately after `<p:notesSz/>` (`_splice`), re-mints
every relationship id against the destination's `presentation.xml.rels`
(`_add_font_rels`), and adds the `fntdata` content-type default
(`_content_type_default`) if it is not already present. **Pinned by:**
`tests/test_fonts.py::test_embedded_font_list_lands_after_notesSz_with_reminted_rids`
- it asserts the splice position, that no relationship id collides, and that
the content-type default and `dangling_refs` are both clean. This is a unit
test against a fixture donor built by `fonts.embed`, not a COM measurement -
the gate does not exercise this path through real PowerPoint, because COM
font embedding is unavailable on the machine this phase was built on (see
item 4).

### 3. `[Content_Types].xml` goes first when writing a pptx package by hand

**Symptom:** none recorded from the source repository - this is a convention
every writer there honoured, not a diagnosed bug. **Cause:** unstated by the
source material; kept as a convention rather than relaxed. **Fix:**
`merge.write_package` always writes `[Content_Types].xml` as the first entry
in the zip. **Pinned by:**
`tests/test_merge.py::test_content_types_is_the_first_entry_in_the_package`.

### 4. Embed the full character set, not a subset

**Symptom:** a deck renders correctly on the day it is embedded, then shows
boxes for any character a later editor types that was not already in the
subset. **Cause:** the source's documented reason is only "embed ALL
characters, not just used subset" - `SaveSubsetFonts = $false` on the COM
donor route. **Fix:** never subset when embedding; the recorded reason is the
only justification this catalogue carries. **Pinned by:** nothing. This is a
property of the COM `SaveSubsetFonts = $false` route specifically
(`scripts/embed_fonts.ps1`), and that route is unusable on the machine this
phase was built on - `$pr.EmbedTrueTypeFonts` does not exist on this
PowerPoint build's automation surface (`DISP_E_UNKNOWNNAME`), confirmed
through two independent COM binding mechanisms (late-bound `InvokeMember` as
well as the direct property access). `tests/test_fonts.py`'s own
`test_embed_writes_each_face_as_its_own_part` says explicitly in its
docstring that it is not this item: `fonts.embed` is a byte copy of whatever
TTF it is given, so nothing in this module can produce or detect a subset
either way. What would pin this item: run `scripts/embed_fonts.ps1` on a
machine whose PowerPoint build does expose `EmbedTrueTypeFonts`, embed a face
using only a handful of glyphs from a full source TTF, and confirm the
resulting `.fntdata` part still carries the full character set rather than
only the glyphs used in the deck at embed time.

## OOXML surgery

### 5. Relationship ids are part-local; presentation-scope ids are not

**Symptom:** a transplanted slide's layout or master silently collides with
one already in the destination, or PowerPoint repairs the file on open.
**Cause:** copied parts can keep their own relationship ids unchanged - only
relationship *targets* need rewriting - but `p:sldId`, `p:sldMasterId` and
`p:sldLayoutId` values must be unique across the whole presentation, and the
`p:sldLayoutId` values live inside the copied slide **master** parts, not in
`ppt/presentation.xml`. **Fix:** `merge()` re-mints every `p:sldLayoutId`
found inside a newly-copied master part, above the maximum id already in use
anywhere in the destination. **Pinned by:**
`tests/test_merge.py::test_copied_master_layout_ids_do_not_collide_with_the_destination`.

### 6. Notes slides and modern comments are bound to the source package

**Symptom:** a transplanted slide carries a dangling reference to a notes
master or comment author list the destination does not have, and PowerPoint
reports the file needs repair. **Cause:** the notes slide relationship is
bound to the source's own notes master; a modern-comment anchor
(`<p:ext uri="{6950BFC3-...}">` inside the slide XML) is bound to the
source's author list. **Fix:** `merge()`'s `DROP_TYPES` set excludes
`notesSlide`, `comments` and `commentAuthors` relationships from the
transitive part-collection walk, and `_clean_slide` strips the comment anchor
extension out of the slide XML itself, not just the relationship pointing to
it. **Pinned by:**
`tests/test_merge.py::test_notes_and_comments_are_dropped_and_leave_no_dangling_rid`.

### 7. A slide's hidden flag lives on the slide root, not in presentation.xml

**Symptom:** a slide meant to be hidden shows during a slideshow, or a
transplant tool that only edits `p:sldId` in `presentation.xml` has no effect
at all. **Cause:** `show="0"` is an attribute of the `<p:sld>` root element of
the slide's own part; `p:sldId` in `presentation.xml` carries no visibility
information. Established empirically against PowerPoint COM, per D10.
**Fix:** `merge()` sets or inserts `show="0"` on the copied slide's own
`<p:sld>` tag. **Pinned by:**
`tests/test_merge.py::test_hidden_flag_is_on_the_slide_root_not_on_sldId`.

### 8. Deleting an animation target makes the file unopenable, not repairable

**Symptom:** a deck that opened fine now fails automation-mode `Open()`
outright with "PowerPoint could not open the file" - no repair prompt, no
recovery. **Cause:** a dangling `p:spTgt` left in the `p:timing` tree by
deleting the shape it targets. Whether the interactive UI behaves the same
was never established. **Fix:** `textedit.delete_shape` checks the union of
the shape's own id and, when the shape is a group, every descendant's id
against `anim_targets(slide)`, and raises `AnimationTargetError` rather than
removing anything in that union - a group whose child is the animation
target is refused even though the group's own id is never mentioned in the
timing tree. This is the point every deletion this module MAKES goes
through, not the only place a deck can lose animation-tree integrity:
`apply_text_map`'s paragraph removal and `set_paragraph`'s run removal
mutate below shape granularity, with no guard, and can leave a
`p:spTgt/p:txEl` range pointing past the end. **Pinned by:**
`tests/test_textedit.py::test_delete_shape_refuses_a_shape_the_timing_tree_targets`
and
`tests/test_textedit.py::test_delete_shape_refuses_a_group_whose_child_is_an_animation_target`.

### 9. `add_slide()` reuses an occupied part name after slides are deleted

**Symptom:** two slides silently collapse into one inside the package -
`slideN.xml` gets overwritten by a later slide that reuses the same number.
**Cause:** python-pptx's own slide-adding machinery picks the next `slideN`
number naively, without checking whether a gap left by a deletion is still
referenced elsewhere. **Fix:** `deck._rename_above_max` computes the maximum
number over every existing `slideN.xml` part and sets the new slide's part
name explicitly, above it. The catalogue names `add_slide()` specifically
(not only `duplicate_slide`), and both callers route through the same
helper. **Pinned by:**
`tests/test_deck.py::test_add_slide_does_not_reuse_a_freed_part_name` -
`add_slide` is the one the catalogue item names - and
`tests/test_deck.py::test_duplicate_slide_does_not_reuse_a_freed_part_name`
for the sibling caller.

## Text editing

### 10. New runs must precede `<a:endParaRPr>`; deep-copied runs carry spellcheck state

**Symptom:** a run is visibly present in the saved XML but never renders in
PowerPoint at all; separately, a cloned run underlines text nobody has
actually checked. **Cause:** a run element appended after
`<a:endParaRPr>` is silently ignored by PowerPoint's renderer; `err` and
`dirty` are attributes of `<a:rPr>` (not `<a:r>`, which carries no attributes
of its own), and a deep copy of a run carries them along unless stripped.
**Fix:** `textedit.append_runs` inserts new run elements with `addprevious`
against the paragraph's `<a:endParaRPr>` (or appends, if there is none), and
`_strip_err` removes `err`/`dirty` from the cloned run's `<a:rPr>` before it
is used. **Pinned by:**
`tests/test_textedit.py::test_appended_runs_precede_endParaRPr_and_carry_no_err`.

### 11. A notes master without placeholders makes note insertion fail silently

**Symptom:** speaker-note text is written into the file, saved without error,
and never appears in the notes pane. **Cause:** a slide's notes slide has no
BODY placeholder to hold the text, and writing to a text frame that does not
exist is a silent no-op. **Fix:** `textedit.ensure_notes_body` clones a BODY
placeholder (matched by `placeholder_format.type == PP_PLACEHOLDER.BODY`,
not by `idx` - see `docs/decisions.md` for why an `idx`-based match fails on
every real deck) from any other slide in the presentation that already has
one. `notes.write_notes` consumes this function; pinned also by
`tests/test_notes.py::test_write_notes_reaches_ensure_notes_body_when_the_master_has_no_body`.
**Pinned by:**
`tests/test_textedit.py::test_ensure_notes_body_clones_a_donor_placeholder`.
This test's fixture is what makes the clone branch reachable at all: it
deliberately strips the notes-master BODY placeholder before the test runs,
so `notes_slide.notes_text_frame` genuinely returns `None` and the clone path
executes. A naive fixture that leaves the default notes master intact never
reaches this code, because python-pptx's own notes machinery would already
supply a BODY placeholder on every slide.

### 12. Inherited text boxes may arrive with word wrap off, or the wrong width

**Symptom:** longer replacement copy overflows the right edge of a text box
with no warning anywhere. **Cause:** two independent problems that look the
same from the slide: a text box's `word_wrap` was off in the source
template, or a box's width was auto-fitted to the original (shorter) copy and
needs to be widened, not just wrapped. **Fix:** `textedit.set_wrap` turns
word wrap on for named targets; `textedit.widen` sets an explicit width (in
design pixels, through `geometry.px`) and turns wrap on together, since wrap
alone only makes the overflow vertical. Both report the targets they could
not find rather than raising. **Pinned by:**
`tests/test_textedit.py::test_set_wrap_turns_wrap_on_in_the_saved_package` and
`tests/test_textedit.py::test_widen_sets_the_width_and_turns_wrap_on`.

### 13. No OOXML association between a text box and its pill background

**Symptom:** deleting a label's text box leaves an orphan rounded rectangle
behind on the slide, invisible until someone notices it in a printed deck.
**Cause:** OOXML records no link between a text box and the shape drawn
behind it as a background; the pairing exists only as a geometric
coincidence. **Fix:** `textedit.backing_shape` recovers the pairing
geometrically - exact bounding-box equality first, then the smallest empty
auto-shape whose bounds contain the text box's centre - and
`delete_with_backing` deletes both together through `delete_shape` (so the
animation guard, item 8, applies to each). A backing shape that also
encloses some *other* text shape's centre is refused as a container rather
than a pill, because deleting it would take a whole card and its other
labels with it. **Pinned by:**
`tests/test_textedit.py::test_backing_shape_finds_the_pill_and_delete_takes_both`
for the pairing and joint deletion, and
`tests/test_textedit.py::test_delete_with_backing_refuses_a_card_enclosing_other_labels`
for the container refusal.

### 14. Page-number markers come in three incompatible flavours

**Symptom:** renumbering silently misses a slide, or writes over the wrong
box, or a re-derived field shows the wrong number after the deck is
reordered. **Cause:** printed page number is not file position (hidden
slides do not count, covers are unnumbered, the author reorders slides), and
the marker itself is one of: (1) a real slide-number **placeholder** holding
an `<a:fld type="slidenum">`; (2) an inherited text box **named for the
locale** holding a literal; (3) a plain **literal** text box on machine-built
slides, recognised only by being small, low and numeric. **Fix:**
`pagenums.find_marker` ranks all three by flavour, strongest first (real
placeholder, then locale name, then field, then the literal heuristic), not
by which shape happens to come first in the slide's z-order - a single walk
classifies every shape once and the best-ranked candidate wins, so a stray
numeric footnote near the marker floor cannot be mistaken for the real
marker just because it was added earlier. `renumber` skips hidden slides in
the visible count and derives its skip list by visible position, not file
position. **Pinned by:**

- flavour precedence over z-order:
  `tests/test_pagenums.py::test_find_marker_ranks_by_flavour_not_z_order`
  (adversarial order: literal heuristic first, real placeholder last, the
  placeholder must still win) and
  `tests/test_pagenums.py::test_renumber_does_not_overwrite_a_numeric_footnote_that_precedes_the_real_marker`
  (the reproduced defect: a numeric footnote before the real marker must be
  untouched, not overwritten with the page number).

- flavour 1 (real placeholder):
  `tests/test_pagenums.py::test_find_marker_recognises_a_real_slide_number_placeholder`.
  This is reachable only because `scripts/make_template.py` now leaves one
  real `SLIDE_NUMBER` placeholder on the content layout and `deck.add_slide`
  explicitly clones latent placeholders (date, footer, slide number) when
  asked - python-pptx's own `clone_layout_placeholders()` never clones them
  on its own, even when they exist on the layout, and a plain synthetic text
  box with an injected `<a:fld>` (as
  `tests/test_pagenums.py::test_find_marker_recognises_the_field_placeholder`
  exercises) only covers the field-detection branch, not the
  `is_placeholder`/`placeholder_format.type` branch specifically.
- flavour 2 (locale-named box):
  `tests/test_pagenums.py::test_find_marker_recognises_the_locale_named_box`.
- flavour 3 (plain literal):
  `tests/test_pagenums.py::test_find_marker_recognises_the_plain_literal_box`.
- field collapse preserving run properties:
  `tests/test_pagenums.py::test_set_number_collapses_the_field_and_keeps_its_run_properties`.
- all three flavours together, hidden slide skipped, in one deck:
  `tests/test_pagenums.py::test_renumber_handles_all_three_flavours_and_skips_hidden`.
- the visible-index/file-position distinction for `skip`:
  `tests/test_pagenums.py::test_renumber_skips_by_visible_index_not_file_position`.
- the round trip's mechanism-level guard against a marker flavour going
  unrecognised while the resulting numbers still happen to come out right:
  the `renumber_report` assertion in `examples/integration/version.py` (not
  a `tests/` file - the gate step `"round trip"` in `scripts/gate.ps1` is
  what runs it).

## Build and tooling

### 15. Generated-asset caches keyed on file existence, not content

**Symptom:** a colour change to a maturity ball or similar rendered asset
produces nothing - the build reports success and reuses the stale PNG.
**Cause:** a cache that checks "does this file exist" rather than "does this
file match what would be generated now" never notices a parameter changed.
**Fix:** `primitives.ensure_balls` keys its cache on a hash of the rendering
parameters (including colour), not on file existence alone. **Pinned by:**
`tests/test_primitives.py::test_ensure_balls_regenerates_when_the_colour_changes`
and, for the complementary case,
`tests/test_primitives.py::test_ensure_balls_does_not_rerender_when_nothing_changed`.

### 16. `icon()` fails silently when the file is missing

**Symptom:** a typo in an icon name or colour key renders nothing, and the
build still reports success. **Cause:** the original helper returned quietly
on a missing file rather than raising. **Fix:** `primitives.icon` (called
by whatever draws an icon) raises instead of returning silently. **Pinned
by:** `tests/test_primitives.py::test_icon_raises_when_the_file_is_missing`.

### 17. `PYTHONIOENCODING=utf-8` is required on every invocation

**Symptom:** a builder that prints non-ASCII text (accented characters,
special punctuation) raises a `UnicodeEncodeError` mid-run on a Windows
console with a non-UTF-8 code page. **Cause:** the default Windows console
encoding cannot represent every character these builders print. **Fix:**
every documented invocation in this repository sets
`PYTHONIOENCODING=utf-8` before `uv run`. **Pinned by:** nothing - this is
not a property a test can observe (a test process's own encoding is set by
its own launcher, not by the convention being documented). It is enforced by
convention: `scripts/gate.ps1` sets `$env:PYTHONIOENCODING = "utf-8"` once
for the whole run, and every script's own docstring repeats the same
invocation for anyone running it standalone.

### 18. Palette drift: one named colour existed in two values across builders

**Symptom:** two slides in the same deck render a nominally-identical colour
as two subtly different RGB values, and one builder holds both values live
at once under two different names. **Cause:** the same named colour was
hand-copied and drifted across duplicated builder scripts, with no single
source of truth. **Fix:** the core library holds no colour values at all -
every primitive takes its colours as arguments - and one value per name lives
in `brands/<name>/style.py`. **Pinned by:**
`tests/test_style.py::test_the_core_library_holds_no_colour_values`, a
source-level check (Phase 1) over `src/`. This test is honestly a source
grep, and it passes vacuously against `src/deck_kit/pagenums.py`, which
stores `MarkerStyle.color` as a bare `color: object` rather than anything
the grep's pattern would catch - noted explicitly in `docs/decisions.md`.
The property that actually matters for `pagenums.py` - that a caller-supplied
colour genuinely reaches the saved package, rather than a hardcoded one - is
pinned separately by
`tests/test_pagenums.py::test_marker_style_colour_reaches_the_saved_xml`,
which renumbers one deck under two different `MarkerStyle` colours and
asserts both `srgbClr` values land in the saved XML.

## Environment and process

### 19. Opening a file once proves little

**Symptom:** a package PowerPoint silently repairs on open looks identical
to a healthy one on a single open - the repair prompt only appears, or the
corruption only manifests, on a subsequent open. **Cause:** some corruption
classes are tolerated (and silently fixed) on a file's first open but not
consistently reproducible from one open alone. **Fix:** `scripts/check_pptx.ps1`
opens the target file through COM twice in the same run, second pass
read-only, and fails outright if `Open()` throws on either pass. **This
detects a throwing `Open()`, not a silent repair.** With
`WithWindow = $false` there is no interactive prompt for the script to
observe, and pass 2 always opens read-only specifically so a corrected copy
cannot be written back by accident (pass 1 does too, except under `-Save`,
where writing is the point) - so a package PowerPoint silently
repairs in place (no throw, no prompt, just different bytes than what was
asked for) passes both passes exactly like a healthy file. **Pinned by:**
nothing in `tests/` - this is not a pytest-checkable property, since it
requires real PowerPoint COM. It is `check_pptx.ps1`'s own two-pass loop
that pins the throwing-`Open()` case mechanically, and every gate step named
`"... opens twice"` in `scripts/gate.ps1` invokes it; the silent-repair case
is not pinned anywhere in this repository.

### 20. A relative CSS `@import` resolves against the importing file's URL

**Symptom:** a slide draft renders completely unstyled - no custom
properties resolve - with no error visible anywhere in the browser or the
server log. **Cause:** a relative `@import` inside a stylesheet resolves
against that stylesheet's own URL, not against the server's document root.
Serving from the slide's own directory normalises a `../../tokens.css`
import back past the root, and the request 404s silently. **Fix:** serve
from the repository root (or another root high enough that every relative
`@import` resolves), documented in `scripts/preview.py`'s own docstring and
in `references/02-html-stage.md`. **Pinned by:** nothing automated - this
failure mode requires a browser actually fetching a stylesheet, which no
`tests/` file does. `templates/slide.css` ships with exactly the relative
`@import` (`@import url("../brands/relay/tokens.css")`) that exhibits the
failure if served from the wrong root, so the artifact this item describes
does exist in the repository even though no test exercises it; the
documented procedure in `references/02-html-stage.md` is the mitigation.

### 21. The author's file is frequently locked (open in PowerPoint)

**Symptom:** a rebuild against the author's live file fails partway, or
worse, appears to succeed while corrupting their unsaved edits. **Cause:**
the author's `.pptx` is commonly open in PowerPoint while a new version is
being built, which both locks the file on Windows and leaves a `~$` sidecar.
**Fix:** `new_version.Version.__init__` refuses at construction time to
write its final output over its own source path, rather than warning and
proceeding. **Pinned by:**
`tests/test_new_version.py::test_new_version_refuses_to_write_over_its_input`
- and that is the whole of what is pinned. **Lock detection itself is not
implemented and not tested.** `Version` never checks for a `~$` sidecar or
attempts to open the source file for exclusive access; it only refuses to
target the same path as its output. A locked source file that is genuinely
different from the output path is not detected here at all - the write to
the work directory would simply fail with whatever OS-level error a locked
read produces, uncaught and unexplained by this code.

### 22. Regenerating from a stale assumption destroys manual edits

**Symptom:** a rebuild silently reverts changes the author made by hand
since the last generated version, with no warning that anything was
overwritten. **Cause:** there is no built-in diff between "what the build
assumes the file looks like" and "what the file actually looks like right
now" unless something computes it. **Fix:** dump the current file's text
(`scripts/dump_text.py`) and diff it against the last known version
(`scripts/diff_package.py`) before touching anything. The procedure is
written out in `references/05-qa.md`. **Pinned by:**
`tests/test_new_version.py::test_dump_text_round_trips_and_diff_reports_the_change`,
and the `walkthrough text dump` gate step, which runs `dump_text.py` on a
real built deck on every gate run.

### 23. Lint fails with `not in any note` on a deck built with `--notes none`

**Symptom:** `scripts/lint_deck.py` reports one deck-level finding per
`notes_only` string - `FAIL notes_only deck: <string>: not in any note` - on a
deck whose text is clean, and `--expect-checks 8` passes right up to that
line. **Cause:** the rules file still carries a `[notes_only]` table, copied
from an example whose deck the gate builds with `--notes both`, but this deck
was built with `--notes none` (the intake's default), so it has no notes for
the strings to be in. **Fix:** remove the `[notes_only]` table from the
rules file and lower `--expect-checks` to 7. The check is then reported as
`skipped (no rules)`, which is the truthful state: nothing about the notes
is being asserted because there are none. **Pinned by:**
`tests/test_lint_deck.py::test_notes_only_strings_must_be_in_the_notes_and_never_on_a_slide`,
which pins the deck-level finding this item describes, and
`tests/test_lint_deck.py::test_a_check_with_no_rules_is_skipped_not_passed`,
which pins that the missing table skips the check rather than passing it;
nothing pins the `--notes none` build itself against a rules file that
still carries the table.
