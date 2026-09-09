# SPEC - AI and humanity, 2026 to 2050 and beyond (Relay)

**Date:** 2026-09-09
**Objective:** after this deck the audience holds one forecast per horizon, knows how much confidence each one deserves, and knows which signposts would change it.
**Audience and time budget:** a general leadership audience, no technical background assumed; sixteen minutes of speech.
**Status:** approved for build
**Design system:** relay
**HTML draft:** yes, drafts in `examples/ai-horizon/drafts/` (all ten)
**Notes:** both
**Output:** both

Ten slides in `brands/relay`, drafted in HTML first and then ported. Every
slide is route B and every slide has a draft; the layout rulings are section
7's ledger, `examples/ai-horizon/ledger.md`. Section 5's `Exact string` table
is the closed copy: those thirteen strings appear verbatim on the slides and
`lint.toml` fails the build if one does not.

---

## 1. Content constraints

Non-negotiable editorial rules. Each one is checked by
`examples/ai-horizon/lint.toml`.

- Every forecast carries a confidence grade, and the grade is one of four: High, Medium, Low, Speculative.
- No vendor, product or laboratory names reach the deck: the forecast is about the technology, not about who ships it.
- No internal tracking codes (`D1-01` style) reach the deck.
- Every content slide carries the copyright line and exactly one section kicker.
- Anything spoken only if asked lives in the notes, never on a slide.
- Every figure is a judgement, and the deck says so on the slide that explains how to read it.

Two constraints the design system adds, and both are checked by eye against
the exported PNGs rather than by lint, because no lint can see a colour:

- One orange element per slide. Relay's readme says so outright, and the
  kicker is therefore muted on every white slide.
- No gradients, and no rounded surface. Radius is 0 for a card and 2 for a
  control.

## 2. Sources

| Artifact | Use |
|---|---|
| the author's own forecast, 2026-09-08 | every forecast, milestone and signpost; this is an opinion deck, not a research deck |
| `references/01-spec-stage.md`, the verdict table | the four verdicts; every claim here is graded **Judgement**, none is **Exact** |
| `brands/relay_design_system/` | the design system: `tokens/*.css`, `guidelines/`, the fourteen reference slides in `ui_kits/slides/`, and the rules in its `readme.md` |

## 3. Verified facts

Use EXACTLY these strings; do not invent figures. Every row is checked
verbatim against the built deck by `scripts/lint_deck.py`'s `exact` check
(whitespace-normalised). Append new rows below the line; never edit a
verified row in place.

There are no measured figures in this deck. The rows below are the
headline forecasts and the reading rules, pinned so that a retyped slide
cannot drift from the spec.

| Fact | Exact string | Source |
|---|---|---|
| Reading rule | `Every figure on these slides is a judgement, not a measurement.` | section 1, last rule |
| Grade: High | `High: would be surprised if wrong` | section 1, first rule |
| Grade: Medium | `Medium: more likely than not` | section 1, first rule |
| Grade: Low | `Low: one plausible path among several` | section 1, first rule |
| Grade: Speculative | `Speculative: a direction, not a date` | section 1, first rule |
| Headline, next years | `By 2030, AI agents do most routine digital office work.` | author's forecast |
| Headline, next decade | `By 2040, AI runs the experiment and the human chooses the question.` | author's forecast |
| Headline, toward 2050 | `By 2050, most paid work is supervision, judgement and care.` | author's forecast |
| Headline, beyond | `Beyond 2050, the open question is not capability but who decides.` | author's forecast |
| Closing rule | `The dates will be wrong. The direction is the forecast.` | author's forecast |
| Readiness claim | `Every horizon rests on capabilities that are not in place yet.` | author's forecast |
| Readiness legend: absent | `RED absent today` | section 5, S09 |
| Readiness legend: partial | `AMBER partial today` | section 5, S09 |

## 4. Slide table

