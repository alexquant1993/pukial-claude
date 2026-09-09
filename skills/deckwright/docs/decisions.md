# Reconciliation ledger

Phase 1 reconciles helpers that existed in several incompatible copies in the
source engagement. Each ruling records the decision, its justification, and
the cost of being wrong. The cost-if-wrong clause is what licenses a decision
without stopping for a review.

- Ruling: `grad` takes 3-tuple stops `(position, colour, alpha)` and a
  required `ang` in degrees - spec section 3.1, which records two arities, two
  parameter names and two different defaults (0 and 90) across the source
  builders - cost if wrong: gradients render rotated or lose their alpha;
  caught by `tests/test_xmlfill.py` and visible in the gate's PNG export.

- Ruling: generated-asset caches key on a hash of their rendering parameters,
  not on file existence - spec catalogue item 15 - cost if wrong: a colour
  change silently produces stale assets; caught by
  `test_ensure_balls_regenerates_when_the_colour_changes`.

- Ruling: `icon()` raises on a missing file instead of returning silently -
  spec catalogue item 16 - cost if wrong: a typo'd icon name renders nothing
  and the build still reports success; caught by
  `test_icon_raises_when_the_file_is_missing`.

- Ruling: the core library holds no colour values at all; every primitive
  takes its colours as arguments and the palette lives in
  `brands/<name>/style.py` - spec catalogue item 18, which records one colour
  existing in two values across builders and one builder holding both at once
  under two names - cost if wrong: the drift returns, and a pre-rendered asset
  filename pins one of the values; caught by
  `test_the_core_library_holds_no_colour_values`.

- Ruling: measurement factors are supplied by the brand and `metrics.py` has
  no defaults of its own - spec D8; the 1.12 padding was calibrated against
  one type family - cost if wrong: a brand on a different face silently
  measures wrong and either clips or wastes space; caught by
  `test_width_has_no_default_factors_of_its_own`.

- Ruling: `flow_pills` checks width as well as height - discovered while
  proving the gate could fail, and **not** present in the source repository,
  whose fit check compared total row height only - cost if wrong: a pill wider
  than its cell wraps onto a row of its own, fits vertically, and the build
  reports zero warnings while the text runs past the cell edge; that would
  make the entire zero-warning gate worthless. Caught by
  `test_flow_pills_catches_a_pill_wider_than_its_cell`.

- Ruling: the icon sheet is authored at 160 px cells and captured at device
  scale 1, rather than at 80 px cells captured at 2x - spec section 4 stage 2
  describes the engagement's 2x capture - cost if wrong: none to the output,
  since the cropper derives cell size from the screenshot and both routes give
  the same nine-times oversample, but authoring large removes a dependency on
  the capture tool's device-scale setting. The committed icons are 160x160
  placed at 18 px.

- Ruling: `uv` runs in ephemeral mode - `--offline --no-project --with
  python-pptx --with pillow` - rather than project mode. Project mode cannot
  resolve a lock offline in this environment and the network presents an
  untrusted certificate; the ephemeral environment reads the same packages
  straight from the uv cache. Cost if wrong: none functionally; `pyproject.toml`
  still declares the dependencies for anyone who can resolve them normally.

## Round two - rulings taken after the implementation review

- Ruling: autofit is stripped from every text frame in `settext`, and the
  check lives in `scripts/assert_native.py` against the built package rather
  than in a source grep - spec D8; python-pptx's `add_textbox()` emits
  `<a:spAutoFit/>`, so all 57 text boxes of the first passing gate shipped
  with "resize shape to fit text" on while the repository advertised "no
  autofit anywhere" - cost if wrong: measure-then-place is defeated the moment
  anyone edits the text, and the phase's headline claim is false in the
  artifact the gate itself blesses. Caught by
  `test_settext_turns_autofit_off` and by the gate's native-shape step.

- Ruling: `alpha_fill` picks the `(shape, rgb, pct)` signature and is
  idempotent; `dashed` picks `(shape, color, lw)` - spec section 11, which
  required each reconciliation to be recorded - cost if wrong: two stacked
  `<a:alpha>` children whose resolution PowerPoint does not define. Caught by
  `test_alpha_fill_is_idempotent`.

- Ruling: one line-height model, the named `LS_*` constants in the brand's
  style, rather than the engagement's mix of multipliers and hand-tuned
  integer pitch per size - cost if wrong: line spacing drifts per builder and
  nothing notices; visible only in the PNG export.

- Ruling: `line` is renamed `rule`, because `line` collided with the concept
  of a connector once `paths.py` arrived - cost if wrong: a caller written
  against the source repository's name gets an AttributeError, which is loud.

- Ruling: `arrow_head` delegates to `tri` rather than re-implementing the same
  triangle - cost if wrong: two markers drift apart in fill and shadow
  handling. Caught by `test_arrow_head_is_centred_on_the_point_it_is_given`.

- Ruling: the ladder in `flow_pills` steps down on width as well as height -
  found by the code review - cost if wrong: a pill that would fit one rung
  down is drawn oversized and fails the gate, so the build stops for a fault
  the code could have fixed itself. Caught by
  `test_the_ladder_steps_down_for_width_not_only_for_height`.

- Ruling: `bezier_points` raises on any command outside M, C and S, and its
  number pattern accepts leading-dot decimals - cost if wrong: an unsupported
  command's coordinates are consumed as extra parameters of whichever command
  is still active, and ".5" reads as 5; both produce wrong geometry with no
  error anywhere. Caught by
  `test_unsupported_command_raises_instead_of_being_skipped` and
  `test_leading_dot_decimals_are_parsed`.

- Ruling: `delete_positions` validates its 1-based positions and de-duplicates
  them - cost if wrong: `[0]` silently deletes the last slide and a repeat
  raises halfway through the mutation, leaving the deck half-edited. Caught by
  `test_delete_positions_rejects_zero_rather_than_deleting_the_last_slide`.

- Ruling: sizes below 9 pt are all-caps micro-labels and nothing else, with
  `T_META` at 9 pt for mixed-case metadata; the floor test walks every `T_*`
  rather than naming a few - cost if wrong: the shipped decks carried
  mixed-case copy at 7.2 pt while the reference table promised 9.5, and the
  four constants the old test named were exactly the four that passed.

- Ruling: the gate asserts exact shape counts, a freeform floor and a picture
  ceiling, not a slack minimum - cost if wrong: at `--min-autoshapes 6` the
  furniture example passed with its freeform curve deleted, which is the one
  thing that example exists to prove.

- Ruling: `templates/slide.html`, `templates/slide.css` and
  `brands/example/tokens.css` ship, with the stylesheet reaching the tokens
  through a relative `@import` - the plan dropped all three without recording
  it - cost if wrong: catalogue item 20 documents a failure mode that no
  artifact in the repository could actually exhibit, and README tells a reader
  to draft a slide with no skeleton to start from.

  **2026-09-09, one brand:** `brands/example` was removed. The skeleton and its
  `@import` stayed; the import points at `brands/relay/tokens.css`.

## Phase 2

- Ruling: the brand root is resolved per call through `brands_dir()`, reading
  `DECKWRIGHT_BRANDS` and falling back to the source checkout, rather than
  frozen into a module-level `BRANDS_DIR` at import - handoff section 5 item 6
  - cost if wrong: `deck_kit` installed as a wheel, which `pyproject.toml`
  already configures, resolves the brand root to a path inside site-packages
  and every brand load fails with a path nobody recognises. Caught by
  `test_brand_root_comes_from_the_environment_when_it_is_set` and
  `test_the_module_exposes_no_frozen_brands_dir_constant`.

- Ruling: `backing_shape()` filters to *empty* auto-shapes and breaks ties by
  smallest area - spec section 4 stage 4 names only "exact bounding-box
  equality, or the smallest empty auto-shape containing the text box centre",
  so the emptiness filter and the tiebreak are this repository's choices -
  cost if wrong: a card frame enclosing several labelled pills is returned as
  the backing of each one, and `delete_with_backing` takes the whole card
  away with the first label. Caught by
  `test_backing_shape_returns_none_when_the_text_box_stands_alone` and by the
  orphan assertion in the pill test.

- Ruling: `delete_shape()` raises rather than repairing, and every deletion in
  the library goes through it - catalogue item 8, where a dangling `p:spTgt`
  makes automation-mode `Open()` fail outright rather than offer repair -
  cost if wrong: there is no recovery downstream; the file is simply
  unopenable and the doubled COM check reports it with no way to say which
  shape caused it. Caught by
  `test_delete_shape_refuses_a_shape_the_timing_tree_targets`.

- Ruling: `delete_with_backing()` refuses a container-shaped backing even
  though `backing_shape()` still returns it - spec section 4 stage 4 defines
  the fallback but not what to do when the smallest containing shape is a
  card rather than a pill - cost if wrong: a label with a genuinely oversized
  individual pill that happens to overlap a neighbouring label's centre keeps
  its orphan, which is a cosmetic leftover, versus deleting a whole card and
  its contents, which is data loss. Caught by
  `test_delete_with_backing_refuses_a_card_enclosing_other_labels`.

- Ruling: `merge()` works on the zip package only and never opens a
  `Presentation`, and its package helpers - `read_package`, `write_package`,
  `slide_order`, `dangling_refs` - are public - spec section 4 stage 4, which
  requires the zip-surgery stages to run as separate subprocesses so a crash
  cannot corrupt an in-memory `Presentation` - cost if wrong: python-pptx
  models the destination's masters but not the donor's, so a partially
  modelled package silently drops the parts it has no model for.

- Ruling: `specs` entries are `(source_index, position, hidden)`, with
  `source_index` 1-based in the donor's presentation order and `position`
  1-based in the FINAL deck - the engagement's convention, kept - cost if
  wrong: positions read as pre-insertion indices place every slide after the
  first one wrong, and in a deck whose slides look alike the error is
  invisible until someone presents it.

- Ruling: `dangling_refs()` is a public checker run against every Phase 2
  artifact, rather than an assertion buried inside `merge()` - not present in
  the engagement, where a dropped relationship surfaced only as PowerPoint's
  repair prompt - cost if wrong: the transplant produces a package that opens,
  repairs, and loses the transplanted content, which the doubled COM check
  catches only if the repair prompt appears at all. Caught by
  `test_the_merged_package_has_no_dangling_references`.

- Ruling: `_resolve_from`'s empty-base branch calls `_resolve("/", target)`,
  not `_resolve("x", target)` as the plan's inlined `dangling_refs` block
  specified - `"x".rsplit("/", 1)[0]` returns `"x"` itself (no separator to
  split on), so the plan's version resolves every package-root relationship
  (`_rels/.rels`, e.g. `docProps/app.xml`) to `x/docProps/app.xml` and
  reports it missing - the opposite of catalogue item 4's fix, on every
  package. `"/".rsplit("/", 1)[0]` is `""`, which is what `_resolve` actually
  needs for a root-relative target. Caught by
  `test_dangling_refs_is_empty_on_a_package_nobody_merged`, added for exactly
  this: a checker that fails on a valid file is worse than no checker.

- Ruling: `fonts.transplant()` takes its donor as an argument and requires an
  exact `expect_parts` - the engagement's `add_fonts.py` hardcoded a donor path
  and asserted `len(smap) == 21`, a number true of one file on one machine -
  cost if wrong: the transplant silently succeeds against a donor that lost a
  face, and the deck renders in a substitute font on every machine that lacks
  it, which is the one failure embedding exists to prevent. Caught by
  `test_transplant_refuses_a_count_that_does_not_match`.

