# Integration - stage 4, editing a deck someone else keeps by hand

## 1. When this stage applies

The author edits the PPTX in PowerPoint between versions. A generated deck is
never the deliverable - it is transplanted into, or used to retext, the
author's own file, which is never overwritten. This stage exists for exactly
one situation: you are producing version N+1 of a deck the author has already
been editing by hand, not a fresh deck from a template (that is stage 3).

## 2. The versioned build pattern

`scripts/new_version.py`'s `Version` class is the driver. It copies the
author's source file into a work directory, asserts it is the file the build
was written against, then runs a numbered sequence of steps, each writing its
own `stepN_<name>.pptx`:

```python
v = Version(source=author_file, work=Path("work/v3"), final=Path("v3.pptx"))
v.expect(slide_count=30, fingerprint={14: "Fraud", 23: "Market"})
v.step("patch text", lambda prs: patch_text(prs, PATCHES))
v.step("delete", lambda prs: delete_positions(prs, [23, 14]), slides=28)
v.subprocess_step("merge", [sys.executable, "-m", "...", ...], slides=30)
v.finalise()
```

No step rewrites an earlier one - a failure at step 4 leaves `step3_*.pptx`
untouched, so the failure is diagnosable at the step that caused it rather
than by rerunning the whole pipeline with prints.

`expect()` is a fingerprint, not a checksum. A checksum would reject every
legitimate hand edit the author made since the last version; what actually
has to hold is the slide count and a title-substring at each position the
build is about to touch. `deck.assert_fingerprint` (`src/deck_kit/deck.py`)
is what `expect()` calls, and it walks through groups - a non-recursive title
read returns an empty fingerprint on a real deck whose title sits inside a
group, and a guard that fails on a correct file is a guard people stop
passing arguments to.

Two stages - the transplant and the font re-embed - run as separate
subprocesses via `subprocess_step`, not `step`. `merge.py` and `fonts.py`
work on the zip package directly and never open a `Presentation`
(`src/deck_kit/merge.py`'s own docstring: python-pptx has no model for a
foreign slide's master, and a half-modelled package is harder to reason about
than the zip). Running that surgery out of process means a crash inside it
cannot corrupt the in-memory `Presentation` the rest of the pipeline is
holding, and the intermediate written to disk before the crash is still
openable.

`Version.step` and `Version.subprocess_step` both take an optional
`slides=` count, asserted after the step runs (for `step`, before saving; for
`subprocess_step`, by re-opening the output, since the mutation ran out of
process). `delete_positions` and `merge` both change the slide count, and a
silent off-by-one there is invisible until someone presents the deck.

The worked example is the real `examples/integration/version.py`, which runs
this whole stage end to end on decks the repository builds itself:

1. `v.expect(slide_count=6, fingerprint={2: "The gap is", 6: "on a pill"})`
2. `v.step("patch text", ...)` - retext through run attribution (section 4)
3. `v.step("delete", lambda prs: delete_positions(prs, [5]), slides=5)`
4. `v.subprocess_step("merge", [..., "_merge_step.py", "--donor", ...], slides=7)`
5. `v.step("renumber", lambda prs: renumber_report.extend(renumber(...)), slides=7)`
6. `v.subprocess_step("fonts", [..., "_fonts_step.py", "--donor", ..., "--expect", "2"], slides=7)`
7. `v.finalise()`

## 3. Reading the author's file first

Before touching anything, dump the current file's text and diff it against
the last known version, to discover what the author changed by hand -
catalogue item 22. `scripts/dump_text.py` writes one line per paragraph
(`slide<TAB>shape_id<TAB>paragraph_index<TAB>text`), keyed the same way the
text map is keyed, so the dump can be read against the map directly.
`scripts/diff_package.py` then compares that dump - or any two `.pptx`
packages part by part - against the last known version and exits 1 if
anything differs, printing which parts were added, removed or changed.
Regenerating from a stale assumption destroys manual edits with no undo, so
this pair of scripts runs before any step that mutates.

## 4. Run attribution

PowerPoint fragments a paragraph into arbitrary runs by spellcheck state,
language tags and edit history, so a paragraph that reads as one sentence in
the UI can be four or five `<a:r>` elements underneath by the time a human
has edited it a few times. The naive fix - write the new string into run 0
and blank the rest - silently destroys any formatting that lived in the runs
being blanked: mid-sentence bold, colour, a different language tag.

The real algorithm, `patch_paragraph` (`src/deck_kit/textedit.py`): build a
character-to-run ownership array from the old text (index `i` maps to the run
that contains character `i`); run `difflib.SequenceMatcher(None, old, new,
autojunk=False)` over old and new; for each `equal` opcode route the
unchanged characters back to their owning run; for `delete`, drop them; for
`replace`/`insert`, attach the new characters to the run owning the first
affected old character (or the last run, for an insertion past the end); then
reassign every run's text and assert the reassembly reproduces the target
string exactly. `autojunk=False` is deliberate, not incidental - with
autojunk on, difflib treats frequently-repeated characters in long paragraphs
as junk and the opcodes stop being character-exact, so runs silently reflow
and mid-sentence bold can move to the wrong place.