| # | Slide | Route | Source | Relay slide type |
|---|---|---|---|---|
| S01 | Cover | B | section 5 | 01 Title, inverse ground |
| S02 | How to read this deck | B | section 5 and the four grades above | 06 Three columns, widened to four |
| S03 | The horizon map | B | section 5; seven milestones on one rail | 09 Timeline |
| S04 | The next years, 2026 to 2030 | B | section 5, headline row 6 | 04 Big number + 06 Three columns |
| S05 | The next decade, the 2030s | B | section 5, headline row 7 | as S04 |
| S06 | Toward 2050, the 2040s | B | section 5, headline row 8 | as S04 |
| S07 | Beyond 2050 | B | section 5, headline row 9 | as S04 |
| S08 | Impact by domain and horizon | B | section 5; the matrix | 11 Table |
| S09 | What has to be true by when | B | section 5; the readiness matrix | 11 Table, as a capability matrix |
| S10 | What would change these forecasts | B | section 5; closing rule | 07 Comparison |

Routes: **A** = clone an approved slide and retext it in place (design
intact). **B** = design in HTML on the 1280x720 canvas, then port natively
with `deck_kit`. **C** = extract a slide from an existing deck and reframe it.

**Ten drafts for ten slides**, in `examples/ai-horizon/drafts/`, and
they were authored **before** the builder - which is the pipeline's order.
S05, S06 and S07 share S04's layout and were generated from one template;
they still exist as their own files, because the four horizon slides are
what the composed strip is asserted against and a reviewer needs to see all
four.

S09 was the last one added, and it is the only slide in the deck drawn with
`deck_kit.components` rather than with the builder's own `Draw` vocabulary:
the capability matrix, the measured pill flow, the status pills and the
legend used to live in a second example directory, `examples/capability-matrix`,
which existed for no other reason. Folding it in put those pieces on a slide
that belongs to this argument; section 7's ledger has the ruling.

## 5. Content per slide

The closed copy. Every string below is what reaches the slide; the thirteen
in the `Exact string` table are checked verbatim by `lint.toml`, and the 35%
rule governs any replacement.

### S01 Cover

Inverse (black) ground. Title: "AI and humanity, 2026 to 2050 and beyond",
set as two lines, breaking after the comma. Subtitle: "Forecasts by horizon,
with the confidence each one deserves". A third line: "An opinion deck. Every
forecast is graded; none is a measurement." No kicker, no copyright line, no
page number; the mono line at the top is the brand tagline, which is
furniture rather than content, and the footer carries the wordmark alone.

### S02 How to read this deck

Kicker: "01. HOW TO READ THIS". Title: "Four horizons, four grades of
confidence". Sub: "The further right on the timeline, the wider the error
bars. The grade on each slide says how wide."

Four cells in a butt-joined grid, one per horizon, each with a mono year
label, the horizon name, a hairline, three one-line forecasts and a
confidence tag at the foot:

- **2026 to 2030, The next years** - "Agents take over routine digital work"; "AI in every classroom and clinic"; "Rules lag behind use". Tag: High.
- **The 2030s, The next decade** - "Whole functions run on agents"; "Automated science closes the loop"; "Countries diverge on sharing the gains". Tag: Medium.
- **The 2040s, Toward 2050** - "Robots make physical labour cheap"; "Ageing itself is treated"; "Income begins to decouple from work". Tag: Low.
- **After 2050, Beyond** - "Work optional for most people"; "Science outruns institutions"; "Who decides becomes the question". Tag: Speculative.

A legend of the four grades, exact strings from section 3, two per row. A
closing line over a 3 px rule: the reading rule, exact string from section 3.

The one orange element is the first horizon's year label.

### S03 The horizon map

Kicker: "02. THE HORIZON MAP". Title: "Seven milestones on one rail". Sub:
"Where each forecast lands, and how sure this deck is about it."