- Ruling: `fonts.transplant()` ASSERTS its part count where spec section 3.2
  says the opposite in as many words - "the font count becomes something the
  tool reports rather than something it asserts". This is a declared deviation
  from the spec, not an application of it: Phase 1's "exact values, never
  floors" rule and handoff lesson 2 win here - cost if wrong: the spec's
  reporting posture would let a donor that lost a face pass silently, which is
  the failure embedding exists to prevent. A reviewer who prefers the spec's
  posture should make `expect_parts` default to `None` (report) with the gate
  passing it explicitly; both give the gate the same teeth.

- Ruling: the gate's font donor is built by `scripts/embed_fonts.ps1` (COM,
  SaveSubsetFonts = $false), and `fonts.embed` - which writes raw sfnt bytes
  is for unit fixtures only - spec section 12,
  which ports `finalize_embed.ps1` as an alternative and not the recommended
  path - cost if wrong: PowerPoint repairs the donor and the transplant
  propagates a broken font list into every version. Settled in Task 3 step 5
  by running `check_pptx.ps1` against the donor; the gate re-runs it.
  OBSERVED: Noto Sans IS installed on this machine (confirmed via
  `System.Drawing.Text.InstalledFontCollection`), but
  `scripts/embed_fonts.ps1` fails before it can Save: setting
  `$pr.EmbedTrueTypeFonts` throws "La propiedad 'EmbedTrueTypeFonts' no se
  encuentra en este objeto" - the property is absent from the Presentation
  COM object on this PowerPoint build (16.0.20228.20188,
  O365ProPlusRetail/x64; `Get-Member` on the open Presentation lists no
  `EmbedTrueTypeFonts` or `SaveSubsetFonts` property at all). The unmodified
  text-only specimen was then run through `check_pptx.ps1` anyway, which
  printed `pass 1: OPEN_OK slides=1 hidden=` / `pass 2: OPEN_OK slides=1
  hidden=` / `CHECK PASSED`, and the font-part count on that file is 0 (no
  embedding was ever attempted). This is outcome 3 from the task-3 brief:
  COM is available and the file is not repaired, but embeds nothing in any
  face because the embedding API itself is unreachable through this
  installation's automation surface - not a missing-font problem, and not
  fixed by installing anything. Phase 2 ships without font embedding on this
  machine: the gate uses `--expect-fonts 0`, `fonts.py` and its seven unit
  tests still ship and still pass against the fixture-only `fonts.embed`
  route, and `references/06` (Task 10) must record catalogue items 1, 2 and
  4 as not pinned by the gate, naming this outcome. A machine whose
  PowerPoint automation surface does expose `EmbedTrueTypeFonts` would
  observe a nonzero count and should update `--expect-fonts` to match; the
  ruling here is the measurement taken on the machine this branch was built
  on, not a claim about every machine.

- Ruling: run attribution uses `difflib.SequenceMatcher(autojunk=False)` and
  attaches every insertion and replacement to the run owning the FIRST
  affected old character - `v06_build.py`'s lineage, over `v07_build.py`'s,
  which called the same function but only ever for whole-paragraph
  replacements - cost if wrong: with `autojunk` on, difflib treats frequent
  characters as junk in long paragraphs and the opcodes stop being
  character-exact, so runs silently reflow and mid-sentence bold moves.
  Caught by `test_an_edit_inside_the_bold_run_stays_bold`.

- Ruling: `patch_paragraph()` raises on a paragraph with no runs rather than
  indexing `owner[-1]` on an empty list, which is what the engagement's
  version did - cost if wrong: an empty paragraph between two bullets, which
  is ordinary in a hand-edited deck, crashes the build with an IndexError
  that names nothing. `set_paragraph` (Task 5) will agree with this.

- Ruling: `patch_text()` compares `.strip()`ed paragraph text and requires
  exactly one match per patch - the engagement's convention, kept - cost if
  wrong: zero matches means the author edited that sentence and the build
  would ship the old text silently; two means the patch is ambiguous and
  changes the wrong one as soon as either diverges. Caught by
  `test_patch_text_requires_exactly_one_match` and
  `test_patch_text_rejects_two_matches`.

- Ruling: `apply_text_map()` never raises and returns every mismatch it found;
  the two hand-written fixup passes that sat beside it in the engagement
  (`fix_index`, `apply_fixups` in `apply_dya_text.py`, which did raise on a
  missing shape id) are folded into the same accumulating discipline - spec
  section 4 stage 4 - cost if wrong: one missing id hides the other nine
  problems in the same map, and each one costs a full build round trip to
  discover. Caught by
  `test_apply_text_map_accumulates_every_mismatch_instead_of_raising`.

- Ruling: the text map is keyed on shape id resolved recursively through
  groups, never on shape name, position or text - spec section 4 stage 4 -
  cost if wrong: names repeat inside a deck, so a map keyed on name edits an
  arbitrary one of the matching shapes, and the wrong slide changes.

- Ruling: `paragraph_text()` concatenates the runs rather than reading
  `paragraph.text` - cost if wrong: a paragraph containing a line break
  matches on a string its runs cannot reproduce, and `patch_paragraph`'s
  reassembly assertion fires on text that was never wrong.

- Ruling: the slide part-name minting lives in `_rename_above_max()` and BOTH
  `add_slide` and `duplicate_slide` call it - catalogue item 9 names
  `add_slide()`, and Phase 1 shipped it unfixed - cost if wrong: a build that
  deletes a position and then adds a slide overwrites a slide inside the
  package, and the coverage map claims the item is covered. Caught by
  `test_add_slide_does_not_reuse_a_freed_part_name`.

- Ruling: `fingerprint()` walks through groups, unlike the engagement's
  `v06_build.py` title check which read `prs.slides[i].shapes` flat - cost if
  wrong: on a real deck whose title sits inside a group the fingerprint is
  empty and `assert_fingerprint` fails on a correct file, so the author stops
  passing fingerprints and the guard is gone.

- Ruling: catalogue item 11 - the notes-master placeholder clone - is
  implemented in Phase 2's `textedit.ensure_notes_body`, although `notes.py`
  is Phase 3's - the spec's phase boundary and its Phase 2 gate clause
  ("every catalogue item in the OOXML and text-editing groups has a test")
  disagree here, and this resolves toward the gate - cost if wrong: Phase 3's
  `notes.py` reimplements a placeholder clone rather than consuming one, which
  is the drift D1 exists to prevent. Phase 3 consumes this function.

- Ruling: `ensure_notes_body()`'s donor search matches
  `placeholder_format.type == PP_PLACEHOLDER.BODY`, not `idx == 1` as task-6a's
  brief text specified - measured directly against this environment's default
  notes master (python-pptx's built-in template, since `out/template.pptx`
  carries no `ppt/notesMasters/` part): the BODY placeholder's idx there is 3,
  not 1, alongside HEADER=0, DATE=1, SLIDE_IMAGE=2, FOOTER=4,
  SLIDE_NUMBER=5. An `idx == 1` check matches DATE, never BODY, so the donor
  search fails on every real deck and `ensure_notes_body` raises `LookupError`
  unconditionally - cost if wrong: catalogue item 11 is "fixed" by a function
  that can never succeed, which surfaces as a build-time crash on the first
  deck that needs it instead of the silently-missing note it was meant to
  prevent. `type == PP_PLACEHOLDER.BODY` matches python-pptx's own
  `NotesSlide.notes_placeholder` implementation. Caught by
  `test_ensure_notes_body_clones_a_donor_placeholder`, whose fixture strips
  the BODY placeholder by type for the same reason.

- Ruling: page renumbering is its own module, `deck_kit/pagenums.py`, rather
  than a section of `textedit.py` - the spec's repository structure (section 5)
  names "page numbers" only inside `references/04` and lists no module - cost
  if wrong: none functionally; the alternative mixes marker archaeology with
  run attribution in one file and makes both harder to read.

- Ruling: `pagenums` takes the union of the engagement's three partial
  implementations - `find_marker` and `set_number` from `task6_retouch.py`,
  the visible-count and add-if-missing behaviour from `v02_pagenums.py`, and
  none of `v07_build.py`'s `renumber`, which patched through
  `patch_paragraph` and therefore could not collapse a field - cost if wrong:
  a deck renumbered by the `patch_paragraph` route leaves its `<a:fld>` in
  place, and PowerPoint re-derives the file position on open, which is the
  number renumbering exists to override. Caught by
  `test_set_number_collapses_the_field_and_keeps_its_run_properties`.

- Ruling: `MarkerStyle` carries the marker's geometry, size, colour and font,
  supplied by the caller from the brand - Phase 1's ruling that the core holds
  no colour values and no measurement defaults - cost if wrong: the engagement's
  `v02_pagenums.py` hardcoded `RGBColor(0x2E, 0x40, 0x4D)`, `Pt(8)` and the
  position 1172,690, so a second brand silently inherits the first one's
  furniture. Caught by `test_marker_style_colour_reaches_the_saved_xml`, which
  renumbers one deck under two different `MarkerStyle` colours and asserts
  both `srgbClr` values in the saved package. NOT by
  `test_the_core_library_holds_no_colour_values`: that test is an `rglob` +
  `read_text` + `re.search(r"RGBColor\s*\(")` over `src/`, it is one of the two
  source greps handoff lesson 1 names as having failed, and it passes
  vacuously against `pagenums.py`, which stores `color: object`.

- Ruling: `renumber`'s `skip` names VISIBLE positions only, not
  `visible in skip or position in skip` as task-7's brief text had it - cost
  if wrong: the two indexings coincide until a deck carries a hidden slide
  before the cover, at which point the disjunction skips two different
  slides (file position 1 and visible index 1 both satisfy it) and no caller
  can say which one `skip=(1,)` was meant to protect. Visible index is what a
  reader of a printed deck means by "the cover is unnumbered." Caught by
  `test_renumber_skips_by_visible_index_not_file_position`.

- Ruling: `renumber(prs, style, skip=(1,))` derives its own marker floor from
  `style.y` (via `geometry.px`) rather than taking `min_top_emu` as a
  parameter - task-7's brief text imported `px` into `pagenums.py` for this
  purpose and then never called it, leaving six hand-rolled
  `style.y * 9525 - 1` call sites in the tests instead - cost if wrong: a
  caller could pass a `min_top_emu` that disagrees with the `style.y` it also
  passed, and `find_marker` would then search a different band of the slide
  than the one the marker it is about to write actually occupies.
  `find_marker` itself keeps `min_top_emu` as an explicit parameter for
  direct callers that have no `MarkerStyle` to derive it from.