`patch_text` is the caller most builders use directly: it takes
`(slide_number, old, new)` triples, matches each `old` against every
paragraph's `paragraph_text().strip()`, and requires **exactly one match**.
Zero and two matches are both hard failures, and for different reasons: zero
means the author has already edited that sentence, and applying nothing would
ship the old text silently as if the patch had succeeded; two means the patch
is ambiguous, and it would change whichever paragraph happens to come first
in document order - the wrong one as soon as either paragraph diverges later.
`patch_text` collects and validates every match before mutating anything, so
an ambiguous patch later in the list cannot leave an earlier one already
half-applied.

## 5. The text map

For wholesale retexting of an approved template (not surgical hand-edit
patching), `apply_text_map` takes a pure-data map,
`{slide: {shape_id: {paragraph_index: value}}}`, against a pure-mechanism
applier. Each paragraph value follows a three-valued protocol:

- a **string** collapses the paragraph to one run (`set_paragraph`'s str
  branch);
- a **list of strings** assigns run by run, preserving each run's own
  formatting, deep-copying the last run's formatting (via `append_runs`) when
  the list is longer than the paragraph's existing runs;
- **`None`** deletes the paragraph.

It is keyed on **shape id, resolved recursively through groups**
(`shapes_by_id`, built on `iter_shapes`) - never on name, because names
repeat inside a deck and a map keyed on name silently edits an arbitrary one
of the matching shapes; and never on position or text, because both change
under the author's hand.

The applier never raises. `apply_text_map` accumulates every mismatch -
missing shape, no text frame, paragraph index out of range - into a list of
`(slide_number, shape_id, problem)` tuples and returns it, rather than
stopping at the first one. A map covering a real deck has dozens of entries;
one hard failure per round trip against PowerPoint is a day of round trips to
find them all. A caller that wants a hard failure asserts the returned list
is empty, which is what the version driver does.

Because the map is keyed on shape id, building one requires knowing the ids
first: `scripts/inspect_shapes.py --deck deck.pptx --slide 14` walks the
slide (through groups, printing the group-name prefix) and prints each
shape's id, name, type, position, placeholder type, whether it carries an
`<a:fld>`, and its text - everything needed to write a map entry by hand.

## 6. The transplant

`merge.py`'s `merge(dest_path, src_path, specs, out_path)` copies whole
slides - with their layout, master, theme and media - from a source `.pptx`
into a destination `.pptx` at chosen positions. It works on the zip package
only (see section 2) and is built on two distinctions that are easy to get
backwards:

**Part-local rIds versus presentation-scope ids.** Relationship ids
(`r:id="rId7"`) are local to the part that declares them, so a copied part
keeps its own rIds unchanged; only the relationship **targets** are rewritten
to the new destination part names. What genuinely has to be re-minted, because
it must be unique across the whole presentation, is the small set of numeric
ids stored as XML attributes: `p:sldId/@id`, `p:sldMasterId/@id`,
`p:sldLayoutId/@id`. The re-minted `p:sldLayoutId` values live **inside the
copied slide master parts**, not in `ppt/presentation.xml` - reading
"presentation-scope" as "lives in presentation.xml" means missing the master
rewrite entirely, which is exactly the bug `merge()`'s master-id loop exists
to avoid.