Two registers. Above: four horizon segments whose widths are proportional to
their year span, then a year rail with ticks at 2026, 2030, 2035, 2040, 2045,
2050 and "beyond", carrying the seven milestone markers at their true year,
numbered. Below: the same seven milestones as seven equal columns under a
3 px rule, in reading order, each with its number, year, label and grade:

1. 2027 - "Agents handle most routine office tasks" - High
2. 2029 - "AI-designed drugs in late-stage trials" - High
3. 2032 - "A tutor for every connected child" - Medium
4. 2036 - "Automated labs run the whole loop" - Medium
5. 2040 - "Self-driving is the default in cities" - Low
6. 2045 - "Ageing treated as a condition" - Low
7. 2050 - "Work optional in wealthy societies" - Speculative

Closing line: "Reading rule: the further right, the wider the error bars."

The one orange element is milestone 1, the nearest one.

### S04 The next years, 2026 to 2030

Kicker: "03. THE NEXT YEARS". Title: "2026 to 2030: the agent decade
begins". Sub: "What is already in motion, and will be ordinary by 2030."
Confidence tag: High.

Under a 3 px rule: the oversized numeral "2030" in signal orange, the
headline beside it in display type, and the confidence tag at the right edge.
The headline is the exact string "By 2030, AI agents do most routine digital
office work."

Three domain cells in a butt-joined grid, each with a Lucide icon:
- **Work** - "Agents draft, file, reconcile and schedule. The job that remains is checking, deciding and being accountable."
- **Science and health** - "AI reads every paper and every scan. Diagnosis support becomes standard and reaches clinics without specialists."
- **Society** - "Cheap persuasion at scale. Elections, scams and schooling all feel it before the law catches up."

"What you will notice" tags: "A personal agent on every phone", "Entry-level
desk jobs shrink", "Cheaper software, more of it", "AI in every classroom",
"Deepfakes as a daily nuisance".

Signpost line over a hairline: "Signpost: an agent completes a week-long task
without a human check-in."

### S05 The next decade, the 2030s

Kicker: "04. THE NEXT DECADE". Title: "The 2030s: the loop closes". Sub:
"When agents stop assisting work and start running it." Tag: Medium.
Numeral: 2040.

Headline: "By 2040, AI runs the experiment and the human chooses the
question."

- **Work** - "Whole functions run on agents with a small human crew. Wages split: scarce judgement is paid more, routine cognition less."
- **Science and health** - "Automated labs close the loop from hypothesis to result. Drug pipelines shorten from a decade to a few years."
- **Society** - "Countries diverge on whether AI gains are shared. Universal services in some places, a compute divide in others."

Tags: "Self-driving in most cities", "Tutors for every child", "Robots in
warehouses and farms", "Materials and energy designed by AI", "New rules for
liability".

Signpost line: "Signpost: a discovery credited to an AI system wins a major
prize."

### S06 Toward 2050, the 2040s

Kicker: "05. APPROACHING MIDCENTURY". Title: "The 2040s: physical labour
follows digital". Sub: "When robots get cheap, the question stops being
jobs and becomes distribution." Tag: Low. Numeral: 2050.

Headline: "By 2050, most paid work is supervision, judgement and care."

- **Work** - "Physical labour follows digital labour as robots get cheap. Paid work concentrates in care, craft and deciding what to build."
- **Science and health** - "Life expectancy moves again as ageing itself is treated. Diagnosis is continuous rather than an appointment."
- **Society** - "The question shifts from jobs to distribution. Some societies decouple income from work; others do not."

Tags: "Working week under thirty hours", "Robots in most homes",
"Personalised medicine as the default", "Cities rebuilt around autonomy".

Signpost line: "Signpost: a country funds a basic income mainly from
AI-driven output."

### S07 Beyond 2050

Kicker: "06. BEYOND MIDCENTURY". Title: "After 2050: capability is not the
question". Sub: "Past this line the error bars cover every outcome. What
remains is a direction." Tag: Speculative. Numeral: 2050 with a "+" unit
beside it.

Headline: "Beyond 2050, the open question is not capability but who
decides."