- Ruling: `scripts/make_template.py` keeps one real placeholder on the
  content layout - `PP_PLACEHOLDER.SLIDE_NUMBER`, positioned from the
  brand's `PAGE_X`/`PAGE_Y`/`PAGE_W`/`PAGE_H` - instead of stripping every
  placeholder as it did through Task 6b. Without it, flavour one of
  catalogue item 14 (a real inherited slide-number placeholder, recognised by
  `shape.placeholder_format.type`) had no artifact in the repository that
  could exercise it, and `add_slide`'s `keep_placeholders` parameter, added
  in Task 6b, was inert - cost if wrong: `find_marker`'s placeholder-type
  branch ships covered only by the synthetic `_field_marker` text-box
  fixture, which matches on `<a:fld>` content rather than on
  `shape.is_placeholder`, so a regression in the placeholder-type branch
  specifically would ship silently. `add_slide` still purges the placeholder
  by default, so every existing caller and the Phase 1 gate's exact
  autoshape counts (`assert_native.py --autoshapes 62` for the matrix,
  `--autoshapes 7` for the furniture) are unaffected - verified by rerunning
  both after this change. The `<a:fld type="slidenum">` itself lives only on
  the layout: python-pptx's `clone_placeholder()` gives the cloned
  slide-level SLIDE_NUMBER shape a bare `<p:sp>` with no `<p:txBody>` at
  all, and PowerPoint renders the printed number by inheriting from the
  layout's field. The slide-level shape carries no field of its own; it is
  recognised purely by `placeholder_format.type`, and `set_number` overrides
  the inherited number by writing a literal into what starts as an empty
  text body. Caught by
  `test_find_marker_recognises_a_real_slide_number_placeholder` (whose
  cloned shape is renamed away from python-pptx's default "Slide Number
  Placeholder N" so only the type branch, not the name branch, can match),
  `test_add_slide_keeps_the_slide_number_placeholder_when_asked` and
  `test_add_slide_purges_the_slide_number_placeholder_by_default`.

- Ruling: `Version` refuses at construction time to write its final output
  over its source, rather than warning - catalogue items 21 and 22 - cost if
  wrong: the author's file is usually open in PowerPoint and locked, so the
  write either fails halfway or, worse, succeeds and destroys the manual edits
  the version was supposed to build on. Caught by
  `test_new_version_refuses_to_write_over_its_input`.

- Ruling: every step writes its own `stepN_<name>.pptx` and no step rewrites
  an earlier one - spec section 4 stage 4 - cost if wrong: a failure in step 4
  leaves one file that is neither the input nor the output, and the only way
  to find where it went wrong is to run the whole pipeline again with prints.
  Caught by `test_new_version_writes_every_intermediate`.

- Ruling: `subprocess_step` appends the input and output paths to the caller's
  argv, so every out-of-process stage has the same two-positional-argument
  contract - the engagement's `add_fonts.py` and `v02_pagenums.py` both used
  `sys.argv[1], sys.argv[2]` and it is worth keeping - cost if wrong: each
  stage invents its own flags and the driver grows a special case per stage.

- Ruling: the Phase 2 round trip's font stage stays IN, gated on
  `--expect-fonts 2`, against a donor written by `deck_kit.fonts.embed` - not
  by `scripts/embed_fonts.ps1` (COM) - Task 9's font decision point. Measured
  directly: `fonts.embed` a donor from `brands/example`'s two TTFs onto a
  plain deck, `fonts.transplant(..., expect_parts=2)` it into another plain
  deck, and run `scripts/check_pptx.ps1` on the result -
  `pass 1: OPEN_OK slides=0 hidden=` / `pass 2: OPEN_OK slides=0 hidden=` /
  `CHECK PASSED`, both opens with no repair. `scripts/embed_fonts.ps1` itself
  remains unusable on this machine (Task 3's finding: `EmbedTrueTypeFonts` is
  absent from this PowerPoint build's Presentation COM object), so the gate's
  "font donor" step calls `scripts/embed_fonts.py --brand example --deck
  out/template.pptx --out out/fontdonor.pptx` (the direct `fonts.embed` route,
  no COM), not the `--text-only` + `embed_fonts.ps1` sequence Task 9's brief
  literally specified - that sequence throws unconditionally on this machine
  and would fail the gate on a step orthogonal to anything Task 9 controls.
  Catalogue item 2 (the splice lands after `<p:notesSz/>`, rIds re-minted, a
  `fntdata` content-type Default added) is pinned by the gate against this
  Python-written font list. Catalogue item 1 is NOT pinned here - see the
  corrected ruling below, added after a review round found the original
  "PowerPoint strips fonts on save" step measured nothing (it saved a
  freshly-opened, unmodified file, which is a COM no-op) and its
  `--expect-fonts` was therefore recording a copy, not a save. Item 4 (embed
  ALL characters, not just the used subset) stays unpinned here, as it was
  after Task 3 - it is a property of the COM
  `SaveSubsetFonts = $false` route specifically, which this machine cannot
  exercise at all.

  **2026-09-09, one brand:** `brands/example` was removed; the gate's "font
  donor" step now reads `--brand relay`, and the two TTFs are Public Sans
  Regular and Bold. The measurement above is unchanged and was re-run
  end to end: 2 font parts in `out/v2/final.pptx`, both COM opens clean.

  Cost if wrong: a donor that lost a face, or a splice that
  landed in the wrong place in presentation.xml, ships silently and every
  version this repository regenerates loses its embedded fonts, which is the
  failure embedding exists to prevent. Re-derive `--expect-fonts` on a machine
  whose PowerPoint build does expose `EmbedTrueTypeFonts`; this ruling is the
  measurement taken on the machine this branch was built on.

- Ruling (CORRECTED after a review round; the original version of this entry
  claimed the opposite and was struck): **catalogue item 1 is true.**
  PowerPoint strips embedded fonts when it genuinely saves a file. The
  round trip's first pass at measuring this called `check_pptx.ps1 -Save`
  straight after `Presentations.Open()`, and `.Save()` on a freshly-opened,
  unmodified presentation is a documented COM no-op: `Presentation.Saved` is
  already `msoTrue`, so `.Save()` writes nothing. `out/fontdonor.pptx` and
  the "resaved" copy it produced were byte-identical (same size, same
  content), which is what a no-op looks like, not what a save that stripped
  anything looks like - and the ruling this replaced read that as "the fonts
  survived," which was true only in the sense that nothing had happened at
  all.

  Corrected measurement: `check_pptx.ps1 -Save` now forces the presentation
  dirty (`$pr.Saved = $false`, confirmed writable on this build) before
  calling `.Save()`, and fails outright if that did not leave it dirty. Run
  against `out/v2/final.pptx` (7 slides, 2 `.fntdata` parts, from this
  repository's own round trip): the saved copy carries **0** font parts -
  `<p:embeddedFontLst>`, both font relationships, and the `fntdata`
  `[Content_Types].xml` Default are all gone, and the file drops from
  673,435 to roughly 33,000 bytes. Independently, against a copy of the
  source engagement's `fic.pptx` (21 genuine, PowerPoint-EOT-wrapped font
  parts, not `fonts.embed`'s raw sfnt ones): 21 parts become 16, every
  surviving part is rewritten, and the typeface count drops from six to
  four. PowerPoint parses real EOT parts on save and regenerates the
  embedded-font list from whatever it can still re-embed locally from
  installed faces; it does not parse `fonts.embed`'s raw-sfnt parts at all,
  and discards the entire apparatus rather than repairing or ignoring it.

  The gate's font-save step (`scripts/gate.ps1`, renamed "PowerPoint strips
  embedded fonts on a real save") now runs on `out/v2/final.pptx` and
  asserts `--expect-fonts 0` - the observed result of a real save, not a
  guessed one and not the earlier no-op's number. Cost if wrong: the
  previous version of this ruling shipped a gate step that was green by
  construction (nothing it measured could ever fail) and a decisions-log
  entry asserting the opposite of what PowerPoint actually does, which is
  precisely the kind of false doctrine `tests/test_no_source_grep_doctrines.py`
  exists to catch in test files and had no counterpart for in this log.
  Caught by an independent review round re-running the measurement with a
  forced dirty flag and comparing file sizes and content, not by anything in
  this repository's own test suite - none of it asserts on `.Saved` or on
  byte-for-byte file identity.

- Ruling: `step` and `subprocess_step` take an optional `slides=` count,
  asserted against the result after the step runs and before it is saved (or,
  for the subprocess case, by re-opening the output) - a controller ruling
  overriding the brief's original no-count signature, made because Task 9
  passes `slides=` at every call site - cost if wrong: `delete_positions` and
  `merge` both change the slide count, and a silent off-by-one there is
  invisible until someone presents the deck. Caught by
  `test_new_version_subprocess_step_checks_declared_slide_count`.

## Phase 3

- Ruling: `Note` carries position, title, text, minutes and an optional
  section label, and nothing about hidden state or printed numbers - the
  engagement's 5-tuple carried `printed` by hand and derived hidden from
  `printed is None`, and its teleprompter hardcoded an annex position range
  - cost if wrong: an author types the printed number twice (once in the
  deck, once in the notes) and the teleprompter disagrees with the footer
  the moment a slide is hidden; caught in Task 2 by
  `test_renumber_report_agrees_with_visible_numbers`.

- Ruling: `write_notes` requires exactly one note per slide and raises
  naming the missing, duplicate or out-of-range positions, rather than
  writing what it can - cost if wrong: a slide with no note is discovered on
  stage. Caught by
  `test_write_notes_refuses_a_note_list_that_does_not_cover_every_slide`.

- Ruling: `read_notes` reads `paragraph.text`, an exception to
  `textedit.paragraph_text`'s run-concatenation rule, because notes
  paragraphs are written by this module as single runs and never carry
  `<a:br>` - cost if wrong: a hand-edited note with a line break reads back
  with a vertical-tab character where the break was; visible in lint output
  only.

- Ruling: `pagenums.visible_numbers` is the single counting rule, and both
  `renumber` and `notes.numbering` consume it - handoff section 5 lesson 3
  (two self-consistent mechanisms can both be green and disagree) - cost if
  wrong: the teleprompter says "[7]" on a slide whose footer prints 6, on
  the first deck with a hidden slide, and the presenter reads the wrong
  cue. Caught by `test_renumber_report_agrees_with_visible_numbers`, which
  runs both mechanisms on one deck; `test_numbering_reports_printed_numbers_and_hidden_flags`
  pins only the shape of `numbering`'s output.

- Ruling: `templates/teleprompter.html` carries its own neutral chrome
  colours and the emitter carries none - the no-colour rule (catalogue item
  18) governs `src/deck_kit/`, and a teleprompter is read on a phone, not
  projected under a brand - cost if wrong: none to any deck; a brand that
  wants its own teleprompter chrome passes `template=` to
  `teleprompter_html`.

- Ruling: the template root is resolved per call through
  `notes.templates_dir()`, reading `DECKWRIGHT_TEMPLATES` and falling back
  to the source checkout - the Phase 2 `brands_dir()` ruling applied to the
  second path-relative asset root - cost if wrong: an installed wheel
  cannot find `teleprompter.html` and the emitter fails with a path inside
  site-packages. Caught by
  `test_templates_dir_comes_from_the_environment_when_it_is_set`.

- Ruling: `compose_qa.py` validates the crop box against every image and
  fails on the PNG count before composing anything - the engagement's
  `band.py` and `zoom.py` hardcoded a 1600x900 box and a 30-slide count,
  and Pillow pads an out-of-range crop with black rather than raising -
  cost if wrong: a strip composed entirely of padding looks uniformly
  clean, and a glob matching four of seven PNGs composes four rows nobody
  counts. Caught by `test_band_refuses_a_box_outside_the_image` and
  `test_band_fails_on_a_count_that_does_not_match`.

- Ruling: `zoom` resizes with `Image.NEAREST` - cost if wrong: none to any
  deck; a bilinear zoom blurs the one-pixel offset the zoom exists to show.

- Ruling: `compose_qa.py ink` asserts a composed strip's content per row
  (pixels differing from their scanline's first pixel), and the gate uses it
  instead of asserting the image's size - the size of a band is
  `gutter + box width` by `box height x slides` by construction, so a size
  assertion cannot fail on anything about the deck (the shape of the inert
  meta-check the Phase 2 review caught) - cost if wrong: a crop box that
  drifted off the footer composes a clean strip of the right size and nobody
  looks. Caught by `test_ink_separates_a_row_with_content_from_a_uniform_one`
  and the gate's `band shows the footer` step.

- Ruling: `lint_deck.py` exits 1 on any finding and treats a check with no
  rules as skipped, reporting `ran=` and `skipped=` counts that
  `--expect-checks` asserts - the four engagement scripts it ports all
  exited 0 unconditionally and reported by print, and a check that runs
  with an empty list is green because it checked nothing (handoff section
  5 lesson 3) - cost if wrong: an empty `needles = []` after a careless edit
  turns the typo check off with the gate still green. Caught by
  `test_a_check_with_no_rules_is_skipped_not_passed`.

- Ruling: text is harvested through `textedit.iter_paragraphs`, which
  recurses groups and table cells - the engagement had three harvesters of
  differing depth and the two shallow ones missed grouped text - cost if
  wrong: a forbidden token inside a grouped shape reaches the client.
  Caught by `test_slide_texts_covers_every_slide_including_the_cover`
  (structure) and by `test_lint_deck.py`'s fixture, whose findings sit in
  plain text boxes; a grouped-text fixture is a deferred minor recorded in
  the Phase 3 handoff.

- Ruling: the D4 "no third-party mark" guarantee is enforced as a
  provenance manifest (`brands/<name>/assets.toml`: path, sha256,
  non-empty provenance for every file that is not text) checked by
  `lint_deck.py`'s `assets` check, not as an image judgement - no lint can
  look at a PNG and know whose mark it is; what it can do is refuse any
  file nobody has accounted for. The rule is "everything except a short
  text allowlist", not "every known binary extension", because an
  extension-keyed check lets the person adding the file choose its blind
  spot - cost if wrong: a mark arrives in `brands/example/` through an
  ordinary commit and the README's claim is false until someone notices.
  Caught by `test_assets_check_fails_on_an_unlisted_binary`,
  `test_assets_check_is_not_evaded_by_an_unknown_or_missing_extension` and
  `test_the_example_brand_passes_its_own_asset_check`. `examples/` is not
  covered: it holds no non-text files today, and that half of the
  no-marks constraint stays a review matter, recorded in the handoff.

  **2026-09-09, one brand:** `brands/example` was removed. The third test is now
  `test_the_shipped_brand_passes_its_own_asset_check` and checks
  `brands/relay/assets.toml` - fourteen files: six faces, six icons and two
  wordmarks.

- Ruling: the `exact` check reads the spec's table by its column name
  (`Exact string`), not by section number - cost if wrong: renumbering the
  spec's sections silently turns the check into a no-op; caught by
  `test_exact_strings_come_from_the_spec_table`, which raises on a spec
  with no such table, and by `--expect-checks` in the gate.

- Ruling: `brands/example/fonts/README.md` cites the SIL Open Font
  License 1.1 by name and points at `assets.toml` for provenance, but no
  verbatim copy of the OFL 1.1 text is committed as
  `brands/example/fonts/OFL.txt` - a machine-wide search for an existing
  `OFL.txt`/`LICENSE` and an attempt to read the license field out of the
  TTFs with `fontTools` both came up empty offline (`fonttools` is not in
  the local `uv` cache and the network is disabled), and the text must not
  be typed from memory. The license text is owed and pointed at by name
  in the meantime - cost if wrong: an OFL redistribution without its
  license text, fixed by adding one file once a verbatim copy is available
  offline.

  **2026-09-09, one brand:** `brands/example` was removed with its fonts and this README.
  The debt it recorded is closed for the brand that remains:
  `brands/relay/fonts/` ships `SpaceGrotesk-OFL.txt`,
  `PublicSans-LICENSE.md` and `JetBrainsMono-OFL.txt`, each a verbatim copy
  fetched by `scripts/fetch_fonts.py` alongside the face.

- Ruling: the spec template's "Verified facts" table carries an `Exact
  string` column that `lint_deck.py` reads, so the spec is load-bearing
  for the build rather than prose beside it - spec section 4 stage 1 ("use
  exactly these numbers") and "The QA loop" (verbatim-match assertions on
  the figures the spec declared exact) - cost if wrong: a figure the spec
  fixed is retyped on a slide with a digit wrong and nothing notices;
  caught by the `walkthrough lint` gate step and
  `test_exact_figures_must_appear_verbatim_on_some_slide`.

- Ruling: `examples/walkthrough/` is a fourth example directory, not named
  in spec section 5's tree - the Phase 3 gate needs a subject that is at
  once the filled instance of every template and a deck every new tool runs
  against - cost if wrong: none functionally; the alternative is a filled
  template that lives inside a test function where no reader finds it.

- Ruling: the walkthrough's slides are route B with no HTML draft; the spec's
  section 5 is the design - cost if wrong: none to the gate; a reader who
  wants the HTML stage worked through has `examples/capability-matrix/`.

  **2026-09-09, one deck:** `examples/capability-matrix/` was deleted. The
  reader who wants the HTML stage worked through has
  `examples/ai-horizon/drafts/`, ten drafts for ten slides.

- Ruling: `T_COVER = 36.0` joins the example brand's type scale rather than
  the walkthrough carrying a literal - spec section 4 stage 3, "sizes live
  in named `T_*` constants" - cost if wrong: none; a second brand sets its
  own.

- Ruling: the Phase 3 gate runs on the walkthrough only, not on the Phase 2
  round trip's `final.pptx` - the round trip drops notes at the merge by
  design (catalogue item 6), so it cannot be the notes subject, and the lint
  rules are per-deck - cost if wrong: none to the round trip; a second
  `lint.toml` for `examples/integration/` is a deferred minor in the
  handoff.

- Ruling: the gate asserts the composed strips' *content* per row through
  `compose_qa.py ink` (row 1 blank, row 2 inked, for both strips), and not
  their sizes, which follow from the arguments by construction - handoff
  section 5 lesson 3, and the inert meta-check the Phase 2 review caught -
  cost if wrong: a crop box that drifts off the footer composes a clean
  strip of the right size and nobody looks. Caught by the induced defect
  "band `--box` changed to a blank region".

- Ruling: the `compose zoom` gate step carries no `--expect`: with
  `--slides 1,2` explicit, `find_slides` raises on a missing member before
  the count check runs, so `--expect 2` there could never fail on anything
  about the deck - the inert-assertion shape the previous ruling says the
  gate avoids. `compose band` keeps `--expect 2` because its `--slides`
  defaults to all and the count is the only thing that catches a missing
  PNG (induced defect 6) - cost if wrong: none; the zoom step's protection
  is the `FileNotFoundError`, which stays.

- Ruling: every safety check in `fonts.py`, `deck.assert_fingerprint`,
  `textedit.patch_paragraph`/`append_runs` and `new_version.py` raises
  `AssertionError` explicitly instead of through a bare `assert` - handoff
  section 6, the residual minor with a safety consequence: under
  `python -O` the fingerprint guard that defends catalogue item 22, the
  font part-count guard and the run-reassembly guard all vanish - cost if
  wrong: a `PYTHONOPTIMIZE=1` in someone's environment turns a wrong-file
  build into a silent overwrite of the author's edits. Caught by the gate
  step "safety checks survive python -O", which runs the four pinning
  test files with `-O`. `examples/integration/version.py`'s eight bare
  asserts are deliberately left: they are gate post-conditions run only
  under `scripts/gate.ps1`, which never passes `-O` - cost if wrong: none
  while that stays true; convert them when the file is next touched.

- Ruling: `references/01`'s fact-by-fact verification uses a four-valued
  verdict (Exact / Inexact / Judgement / Untraceable, tie-break toward
  Judgement) where spec section 4 stage 1 names only "exact" and
  "untraceable" - a declared extension of the spec, taken from the
  engagement's actual fact-by-fact review practice, in which "inexact" and
  "judgement" were the two verdicts that separated an error of fact from a
  defensible reading - cost if wrong: a reviewer applies four labels where
  the author expected two; collapse Inexact into the severity grade and
  Judgement into Exact and the spec's scheme is back, with no artifact to
  change.

- Ruling: `pagenums.is_hidden` is the single hidden predicate, consumed by
  `visible_numbers`, `notes.numbering` and `scripts/dump_text.py`, and it
  accepts `"false"` as well as `"0"` - `show` is `xsd:boolean` in the schema,
  so a deck hidden by a tool other than PowerPoint could carry either
  spelling, and the predicate was previously written out three times with the
  `"0"` comparison in each - cost if wrong: none for PowerPoint-authored
  decks, which write `"0"`. Caught by
  `tests/test_pagenums.py::test_show_false_is_hidden_everywhere_the_predicate_is_consumed`,
  which pins both the footer counter and the teleprompter's numbering against
  one `show="false"` slide.

- Ruling: the gate's `walkthrough text dump` step asserts the exact paragraph
  count derived from `examples/walkthrough/build_walkthrough.py`
  (`--expect-paragraphs 10`: 2 on the cover, 8 on slide 2, the pill's own
  empty paragraph included), not a floor and not exit 0 alone - cost if
  wrong: a deck that dumps nothing passes a step whose whole purpose is to
  prove the dump works. Derived before running anything and then confirmed
  against the built deck, which printed `10 paragraph(s)`. Caught by
  `tests/test_new_version.py::test_dump_text_expect_paragraphs_is_exact`.

## Session 2026-09-08 - intake

- Ruling: before any deck is started, the agent runs `scripts/discover.py`
  (brand packages under `brands/`, candidate corporate masters outside
  `out/`, `tokens.css` files, one recommendation line) and then asks the
  user which design system to use - the brand it found, another master
  through `scripts/inspect_template.py --brand <name> <deck>` and the "Set
  up a brand" route, or the default `brands/example` when they have none -
  and records the answer on the spec's `**Design system:**` line; it never
  assumes one. Working-agreement rule 4 (one question per message, in prose)
  applies, and the intake is rule 6 of `templates/handoff.md` section 0 -
  cost if wrong: a deck built on the placeholder brand for a client who has
  a master, or on the wrong master; every slide is rebuilt against the right
  template, and the spec's front matter is what makes the mistake visible.
  Caught by
  `tests/test_templates.py::test_the_spec_template_and_every_filled_spec_carries_the_intake_lines`
  and `tests/test_skill.py::test_the_intake_section_names_its_tools_and_the_front_matter_lines`.

  **2026-09-09, one brand:** the default named here is `brands/relay` (the
  "relay default" session below), and `brands/example` was removed
  altogether, so there is no placeholder brand left to build a client deck
  on.

- Ruling: the HTML draft is on by default for every route-B slide, because
  the draft is what makes a deck visually rich; the user may opt out, and
  the spec records `**HTML draft:** skipped: <reason>` rather than leaving
  the omission silent. The walkthrough skips it (two slides, section 5 is
  the design); the AI horizon deck carries drafts for s02, s03, s04, s08 and
  s09, authored after the builder because the deck predates this ruling, and
  the builder wins where they disagree (`examples/ai-horizon/ledger.md`) -
  cost if wrong: a route-B slide ported from prose alone comes out flat, and
  the layout is argued about in Python where iteration is slow instead of in
  a browser where it is free; the fix is one draft and one port. Caught by
  the same two tests as the ruling above.

- Ruling: speaker notes are opt-in, default none. The intake asks whether
  the presenter wants them in the PPTX notes pane, on a teleprompter HTML
  page, both, or neither; the spec's `**Notes:**` line records one of
  `none | pptx | teleprompter | both`; the builders take `--notes` with
  those four values (default `none`) and `--teleprompter PATH` only when the
  mode includes the teleprompter; and one library entry point,
  `deck_kit.notes.emit_notes(prs, notes, mode, *, font, size_pt, gap_pt,
  title, teleprompter=None, skip=(1,))`, dispatches to `write_notes` and
  `teleprompter_html`. The gate builds both example decks with `--notes both`
  so the feature stays proved on every run - cost if wrong: a presenter who
  wanted a teleprompter gets a deck without one, discovered on stage; the
  rebuild is one flag, and `write_notes` still refuses a note list with a
  gap. A deck built with `--notes none` and linted against a rules file that
  still carries `[notes_only]` fails with `not in any note` (catalogue item
  23); the rules file drops the table and expects 7 checks.

## Session 2026-09-09 - relay brand

The first real design system adopted into a brand package, and the first
deck built against a brand that is not `brands/example`. The system arrived
as `brands/relay_design_system/` - Relay, a technology consulting firm -
with tokens, guidelines, fourteen reference slides at 1920x1080 and a readme
that already declares three substitutions of its own. It is read here and
never edited.

- Ruling: `scripts/discover.py` reports a directory holding a design system
  but no `brand.py` as a "design system without a deckwright brand package",
  and recommends setting a brand up from it. Three shapes are evidence, any
  one enough: a `tokens/` directory of CSS, a `styles.css` beside a
  `readme.md` or a `SKILL.md`, or a `_ds_manifest.json`. The recommendation
  ranks it above a loose `.pptx` master, because a system that declares its
  own tokens says what the identity IS while a deck somebody dropped in says
  only what one file happened to inherit - and the failure it fixes is
  concrete: Relay has no `brand.py`, no master and no `tokens.css` (its
  tokens are eight files under `tokens/`), so the intake said "no design
  system found" and sent the user to the placeholder brand with their own
  system unread on disk - cost if wrong: a directory that is not a design
  system is offered as one, which costs the user one word in the intake
  conversation; the answer is still theirs. Caught by
  `tests/test_discover.py::test_a_downloaded_design_system_is_reported_with_what_it_holds`,
  `tests/test_discover.py::test_each_of_the_three_shapes_is_evidence_on_its_own`
  and
  `tests/test_discover.py::test_the_recommendation_sets_a_brand_up_from_a_system_ahead_of_a_master`.

- Ruling: `tests/test_style.py` walks EVERY brand that ships a `style.py`,
  not `brands/example` alone. The type floors are the repository's, and the
  moment a floor gets broken is the moment a second brand re-derives its
  scale from a design system with floors of its own - which is exactly what
  happened here: Relay's kit says "nothing on a slide goes below 24px",
  which is 12.2 pt at this canvas and disagrees with the repository's 8 to
  11 - cost if wrong: a brand ships type under the floor and nothing notices
  until a projector does; the walk is one fixture. Caught by
  `tests/test_style.py::test_every_type_size_honours_the_floors` and
  `tests/test_style.py::test_the_repository_ships_more_than_one_brand_with_a_style`.

  **2026-09-09, one brand:** `brands/example` was removed, so the walk covers one
  brand today. It is still written as a walk over the brands directory, so
  the rule holds for the second brand without the test being edited, and
  `test_the_repository_ships_exactly_one_brand_and_it_is_furnished` pins the
  count so the walk cannot silently become vacuous.

- Ruling: this repository's floors govern `brands/relay`, not Relay's own
  "nothing below 24px". That rule is written for a fourteen-slide reference
  deck whose densest slide is a five-row table; the deck built against this
  brand puts three domain cells and five tags on one slide, and a 12.2 pt
  floor would not fit it. Every Relay size is mapped onto the repository's
  scale instead, and `brands/relay/style.py`'s docstring says so where a
  reader will find it - cost if wrong: the mono labels read small in a large
  room; raise `T_COL_SUB`, `T_FOOT` and `T_META` and re-fit two slides.

- Ruling: `primitives.settext`, `textbox` and `add_para` take `spc`, a
  letter-spacing in points, and `metrics.width`, `lines` and `fits` take the
  same. A design system whose display type is set at -0.035em and whose
  labels are set at +0.12em is a different system without it, and tracking
  is typography mechanics carrying no colour and no brand knowledge, so it
  belongs in the core while the amount stays in `brands/relay/style.py` as
  `TRACK_*` em constants. Tracking is added AFTER the padding factor rather
  than multiplied by it: the factor calibrates glyph advances, tracking is
  exact - cost if wrong: a mono label measured untracked is about a fifth
  narrower than it renders and the register never sees the overflow; the
  builder passes the same `spc` to both halves and `Fit.wide` catches it.
  Caught by
  `tests/test_primitives.py::test_settext_writes_letter_spacing_in_hundredths_of_a_point`,
  `tests/test_primitives.py::test_no_spc_attribute_is_written_when_tracking_is_zero`,
  `tests/test_metrics.py::test_tracking_is_added_after_the_padding_factor_not_multiplied_by_it`
  and `tests/test_metrics.py::test_tracking_reaches_the_wrap_simulator`.

- Ruling: the inverse (dark) cover is painted per slide as one full-bleed
  `rrect`, NOT as a second layout in the template, so `make_template.py`,
  `BrandSpec` and the template contract are unchanged. Relay's own kit does
  exactly this - `data-theme="dark"` on the section element, not a second
  master - and python-pptx cannot add a layout, so a second one would mean
  cloning a `p:sldLayout` part and re-minting its relationships by hand,
  which is the class of surgery the gate's doubled COM open exists to catch.
  `assert_native.py` fails on a slide-sized *picture*, not a slide-sized
  autoshape, so the ground costs one shape and no doctrine - cost if wrong:
  one autoshape per dark slide and a background a hand-editor can select and
  delete; build the second layout and give `BrandSpec` a layout list.

- Ruling: `brands/relay` ships Noto Sans (OFL 1.1) as a fourth substitution
  on top of Relay's three, and has no monospaced face at all. Relay names
  Space Grotesk, Public Sans and JetBrains Mono and ships no binaries; none
  of the three is installed, `uv --offline` cannot fetch one, and the
  nearest Windows grotesk is proprietary - which may be pointed at but never
  committed, and pointing at the Windows font directory would make the
  native build machine-dependent when `references/00-pipeline.md`'s platform
  matrix says only QA is. The mono role is carried by uppercase plus
  `TRACK_MONO` instead - cost if wrong: the deck is less distinctive than
  the system it claims; `brands/relay/fonts/README.md` records what was
  looked for and where, and swapping the faces in is two lines plus a
  recalibration of `width_factor` and `wrap_factor`.

- Ruling: the Relay builder draws with `deck_kit.primitives` and a local
  `Draw` class rather than with `deck_kit.components`. Every function in
  `components` hard-codes a corner radius of 6, 7 or 8 and several assume a
  gradient band; Relay's radius is 0 for a surface and 2 for a control, and
  its readme forbids gradients outright. `components` is a vocabulary, not a
  contract - cost if wrong: one deck's worth of drawing code lives in a
  builder rather than in the kit; move `Draw`'s methods into
  `deck_kit.components` behind a radius parameter when a second
  Relay-shaped deck needs them.

- Ruling (SUPERSEDED by "relay default", below): the Relay build of the AI
  horizon deck imported `notes_data.py` from the placeholder build rather
  than copying it, and defined its own copy of the slide content. The
  spoken content was the same deck in a different design system and a
  second copy would have drifted; the slide content was the spec's closed
  copy, and each deck's builder owning the port of its own spec is the
  pipeline's discipline - cost if wrong: editing one deck's notes silently
  changes the other's teleprompter. There is now one build of that deck and
  the question does not arise.

- Ruling: `scripts/crop_icons.py` carries one `SHEETS` entry per icon sheet
  and takes `--sheet NAME`, defaulting to `example`, rather than one
  module-level `LIST`. The MUST-match comment is still the only contract
  between a sheet and its cropper, and now each half names the other
  explicitly - cost if wrong: a third sheet is added without an entry and
  crops against the wrong names; the comment in both files says so, and the
  icons are committed rather than regenerated, so a mismatch is caught the
  first time a builder places one, because `primitives.icon` raises.

- Ruling: the Relay drafts link `brands/relay/slide.css` rather than
  `templates/slide.css`. That file's `@import` is hard-wired to the example
  brand's tokens and its header furniture is the example brand's header - a
  tagline row and a two-mark lockup top right - while Relay's header is a
  3 px rule, a mono kicker and a display heading with the mark in the
  footer. `templates/components.css` stays brand-neutral and is imported by
  both - cost if wrong: two skeletons to keep in step; `tests/test_html_stage.py`
  holds both brands to the same mirror rule and both draft sets to the same
  draft rules.


## Session 2026-09-09 - relay default

Three decisions, all the user's: fetch the faces a brand names instead of
substituting for them; make `brands/relay` the default design system; and
delete the second build of the AI horizon deck.

- Ruling: a brand's declared type faces are FETCHED, not substituted.
  `scripts/fetch_fonts.py` reads `brands/<name>/fonts.toml` - family, role,
  weight, filename, URL, sha256, licence - downloads what is not on disk,
  verifies it against the pinned hash, writes the licence text beside it,
  and never rewrites a file whose hash already matches. Only the SIL Open
  Font License 1.1 is accepted; a proprietary face is named in `brand.py`
  and never copied in. The failure it closes is concrete and was in this
  repository: `brands/relay` names Space Grotesk, Public Sans and JetBrains
  Mono, all three OFL, and shipped Noto Sans for all three with a README
  arguing that none was installed and `uv --offline` could fetch nothing.
  The network was reachable; nobody had looked - cost if wrong: a fetcher is
  one line of TOML away from committing a proprietary binary, which is a
  licence violation rather than a mistake, so the licence field is checked
  against one exact string and a non-OFL entry is a refusal, not a warning.
  Caught by `tests/test_fetch_fonts.py::test_a_non_ofl_licence_is_refused`,
  `::test_a_face_whose_bytes_moved_is_refused_not_overwritten` and
  `::test_a_download_that_does_not_match_the_pin_writes_nothing`.

- Ruling: the manifest is `brands/<name>/fonts.toml`, a sibling of
  `assets.toml`, and not a `[[font]]` table inside it.
  `scripts/lint_deck.py manifest --brand <name>` regenerates `assets.toml`
  wholesale from what is on disk and would silently drop any block it did
  not generate - cost if wrong: two files to keep in step for a fetched
  face; both name each other, and the lint fails on a hash that moved in
  either. Caught by
  `tests/test_fetch_fonts.py::test_the_relay_brand_declares_six_ofl_faces_and_has_them_all`.

- Ruling: measurement factors are per FACE, not per brand. `BrandSpec` grew
  `display_*` and `mono_*` fields and a `metrics(role="sans")` method; a
  brand that declares one family answers every role with it, so single-family
  brands are unchanged. The factors calibrate how a face renders against how
  PIL measures it, and sharing one pair across three families measures two
  of them against the third - cost if wrong: a title measured with the body
  face's factor overflows without a warning, which is the one thing the
  register exists to stop. Caught by
  `tests/test_brand.py::test_each_role_carries_its_own_measurement_factors`,
  `::test_a_one_family_brand_answers_every_role` and
  `tests/test_style.py::test_header_measures_the_title_against_the_display_face`.

- Ruling: the calibration keeps the repository's existing headroom rather
  than re-deciding it. The measured ratio of PowerPoint's pen advance to
  PIL's `getlength` came out within a percent of 1 at 24 pt for all four
  families measured, so 1.12 was never "PowerPoint sets ten percent looser";
  it is headroom, and the new factors are 1.12 (or 1.07) x R_family /
  R_noto, taken at whichever of two sizes gave the larger answer. Space
  Grotesk 1.11 / 1.06, Public Sans 1.11 / 1.06, JetBrains Mono 1.12 / 1.07 -
  cost if wrong: two of the three land on the same pair, which reads like a
  shortcut and is not; the method and the observed numbers are in
  `brands/relay/brand.py`'s docstring so the next reader can redo it rather
  than trust it.

- Ruling: `brands/relay` is the default design system. `SKILL.md`'s intake,
  `templates/spec.md`, `references/01`, `references/00`, `references/02` and
  `templates/slide.css`'s `@import` all name it, and `discover.py` recommends
  it when the user has none of their own. The cost clause is the one that
  matters: **a default that is a placeholder is a default nobody wants to
  ship**, and every deck built on it has to be redesigned before it leaves
  the building, while a default that is a real system produces a deck that
  is presentable on the first build and wrong only in its identity - cost if
  wrong: a user with no brand gets slides that look like Relay rather than
  like nothing, and has to say so; `discover.py` names the brand it chose in
  one line and the spec's front matter records it, so the choice is visible
  before a slide is drawn rather than after.

- Ruling: `brands/example` and `brands/example2` stay, as TEST FIXTURES
  only. Two brands with two different master names are what make the Phase 2
  transplant a real cross-master merge rather than a template merged with
  itself, and `brands/example` is the second brand `tests/test_html_stage.py`
  needs to prove the mirror rule is about brands rather than about one
  brand. Their module docstrings say so, README's map says so, and
  `discover.py` prints "test fixture, not a design system" against each and
  never recommends one - cost if wrong: someone builds a client deck on a
  placeholder palette; the report line and the two docstrings are the three
  places that would have to be missed at once.

  **2026-09-09, one brand:** **reversed.** Both packages were deleted; see
  "Session 2026-09-09 - one brand" at the end of this file for what replaced
  each of the three things this ruling protected.

- Ruling: the placeholder-brand build of the AI horizon deck is deleted and
  the Relay build takes its name. `examples/ai-horizon/` is now the Relay
  deck, `notes_data.py` moved with it, and the gate runs one `ai-horizon`
  step instead of two. Two builds of one deck proved that a builder can be
  ported and nothing else, and they cost a duplicated copy deck, a second
  `Fit` class, a second lint rules file and a pair of specs whose exact
  tables had to be asserted equal - cost if wrong: the repository loses its
  one worked example of the same content in two design systems; what it
  demonstrated is written down in `references/02-html-stage.md` instead, and
  the gate still exercises `brands/example` through the matrix, the
  furniture, the round trip and the walkthrough.

  **2026-09-09, one brand:** `brands/example` was removed; those four now exercise
  `brands/relay`.

- Ruling: `examples/capability-matrix`, `examples/kit-furniture`,
  `examples/integration` and `examples/walkthrough` stay on the fixture
  brand. **`examples/capability-matrix` was deleted on 2026-09-09, "one
  deck"; read this ruling as naming the three that remain.** What they prove is the library and the merge, not a design; a real
  design system would make their assertions harder to read and would not
  make them stronger - cost if wrong: nothing exercises `brands/relay`
  through the Phase 2 round trip, which was already a deferred minor and
  still is; README says which decks run on the fixture and why.

  **2026-09-09, one brand:** **reversed.** All four moved onto `brands/relay`, and
  the deferred minor this ruling's cost clause names - nothing exercising
  `brands/relay` through the Phase 2 round trip - is closed.

- Ruling: `brands/relay/brand.py` sets `serif=None`. Relay has no serif role
  at all, and the field named "Noto Serif" - a face this brand does not ship
  and nothing reads - cost if wrong: nothing today; a future builder
  reaching for `spec.serif` gets `None` and fails at the call rather than
  writing a font name no machine can resolve.

- Ruling: `style.header()` grew an optional `display=` keyword rather than a
  new positional parameter or a `BrandSpec` argument. Every builder and
  `tests/test_style.py` call `header` positionally and the first seven
  parameters are unchanged; a brand with one family passes nothing and gets
  what it always got - cost if wrong: a builder that forgets to pass it
  measures the title against the body face, which is a smaller error than
  the one before it (measuring against another BRAND's face) and is caught
  by eye in the export; `tests/test_style.py` walks the keyword over every
  furnished brand.

- OBSERVED, not a ruling: `brands/relay_design_system/` is not in this
  repository and never was. It is a third-party download; what is committed
  is the derivation. `tests/test_discover.py` had a test calling `next(...)`
  over a search for it, which raised `StopIteration` on any tree without it -
  that is every tree anyone else clones, and this one. The test now asserts
  the absence explicitly and still checks the shape when the directory is
  put back. README says the same in its Provenance section, so a reader who
  follows a citation to that path knows why it is not there.

## Session 2026-09-09 - one brand

`brands/example` and `brands/example2` are deleted. `brands/relay` is the
only brand in the repository, and every builder, every test and every gate
step runs on it.

- Ruling: one brand, not three. The two fixture packages were carried for
  three reasons and each is now met without them: the Phase 2 transplant's
  second slide master is a VARIANT of Relay's own contract, the mirror rule
  in `tests/test_html_stage.py` is parametrized over a list read from the
  brands directory rather than over two hardcoded brands, and every test that
  needed "a brand to load" loads `relay`. **The cost clause is the same one
  the default's ruling turns on: a placeholder that only the repository's own
  tests ever see is a second design system to keep in step, and it was not
  kept in step** - its `tokens.css` had to mirror a `style.py` nobody drew a
  slide with, its logos were regenerated by a script that wrote all four
  marks whichever brand you wanted, and its README argued for a font
  substitution that the fetcher had already made unnecessary - cost if wrong:
  the gate's assertions are now read against a palette with opinions, so a
  count that moves because Relay draws a wordmark in the footer reads as a
  brand change rather than as a regression; the gate comments name the
  derivation for every count, and `no warnings` is still the build's own
  verdict.

- Ruling: the second slide master comes from `scripts/make_template.py
  --brand relay --variant donor`, not from a second brand package.
  `variant_spec` appends " (NAME)" to the master and layout names through
  `dataclasses.replace` - which re-runs `BrandSpec.__post_init__`, so the
  by-name-never-by-index rule is enforced on the copy - and the ground is
  painted in the brand's own `PANEL` instead of `BG_TOP`. What makes the
  merge cross-master is unchanged and is now asserted against the generated
  files rather than inferred from a package count: both templates put their
  master at `ppt/slideMasters/slideMaster1.xml` and both carry
  `p:sldLayoutId` 2147483655, so `merge` mints a free part name and re-mints
  a real collision (OBSERVED in `out/v2/final.pptx`: `slideMaster2.xml`,
  id 2147483657), while the master and layout NAMES differ so `deck._layout`
  can still resolve by name - cost if wrong: the transplant silently becomes
  a template merged with itself and catalogue item 5 stops being tested;
  caught by
  `tests/test_template.py::test_a_variant_template_is_a_second_master_of_the_same_brand`
  and by the gate's new `template2 contract` and `template2 opens twice`
  steps.

- Ruling: the variant's ground is the brand's `PANEL`, so the two masters are
  distinguishable by eye and not only in the XML. `brands/example2`'s own
  docstring conceded that its palette difference "does not reliably
  distinguish" the two in a rendered PNG; white against `#F5F5F4` does - cost
  if wrong: nothing functional, and the colour still comes from the brand's
  style module rather than from the script, so `make_template.py` holds no
  colour value. Caught by
  `tests/test_template.py::test_the_variant_ground_is_visibly_not_the_brands_own`.

- Ruling: `deck_kit.components.matrix_frame` takes the icon colour key from
  the brand (`style.ICON_KEY`) and the frame ink as an `accent` argument.
  The kit hardcoded the literal `"blue"` for the key, which was one brand's
  value living in `src/deck_kit`, and drew the column headers, their rule and
  the row labels in `style.BLUE` - which in Relay is the signal orange, and
  Relay allows one orange element per view. `build_matrix.py` passes
  `accent=s.NAVY` and spends the signal on the enablers label alone (**that
  builder was deleted on 2026-09-09, "one deck"; the caller is now
  `examples/ai-horizon/build_ai_horizon.py`'s `readiness()`, which passes the
  same argument for the same reason**) - cost if wrong: a brand whose icons are cropped in another key raises mid-deck, and
  a matrix drawn entirely in the accent spends a budget the design system
  says is one element wide. Caught by
  `tests/test_style.py::test_every_brand_names_its_icon_colour_key`.

- Ruling: `scripts/crop_icons.py --sheet` is now REQUIRED, and its
  `"example"` entry became `"template"` - the sheet it names is
  `templates/iconsheet.html`, the skeleton a new brand copies, and nothing in
  the repository is cropped from it. The filenames the cropper writes end in
  the sheet's colour key, so a default let a screenshot of one sheet be
  cropped under another sheet's names, producing plausible files that
  `primitives.icon` would raise on weeks later - cost if wrong: one more flag
  to type on the one invocation there is, which
  `docs/handoff/2026-09-09-relay-default.md` section 3 already spelled out in
  full.

- Ruling: `scripts/make_placeholder_logos.py` keeps only `wordmark()` and
  writes only Relay's two marks. This closes the deferred minor that it
  rewrote all four marks on every run - cost if wrong: nothing; the script
  still has exactly one purpose, and `assets.toml` records both outputs as
  PLACEHOLDER.

- Ruling: the golden measurements in `tests/test_metrics.py` were re-measured
  against Public Sans at the factors `brands/relay` calibrated (1.11 / 1.06),
  not converted from the Noto figures by arithmetic. Two of them moved for a
  reason worth recording: Public Sans's bold is close enough to its regular
  that `m.width("Capability", 9.5, bold=True)` equals the regular exactly -
  PIL loads a face at an integer PIXEL size, so 9.5 pt is measured at 12 px
  and the two advances round together - so the bold-is-wider assertion moved
  to "Feature Store", and the two wrap-count assertions moved to the avails
  where the counts actually differ (323 px and 86 px) rather than being
  relaxed to `>=` - cost if wrong: a calibration drift stops being caught;
  every number was measured once and pinned, and the test comments say which
  band each came from.

- Ruling: `scripts/discover.py` lost its `PLACEHOLDER_BRANDS` special case
  and the `fixture` field on a brand record. A brand package on disk is a
  candidate; the recommendation on this tree is "use brand relay" because
  relay is the only one, not because two others were filtered out - cost if
  wrong: a future fixture brand would be offered for a deck, which is an
  argument for not adding one. Caught by
  `tests/test_discover.py::test_the_repository_recommends_its_one_brand`,
  and the multi-brand branch is still covered by
  `test_recommendation_walks_one_brand_then_a_master_then_the_default` over a
  two-brand tmp tree.

## Session 2026-09-09 - one deck

`examples/capability-matrix` is **deleted**. Its two slides were an artifact
of another engagement - a fraud-detection target model, in a vocabulary
nothing else in this repository speaks - and the only argument for keeping
them was that they were the sole caller of `matrix_frame`, `flow_pills`,
`Pill`, `PillStyle`, `draw_pill` and `pill_w`. That coverage is now a slide
of the AI horizon deck, `S09 What has to be true by when`, and the deck is
ten slides rather than nine.

- Ruling: the kit's coverage moves onto a slide of the real deck rather than
  living in an example directory of its own. An example kept alive only to
  keep a function called is a cost with no reader: it carries its own drafts,
  its own copy, four gate steps and a shape-count block, and every session
  that touches the kit has to re-derive all of it for a slide nobody presents.
  A slide that belongs to the deck's argument is read every time the deck is
  read, and the readiness matrix is the argument's missing half - the other
  nine slides say what will happen, S09 says what it rests on - cost if
  wrong: the kit's components are exercised by ONE slide instead of two, so a
  regression that only shows on a second layout is not caught; the unit tests
  in `tests/test_components.py` are what actually cover the components, and
  the deck covers them being called together.

- Ruling: `deck_kit.components` takes the radius as a parameter -
  `draw_pill(rad=7)`, `flow_pills(rad=7)`, `matrix_frame(cell_rad=8)` - and
  `brands/relay` passes `RAD_CONTROL` and `RAD_SURFACE`. The defaults are the
  literals that were there, so no existing call moves. A radius is a
  design-system value and `src/deck_kit` holds no brand knowledge; without
  the parameter the choice was between a slide that draws lozenges on a
  system whose readme forbids them and a component nobody calls - cost if
  wrong: two more keyword arguments on two functions. Caught by
  `tests/test_components.py::test_draw_pill_takes_the_brands_control_radius`,
  `::test_flow_pills_hands_its_radius_to_every_pill_it_draws` and
  `::test_matrix_frame_takes_the_brands_surface_radius`.

- Ruling: `templates/components.css` gains `.pill--red`, `.pill--quiet`,
  `.pill--square`, `.cell--square`, `.matrix > .head--ink` and `.ink-red`.
  Every one of them is a `PillStyle` or a `matrix_frame` argument the kit
  already took and the CSS could not say, and a draft may use only classes a
  stylesheet defines
  (`tests/test_html_stage.py::test_each_draft_uses_only_classes_the_stylesheets_define`)
  - so the vocabulary had to grow or the draft had to hand-roll CSS, which is
  the thing that test exists to stop - cost if wrong: six more classes in a
  file that is already the kit's whole vocabulary; each names the argument it
  stands for in its comment.

- Ruling: `loop_line` and `explain_box` are now exercised by unit tests only.
  `loop_line` had exactly one caller, the deleted builder, and S09 does not
  use it: Relay has no rounded ghost panel to put a note in, and the deck's
  own `noteline` - a line over a rule - is what this brand does instead.
  `explain_box` already had no caller before this session - cost if wrong:
  neither is proved to survive a real build, only a slide in a test; give
  `loop_line` a radius parameter the way the pills got one and put it under
  S09's matrix when a slide needs a transversal note.

- Ruling: the deck's time budget went from fifteen minutes to sixteen rather
  than a minute being taken off another slide. The budget is a statement
  about the deck, and a deck with a tenth slide is a minute longer; shaving
  S08 to keep the number would have made the number the thing being
  protected - spec front matter and `notes_data.py` - cost if wrong: a
  fifteen-minute slot needs one slide dropped, and the note that says which
  is `check()`'s "Total spoken time: 16 min" needle, which fails loudly.

- Ruling: the four gate steps the matrix owned - `build matrix`, `matrix is
  native`, `matrix opens twice`, `export matrix png` - are gone rather than
  retargeted. What they proved about the kit is proved by the `ai-horizon`
  step, which runs the same assertions on a ten-slide deck; what they proved
  about PowerPoint (the doubled open, the export) is proved on five other
  decks in the same file - cost if wrong: the gate is four steps shorter and
  one fewer package faces the doubled COM open; the deck it lost is the one
  that had the fewest slides.

## Session 2026-09-10 - html output

Two product rulings from the user, and the friction an unattended run of the
skill against somebody else's design system produced. That run's friction log
lives in its own tree, outside this repository; every item it raised is either
fixed below or deferred with a reason.

### The two product rulings

- Ruling: **the pipeline always starts from a design system plus HTML
  examples, and no route adopts a corporate PPTX master.** The intake's
  first question offers three answers - a design system the user points at
  (`discover.py --design-system PATH`), one discovery found, or the default
  `brands/relay` - and `inspect_template.py` is kept as the verifier of a
  *generated* template rather than as an adoption path. The evidence is what
  a real corporate master looks like: four slide masters all named `''`, a
  hundred layouts with names repeated across masters and once within one,
  and 21 embedded font parts. The contract's one rule is by name, never by
  index, and that file supplies no names to bind to; the only two moves
  available were to write an empty `master_name` (an index in disguise,
  which passed the verifier) or to rename masters inside the user's own
  artifact - `SKILL.md`, `README.md`, `references/00`, `01` and `03`,
  `templates/spec.md` - cost if wrong: a user with a corporate master and no
  design system has no route, and the answer for them is to derive a design
  system from the master by hand, which is a bigger job than this repository
  was pretending it was.

- Ruling: **the PPTX is optional, and `html` is a first-class output the
  intake offers by name.** A fourth front-matter line,
  `**Output:** <html | pptx | both>`, default `both`. `html` stops the
  pipeline after the draft stage: the drafts become the deck,
  `scripts/build_html_deck.py` builds one navigable, printable stage page
  from them, and the deliverable is that page - which needs no Windows and
  no PowerPoint anywhere. `both` ships the stage page as well as the file -
  `templates/spec.md`, `SKILL.md`, `references/00`, `01`, `02` and `05` -
  cost if wrong: a fourth question in every intake, and a spec line to fill
  in for decks that were always going to be `both`.

- Ruling: the stage page **embeds** each draft rather than iframing it.
  An iframe would keep each draft's own document intact and need no URL
  rewriting, but browsers print an iframe as one clipped box or not at all,
  and "print to PDF yields a deck" is half of what the page is for - cost if
  wrong: the rewriting is the part that can be wrong, and it is pinned by
  `tests/test_build_html_deck.py::test_relative_links_are_rewritten_from_the_output_directory`.

- Ruling: the stage page **refuses** a draft that links an absolute or
  protocol-relative URL, rather than passing it through. A deck that fetches
  a font from a CDN renders differently on the client's machine and not at
  all offline, and the failure is invisible until the room it happens in -
  cost if wrong: a draft that legitimately wants a remote asset has to
  commit it first, which is the rule the assets manifest already keeps.

- Ruling: `capture_drafts.py` **exits 0** when Playwright is not importable,
  printing the serve command and one line per slide giving the URL and the
  file to write. An offline `uv` cannot fetch Playwright, and that is the
  machine the rest of this repository is documented for, so treating its
  absence as a failure would make the HTML gate step permanently red on the
  only machine that runs it. `--require` is there for a pipeline that has
  decided otherwise - cost if wrong: a capture step that silently does
  nothing; the composition steps that consume its output say SKIPPED with
  the count they found, and the stage build and the lint, which need nothing
  but Python, still have to pass.

- Ruling: one `lint.toml` per deck, for both outputs, with `--expect-checks`
  one lower on the drafts directory. The content constraints belong to the
  deck and not to the file format it ships as, and a second rules file is a
  second thing to drift - `examples/ai-horizon/lint.toml` - cost if wrong:
  a deck whose two outputs genuinely need different rules writes a second
  file, and `--expect-checks` catches the first check that stops running.

- Ruling: `[kickers]` **folds case on a drafts directory and no other check
  does.** A kicker is a label and a design system uppercases its labels in
  CSS, so the markup reads `01. How to read this` where the slide reads
  `01. HOW TO READ THIS`. `required` and `exact` compare strings the spec
  fixed and must not fold. The alternative - resolving `text-transform` by
  parsing the linked stylesheets - needs selector matching and cascade
  order, and `.chiplist .tag { text-transform: none }` in Relay's own CSS is
  the case a crude version gets wrong; getting it subtly wrong would
  silently change what `[exact]` compares - cost if wrong: a draft whose
  kicker is genuinely lowercase on screen passes the check; nothing else
  moves.

### The friction, fixed

- Ruling: `discover.py`'s evidence test now takes a named token sheet beside
  a readme (`colors_and_type.css`), any top-level sheet that declares custom
  properties on `:root`, a `tokens/` directory or a `_ds_manifest.json`, and
  it prefers the **outermost** match - a design system ships sample UI kits
  and each kit has a `styles.css`. The run that prompted this reported the
  kit, `ui_kits/analytics-dashboard`, and not the system above it, and then
  recommended `brands/relay`: the exact failure the script's own docstring
  says it exists to prevent - cost if wrong: a directory that is not a
  design system is reported as one, which costs a line in a report the user
  reads.

- Ruling: a design system found on disk **outranks** `brands/relay` in the
  recommendation, and any other brand package outranks both. "The repository
  ships one default brand" is not a fact about the user's identity. Ranked
  under that, a directory whose only evidence is `:root` custom properties
  is weaker than one that declares itself, because a deck's own working CSS
  looks like the former - observed: a deck directory holding `theme.css` and
  `dya-matrix.css` sorted ahead of the real system by name alone - cost if
  wrong: the report lists both and the user picks.

- Ruling: candidate masters are **inventory, never a recommendation**, and
  the section is grouped: a directory holding more than five is one line
  with a count, layout lists stop at six names, and `build/`, `dist/` and
  `_archive` join `out/` in the pruned set. The report that prompted this
  was 563 lines, 548 of them ninety copies of one corporate template under
  one deck's build directory, with the single actionable line at the bottom.
  The recommendation is now printed first as well as last - cost if wrong: a
  user with six genuinely different masters in one directory sees a count
  instead of a list, and `--json` still carries every one.

- Ruling: `BrandSpec` rejects an empty or whitespace `master_name` /
  `layout_name` with the same force as an index, and `inspect_template.py`
  prints a remedy line under the failed clause. An empty `master_name`
  passed `__post_init__`, then passed the verifier's `in names` clause
  against a deck whose masters were all unnamed, while `deck._layout` bound
  to whichever came first - cost if wrong: a brand that legitimately wants
  an empty name, which is not a thing.

- Ruling: `preview.py serve` no longer sets `allow_reuse_address`, refuses a
  busy port with a clear message, and **proves the root before announcing
  it** by fetching one file it knows is under the root and comparing the
  bytes. On Windows `SO_REUSEADDR` let a second server bind a port a stale
  one still held: the new server printed `serving <the new root>` and
  answered 404 to everything, and the printed line was the only evidence and
  it was false - cost if wrong: a serve on a tree with no readable file
  prints "holds no file to verify the root with" and serves anyway.

- Ruling: `TextMetrics.lines` normalises a bare string the way
  `primitives.settext` does, through one shared `metrics.norm_runs`. The
  doctrine of the PPTX stage is "measure with the same thing you write
  with", so the two calls sit on adjacent lines in every builder, and they
  did not take the same argument: `lines("some copy", ...)` raised
  `IndexError: string index out of range` from four frames inside the
  library, naming nothing about the caller - cost if wrong: none; the
  normalisation is the one `settext` has always done.

- Ruling: `brands/relay`'s `header()` measures the **sub** against
  `SUB_AVAIL` as well as the title against `TITLE_AVAIL`. `SUB_AVAIL`'s
  comment - "one line for every sub in the deck" - was a claim nothing
  checked, and a sub that wrapped to two lines pushed into the content under
  it while the build printed "no warnings" - cost if wrong: a deck whose sub
  is deliberately two lines has to say so by widening `SUB_AVAIL` or by not
  using `header()`.

- Ruling: the shipped kicker pattern names its accented capitals,
  `[A-ZÁÉÍÓÚÜÑ]`, in both example rules files, in `references/05-qa.md` and
  in the new `templates/lint.toml`. `[A-Z]` stops at the first accented
  capital, so on a Spanish deck `01. DÓNDE ESTÁ LA PRESIÓN` matched nothing
  and was reported as "no kicker" - the report said the opposite of what was
  true - and `03. DISEÑO Y OPERACIÓN` matched the prefix `03. DISE` and
  reported a kicker that does not exist, which invites adding that prefix to
  the allowlist and makes the check permanently wrong - cost if wrong: a
  language whose capitals are outside the class extends it, and the
  reference says so.

- Ruling: `[forbidden]` takes `tokens_file`, a path outside the deck
  directory. The rules file travels with the deck, so listing a client's own
  name in it writes that name into the one file it must not be in, and the
  check could enforce only the vendor half of the constraint. What it does
  not solve is the report, which prints the token on stdout; the reference
  says so rather than implying the problem is closed - cost if wrong: a
  rules file that points at a path a second machine does not have fails
  loudly, with `FAIL:` and no traceback.

- Ruling: `lint_deck.py --brand NAME` runs the `[assets]` check with no
  `--deck` and no `--rules`. "Set up a brand" step 4 asks for it two stages
  before either exists, and both were required, so the manifest could only
  be verified by building a deck first - cost if wrong: one more CLI shape
  to keep working, pinned by its own test.

- Ruling: the `**Design system:**` placeholder gains
  `brand name @ path outside the repository`, and `DECKWRIGHT_BRANDS` is
  named in `SKILL.md` and `README.md`. It is the only way to keep an
  employer's brand out of this repository, which the repository's own
  provenance rule makes the normal case, and it was documented nowhere
  outside a docstring - cost if wrong: none.

- Ruling: `SKILL.md` says once, at the top, that every `python <script>` in
  it means the `uv run --offline --no-project --with ...` prefix `README.md`
  requires, rather than repeating the prefix on thirty lines - cost if
  wrong: a reader who copies one line out of context and runs it against a
  bare interpreter, which fails immediately and loudly.

- Ruling: `references/02-html-stage.md`'s capture command drops `--offline`
  and says why, and the "any browser does the same job" sentence moves up
  next to it. The documented command could not run on the machine the rest
  of the pipeline is documented for, and the sentence that made that
  survivable was three paragraphs below - cost if wrong: none.

- Ruling: `references/03-pptx-stage.md`'s vocabulary table says which
  primitives land in `--autoshapes`, `--min-pictures` and `--min-freeforms`,
  and that `rule` is an `rrect` so every hairline is counted. On a Relay
  deck the hairlines can be most of the count, and the number was previously
  derivable only by reading `primitives.py` - cost if wrong: none.

- Ruling: `brands/relay/style.py`'s COPYRIGHT comment states the true
  reason. It said the string is written uppercase "so the string this check
  looks for is the string on the slide", which `settext` contradicts -
  `upper=True` writes the uppercased string into the XML either way. The
  real reason is that the spec, the rules file and the constant should read
  the same characters as the slide without a reader applying the transform
  in their head - cost if wrong: none.

### The friction, deferred

- Deferred: F-7, "the intake's master route needs a brand that does not
  exist yet". The route it complains about is gone: there is no master
  route, so `inspect_template.py` never runs before a brand exists. Letting
  it run with no `--brand` and merely report a deck would be a new feature
  serving no documented step - reason: the product ruling above removed the
  need rather than the friction.

- Deferred: F-9's second half, the two-tree serving root. Documented rather
  than fixed - `references/02-html-stage.md` now says the root that
  `DECKWRIGHT_BRANDS` implies is higher than anyone expects - because the
  alternative is a server that merges two roots, and a stylesheet whose
  `@import` resolves differently under the preview server than under any
  other server is worse than a high root.

- Deferred: F-12's `hashes` alternative. `tokens_file` is implemented;
  hashing the tokens is not, because "does this text contain a token whose
  sha256 is X" needs every substring of every slide hashed, which is not a
  check, it is a search - reason: the cost is real and the benefit over a
  file outside the deck directory is small.

- Deferred: F-18's wider version, a machine-checked mapping from every
  primitive to its `assert_native.py` bucket. One clause in the vocabulary
  table says it; a test that walked `primitives.py` and asserted the bucket
  of each function would be asserting python-pptx's own behaviour - reason:
  the shape counts in every builder's docstring are the real check, and they
  are exact.

- Deferred: capturing the stage page itself, rather than the drafts, for
  composition QA. The page scales its slide to the window and hides all but
  one, so a capture of it is a capture of the viewport and not of the
  canvas; `capture_drafts.py` opens each draft at 1280x720 instead, which is
  the geometry every crop box in `references/05-qa.md` is derived from -
  reason: two ways to produce `sNN.png` would be two ways for the boxes to
  be wrong.

## Session 2026-09-10 - capture is a requirement

One product ruling from the user, and everything that followed from taking
it seriously. Before this session `scripts/capture_drafts.py` printed
`CAPTURE SKIPPED: Playwright is not importable`, exited 0, and the gate's
`ai-horizon html` step reported SKIPPED and stayed green. A deck could reach
a stage page with ten drafts nobody had looked at, and nothing said so.

### The ruling

- Ruling: **seeing its own work is a requirement of this skill, not an
  optional nicety.** An agent that cannot screenshot its drafts cannot judge
  them, and the quality of the final deck falls. So the capture is a hard
  stop rather than a skip: `capture_drafts.py` tries Python Playwright, then
  every Chromium-family binary on the machine, and then exits non-zero with
  `CAPTURE UNAVAILABLE`, three remedies and the real diagnostics for every
  route it tried; `scripts/doctor.py` reports the same requirement at the
  intake's step 0; `SKILL.md` gains a Requirements block and a draft step
  that says to stop rather than proceed to the port - `SKILL.md`,
  `references/00-pipeline.md`, `references/02-html-stage.md`,
  `references/05-qa.md`, `README.md`, `examples/ai-horizon/run_html.ps1`,
  `scripts/gate.ps1` - cost if wrong: a machine with no browser at all can
  no longer run the HTML loop to green, which is the point; the remedy list
  is three lines long and one of them is an environment variable.

### What the browser route actually took

- Ruling: the browser search order is the one measured on the machine of
  record - the ms-playwright Chromium, then that package's
  `chrome-headless-shell`, then Google Chrome (Program Files, Program Files
  (x86), LOCALAPPDATA), then Microsoft Edge (Program Files (x86), Program
  Files), with `DECKWRIGHT_BROWSER` in front of all of it. OBSERVED: the
  ms-playwright Chromium captured a draft in 1.4 s; Edge hung - an
  elevation-service error, a network-service restart, then
  `GPU process exited unexpectedly: exit_code=-1073741819` and the timeout.
  Pinned by
  `tests/test_capture_drafts.py::test_the_browser_search_order_is_the_measured_one`
  - cost if wrong: a machine whose best browser is last in the list pays the
  failover time, which is seconds, not minutes.

- Ruling: the headless-shell path is searched under **two** names,
  `chrome-headless-shell-win64/chrome-headless-shell.exe` and
  `chrome-win64/headless_shell.exe`. The second is the name the task
  description gave; the first is the name Playwright 1217 actually installs
  on this machine. Naming only one would have made the second-choice route
  silently unavailable, which is the route that ends up doing the work here
  - cost if wrong: one more path per package in a list that is already a
  search.

- Ruling: the throwaway `--user-data-dir` is the **retry**, not the default.
  The task described it as the default, for the good reason that a browser
  the user already has open refuses a second instance on its profile.
  MEASURED here: the ms-playwright Chromium captures in 1.4 s with no
  profile flag and **hangs until the timeout with one** - four separate
  profile paths tried, inside and outside the repository, long and short.
  Google Chrome works either way. So each slide gets one attempt with no
  profile and one with a throwaway profile under the output directory, which
  is one retry and covers both machines. Pinned by
  `tests/test_capture_drafts.py::test_the_retry_adds_a_throwaway_profile_and_then_gives_up`
  - cost if wrong: a browser that needs the profile flag pays one wasted
  attempt per slide before it gets it.

- Ruling: a per-capture timeout of 60 seconds, and a timed-out browser is
  killed with `taskkill /F /T` rather than `Popen.kill`. Chromium leaves
  renderer and GPU children behind, and a gate that leaves browser processes
  on the machine every run is its own failure. Pinned by
  `tests/test_capture_drafts.py::test_a_browser_that_hangs_times_out_and_the_next_one_captures`
  - cost if wrong: a genuinely slow machine has to raise `--timeout`.

- Ruling: **`--virtual-time-budget=3000` is in the browser command, and it
  is load-bearing.** `--screenshot` fires on the load event and the load
  event does not wait for web fonts; a `@font-face` still inside its block
  period renders its text invisibly. OBSERVED: the first run of the rewritten
  `run_html.ps1` composed a page-marker strip with rows 6, 7 and 10 blank,
  and the capture of `s06-toward-2050.html` turned out to carry every rule,
  box and icon in place and **not one word of text**. Measured afterwards
  against that draft: 1 blank in 8 without the flag, 0 in 20 with it. The
  Playwright route awaits `document.fonts.ready` for the same reason. Pinned
  by the flag assertion in
  `tests/test_capture_drafts.py::test_the_browser_command_is_the_invocation_that_was_measured`
  - cost if wrong: three seconds of virtual time per slide, which is not
  three seconds of wall clock. **This is the session's own evidence for the
  ruling**: the bug was invisible to the lint, invisible to the stage-page
  assertions, and obvious the moment somebody looked at the picture.

- Ruling: every capture is verified to be exactly `1280x720 x scale` before
  it counts. A browser that ignored the device scale writes a plausible
  1280x720 PNG that every 1600x900 crop box in `references/05-qa.md` then
  misses by a quarter, and a browser that failed to render exits 0 with no
  file at all. Pinned by
  `tests/test_capture_drafts.py::test_a_capture_of_the_wrong_size_is_refused`
  and `::test_a_capture_that_was_never_written_is_refused` - cost if wrong: a
  deliberate capture at another scale passes `--scale`, which the check
  reads.

- Ruling: `capture_drafts.py` serves through `preview.py`'s own `_Server` and
  root proof rather than a second copy, on a port chosen by binding 0, and it
  counts 404s instead of logging every request. The root proof is what stops
  a capture of ten slides that fetched no stylesheet, which is the failure
  `preview.py serve` was fixed for in the previous session; a hundred request
  lines per run would bury the capture's own output, while the number that
  matters is how many URLs did not resolve - cost if wrong: `/favicon.ico` is
  excluded by name, so a draft that genuinely wants one is not reported.

- Ruling: the routes that failed are printed **on success too**, not only on
  failure. OBSERVED on this machine: `chromium-1217/chrome.exe` sometimes
  succeeds in 1.4 s and sometimes exits 0 in 1.2 s having written nothing -
  the behaviour of a Chromium that forwarded its command line to an instance
  already holding the default profile - and the headless shell then captures
  all ten. Dropping that line once the capture worked is how a browser that
  fails half the time looks like one that always works - cost if wrong: two
  extra lines in a green gate log.

- Ruling: `--require` is gone. It existed to turn the skip into a failure for
  "a pipeline that has decided it needs the images", and every pipeline has
  now decided that - cost if wrong: nothing; no caller passed it.

### The doctor

- Ruling: `scripts/doctor.py` reports four requirements - python-pptx,
  Pillow and a browser REQUIRED, PowerPoint through COM OPTIONAL - with one
  line of consequence and the remedy per missing item, and exits non-zero on
  a missing REQUIRED one. `SKILL.md`'s intake runs it as step 0, before
  question 1, because every one of those fails late and expensively
  otherwise: a missing browser after ten drafts are written, a missing
  `python-pptx` after the spec is agreed. Pinned by `tests/test_doctor.py`
  and by
  `tests/test_skill.py::test_the_intake_runs_the_doctor_before_its_first_question`
  - cost if wrong: one command before the first question.

- Ruling: the PowerPoint probe reads `PowerPoint.Application` under
  `HKEY_CLASSES_ROOT` rather than starting PowerPoint. Launching the
  application to find out whether the application is installed would put a
  COM instance on the machine of every agent that runs the intake, and the
  registry key is what `check_pptx.ps1`'s `New-Object -ComObject` resolves
  anyway. Pinned by
  `tests/test_doctor.py::test_the_powerpoint_probe_never_launches_powerpoint`
  - cost if wrong: a PowerPoint installed without registering its COM class
  is reported missing, and it would not work through COM either.

- Ruling: the doctor's browser probe calls `capture_drafts.find_browsers`
  rather than restating the search, and its remedy text is asserted equal to
  the capture script's. A doctor that reports a browser the capture script
  would not find is worse than no doctor, and two remedy lists that drift are
  how a user is told to install something that would not have helped. Pinned
  by
  `tests/test_doctor.py::test_the_browser_probe_runs_capture_drafts_own_search`
  and `::test_the_browser_remedy_is_the_capture_scripts_own_three` - cost if
  wrong: none.

### The gate

- Ruling: `examples/ai-horizon/run_html.ps1` has no conditional left. The
  capture step must pass, a new `ten captures exist` step asserts the exact
  count, and the four composition steps run unconditionally on the captures.
  The `if ($pngs.Count -eq 10) { ... } else { SKIPPED }` block is gone: it
  was the mechanism by which a green run proved nothing about the pixels -
  cost if wrong: the HTML loop now needs a browser, which is the ruling.

- Ruling: the ai-horizon ledger records that this deck's captures came from
  `chrome-headless-shell` rather than from Python Playwright, because
  `SKILL.md` now says a fallback route is a ruling with a cost. Walking the
  rule on the repository's own deck is the only way to find out whether it is
  writable - cost if wrong: one entry per deck built on a machine without
  Playwright, which is most of them.