**What is dropped, and why.** `merge()` transitively collects a part and
everything it relies on (`collect()`, walking each part's own `.rels`) except
relationships of type `notesSlide`, `comments` or `commentAuthors`
(`DROP_TYPES`). Notes slides are bound to the source package's notes master;
modern comments are bound to the source's author list. Both would carry
dangling references into a destination that has neither, so they are dropped,
together with the comment anchor extension (`<p:ext uri="{6950BFC3-...}">`)
that `_clean_slide` strips from the slide XML itself - not just the
relationship to it.

**The hidden flag's real location.** `show="0"` lives on the `<p:sld>` root
element of the slide part itself, not on `p:sldId` in `presentation.xml`.
This was established the way section 8's item 8 and item 5 both were -
empirically, per D10 - and `merge()` writes it by finding the `<p:sld ...>`
open tag in the copied slide's XML and setting or inserting the attribute
there.

**`dangling_refs(parts)`** is the check that closes the loop: it reads every
`.rels` file in a package and confirms each relationship target exists as a
part, and reads every OOXML part under `ppt/` and confirms every `r:id` it
uses resolves to a relationship. A dropped relationship that leaves a
dangling reference is otherwise invisible from Python - PowerPoint reports it
only as a repair prompt, and only if the repair prompt fires at all.

## 7. Page numbers

Printed page number is not file position: covers are unnumbered, hidden
slides consume no number, and the author reorders slides. `pagenums.py`
(`src/deck_kit/pagenums.py`) handles three incompatible marker flavours,
which `find_marker` classifies into four ranks - strongest first - and
returns the best-ranked candidate on the slide, REGARDLESS of which shape
happens to come first in the slide's z-order:

1. a real slide-number **placeholder**, recognised by
   `shape.placeholder_format.type` containing `SLIDE_NUMBER` - its `<a:fld
   type="slidenum">` lives on the layout it inherits from, not on the slide
   itself, once `add_slide(..., keep_placeholders=...)` clones a latent
   placeholder onto a slide;
2. an inherited text box **named for the locale** (`LOCALE_NAMES`, e.g.
   `"Slide Number"`, or the locale fragment `"mero de diapositiva"`);
3. any OTHER shape whose paragraph directly holds an `<a:fld
   type="slidenum">`, regardless of name;
4. a **plain literal** text box on a machine-built slide, recognised only by
   being short, numeric, and positioned at or below a caller-supplied floor
   (`min_top_emu`) - the weakest signal of the four, checked last.

Ranking, not z-order, is what makes this safe: a small numeric footnote near
the marker floor, added to the slide before the real marker, is exactly the
shape a naive "return on first hit while walking the shape tree" loop would
mistake for the marker - and `renumber` would then overwrite the footnote
with the page number while the real marker keeps its stale value.
`find_marker` instead classifies every shape once in a single walk and keeps
only the best rank seen; a shape earlier in z-order only wins a tie WITHIN
the same rank.

The **visible count**: `renumber(prs, style, skip=(1,))` walks slides in file
order, skips any with `show="0"` entirely (they are never visited and never
consume a number), and counts only the rest to derive each slide's printed
number. `skip` names positions in that **visible** count, not file position -
the two coincide only until a hidden slide sits before the cover, at which
point they name two different slides and no caller can say which one a bare
`skip=(1,)` was meant to protect.

**`renumber` self-heals when a flavour goes unrecognised, and that is a risk,
not just a convenience.** If `find_marker` fails to match any of the three
flavours on a visible slide, `renumber` does not fail - it concludes the
slide has no marker at all and calls `add_marker`, appending a new,
correctly-numbered box while leaving the unrecognised, now-stale marker in
place. The resulting numbers come out right regardless, because the new box
carries the correct number - they are right for the wrong reason, and an
assertion on the numbers alone stays green while a whole detection branch is
dead and the slide silently carries two page-number-shaped boxes. The only
signal that distinguishes "recognised and fixed" from "missed and re-added"
is `renumber`'s own return value: a list of `(position, visible,
"fixed"|"added")` tuples. A caller that cares whether marker recognition is
actually working - not just whether the final numbers look right - has to
assert that report, not only the numbers. This is not hypothetical: deleting
`LOCALE_NAMES` entirely left `examples/integration/version.py`'s numbers-only
assertion green until the report assertion was added specifically to catch
it (`docs/decisions.md`, Task 9).

`renumber` never receives colour, size or position as its own parameters: the
brand supplies all of it through `MarkerStyle` (x, y, w, h, size, color,
font), the same rule that keeps every colour and measurement default out of
the core library. `renumber` derives its own marker floor from `style.y`
rather than taking a second, independently-suppliable `min_top_emu` - a
caller that could pass a floor disagreeing with the style it also passed
would have `find_marker` searching a different band of the slide than the one
the marker it is about to write actually occupies.

## 8. Fonts

PowerPoint strips embedded fonts when a human genuinely saves the file
(catalogue item 1), so every generated version has to re-embed them - the
count of `ppt/fonts/*.fntdata` parts is what the fixed transplant restores.
The **splice point**: `fonts.transplant` inserts the donor's
`<p:embeddedFontLst>` block into `ppt/presentation.xml` immediately after
`<p:notesSz/>` (`_splice`), re-mints the block's relationship ids against the
destination's own `presentation.xml.rels` (`_add_font_rels`), copies the
`.fntdata` parts themselves, and adds a `fntdata` `Default` to
`[Content_Types].xml` if one is not already present (`_content_type_default`).
`expect_parts` is required and asserted exactly - not reported, which is a
declared deviation from spec section 3.2; see `docs/decisions.md`.

**Full-charset embedding**: the source convention this ports set
`SaveSubsetFonts = $false` on purpose - a subset renders only the characters
present on the day it was embedded, and boxes for anything a later editor
types that was not already there. `fonts.py` follows the same rule: it never
subsets, whether writing raw sfnt bytes for fixtures (`embed`) or splicing a
real donor's parts (`transplant`).

## 9. What can go wrong

See `references/06-gotchas.md` for the full failure catalogue, not repeated
here.