- **Work** - "Work becomes optional for most people in wealthy societies. Status and meaning come from what people choose to do."
- **Science and health** - "Research runs faster than institutions can absorb it. Fusion, engineered biology and off-world industry are on the table."
- **Society** - "Governance of AI is the central political question. Concentration of control is the risk; broad participation is the prize."

Tags: "Human and AI collaboration as the norm", "Aligned systems as public
infrastructure", "New forms of collective decision".

Signpost line: "Signpost: none. Past 2050 the error bars cover every
outcome."

### S08 Impact by domain and horizon

Kicker: "07. IMPACT BY DOMAIN". Title: "Four domains across four horizons".
Sub: "The same forecasts, placed by domain, each carrying its grade."

A table in Relay's own idiom: mono uppercase column headers over a 1.5 px
rule, then hairline-bottomed rows, no zebra striping and no card wrappers.
Rows Work, Science and health, Society and governance, Daily life, each with
its icon; columns 2026 to 2030, The 2030s, The 2040s, After 2050. One
forecast per cell with its grade under it as a mono label:

| | 2026 to 2030 | 2030s | 2040s | 2050+ |
|---|---|---|---|---|
| Work | Agents do routine desk work | Functions run on agents | Robots do physical labour | Work becomes optional |
| Science and health | AI reads every scan | Automated labs | Ageing treated | Science outruns institutions |
| Society and governance | Persuasion at scale | Countries diverge | Income decouples from work | Who decides |
| Daily life | An agent on every phone | Tutors and self-driving | Robots at home | Meaning over employment |

A legend of the four grades at the foot. The one orange element is the
nearest horizon's column header.

### S09 What has to be true by when

Kicker: "08. WHAT HAS TO BE TRUE". Title: "What has to be true by when".
Sub, the exact string from section 3: "Every horizon rests on capabilities
that are not in place yet."

A capability matrix: four rows down the left, the first three horizons
across the top, and in each cell the capabilities that horizon depends on,
drawn as pills coloured by the state of each one **today**. This is the
deck's only slide in the kit's own component vocabulary - the matrix frame,
the measured pill flow, the status pills and the legend - and section 7's
ledger says why.

Column heads, with a mono sublabel each:

| Column | Sublabel |
|---|---|
| 2026 to 2030 | THE NEXT YEARS. HIGH |
| The 2030s | THE NEXT DECADE. MEDIUM |
| The 2040s | TOWARD 2050. LOW |

Rows, each with a Lucide icon, the label set over two lines: "Data &
compute" (zap), "Models & agents" (terminal), "Institutions & law" (users),
"Skills & people" (activity).

Three states, and the pill's fill says which:

- **plain** - in place today, no sublabel;
- **amber** - partial today, carrying a "today: ..." sublabel;
- **red** - absent today, no sublabel.

The cells, by row:

**Data & compute.** 2026 to 2030: "Frontier compute at scale" (plain);
"Clean enterprise data" (amber, "today: mostly in lakes"). The 2030s:
"Compute priced like power" (amber, "today: scarce and lumpy"). The 2040s:
empty - by then the compute question is answered and the row asks for
nothing new. Drawn as the dashed cell with a centred dash.

**Models & agents.** 2026 to 2030: "Tool use in every workflow" (plain);
"Agents reliable for a day" (amber, "today: minutes at a time"). The 2030s:
"Agents reliable for a week" (red); "Automated experiment loops" (amber,
"today: single steps"). The 2040s: "Robots cheap enough to rent" (red).

**Institutions & law.** 2026 to 2030: "Audit trails on decisions" (amber,
"today: pilots only"); "Liability rules for agents" (red). The 2030s: "Rules
agreed across borders" (red). The 2040s: "Income decoupled from work" (red).

**Skills & people.** 2026 to 2030: "Supervision as a taught skill" (amber,
"today: taught nowhere"); "Public trust in agents" (amber, "today:
falling"). The 2030s: "Retraining at national scale" (red). The 2040s: "Care
and craft paid properly" (red).

Under the matrix, one bottom row. On the left a strip of transversal
enablers - a label, "Enablers", then three plain pills: "Energy", "Chips and
fabs", "Public trust". They sit outside the time axis because they are not a
capability of any one horizon. On the right, a legend box reading the two
states that are not plain, in the exact strings from section 3: "RED absent
today" and "AMBER partial today".

The one orange element is the "Enablers" label. The matrix frame - the
column heads, the rule under them, the row labels - is drawn in ink, and the
amber and red pills are Relay's semantic STATUS colours, which its readme
keeps separate from signal.

### S10 What would change these forecasts

Kicker: "09. WHAT WOULD CHANGE THIS". Title: "Signposts that move the
dates". Sub: "Three things that would bring every horizon forward, and three
that would push them back."

Two columns under two 3 px rules: the left one black, the right one orange,
which is Relay's own comparison idiom and the one orange element here.

Left column, "Would bring the dates forward":
- **Compute keeps getting cheaper** - "Each halving of cost brings the next horizon a year or two closer."
- **Agents prove reliable on long tasks** - "Weeks of unsupervised work is the threshold for whole functions."
- **Robots reach consumer prices** - "The 2040s arrive in the 2030s the year a capable home robot costs what a car does."

Right column, "Would push the dates back":
- **Energy and chips become the bottleneck** - "Demand outruns grids and fabs and the curve flattens for a decade."
- **A serious safety failure** - "One well-publicised harm freezes deployment in health, finance and government."
- **Regulation freezes key sectors** - "Liability rules that nobody can meet keep agents out of exactly the work they would change most."

Closing line over a 3 px rule: the exact closing rule, "The dates will be
wrong. The direction is the forecast."

## 6. Technical pipeline

PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/make_template.py --brand relay --out out/ai-horizon/template.pptx
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/inspect_template.py --brand relay out/ai-horizon/template.pptx
powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/ai-horizon/template.pptx
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python examples/ai-horizon/build_ai_horizon.py --template out/ai-horizon/template.pptx --out out/ai-horizon/deck.pptx --notes both --teleprompter out/ai-horizon/teleprompter.html
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/assert_native.py out/ai-horizon/deck.pptx --autoshapes AUTOSHAPES --min-pictures PICTURES --max-pictures PICTURES --no-dangling
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/lint_deck.py --deck out/ai-horizon/deck.pptx --rules examples/ai-horizon/lint.toml --expect-checks 8
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/dump_text.py --deck out/ai-horizon/deck.pptx --out out/ai-horizon/text.txt --expect-paragraphs PARAGRAPHS
powershell -NoProfile -File scripts/check_pptx.ps1 -Path out/ai-horizon/deck.pptx
powershell -NoProfile -File scripts/export_png.ps1 -Path out/ai-horizon/deck.pptx -Out out/ai-horizon/png -Expect 10
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py band --png-dir out/ai-horizon/png --box 0,836,1600,900 --expect 10 --out out/ai-horizon/qa/band.png
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py ink --image out/ai-horizon/qa/band.png --rows 10 --gutter 200 --inked 1,2,3,4,5,6,7,8,9,10
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py zoom --png-dir out/ai-horizon/png --slides 1,2,3,4,5,6,7,8,9,10 --box 1400,840,1600,900 --scale 2 --out out/ai-horizon/qa/page.png
PYTHONIOENCODING=utf-8 uv run --offline --no-project --with python-pptx --with pillow python scripts/compose_qa.py ink --image out/ai-horizon/qa/page.png --rows 10 --gutter 130 --blank 1 --inked 2,3,4,5,6,7,8,9,10

`examples/ai-horizon/run.ps1` runs the same lines in that order, with
the shape counts and the paragraph count filled in from the builder's
docstring and its `check()`.

## 7. Open flags and rulings

See `examples/ai-horizon/ledger.md`.
