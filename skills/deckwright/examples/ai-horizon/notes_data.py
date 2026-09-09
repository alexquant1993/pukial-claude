"""Speaker notes for the AI horizon deck. One Note per file position; the
teleprompter and the PPTX notes pane are both generated from this list.

Sixteen minutes of speech, which is the spec's time budget."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from deck_kit.notes import Note

TITLE = "AI and humanity, 2026 to 2050 and beyond"

NOTES = [
    Note(1, "Cover",
         "This is an opinion deck. Every forecast on it is graded, and none of "
         "them is a measurement. The point is not to be right about dates; it "
         "is to give you one picture per horizon and tell you how much to "
         "trust it.",
         minutes=1),
    Note(2, "How to read this deck",
         "Four horizons: the next years to 2030, the 2030s, the 2040s, and "
         "everything after 2050. Four grades of confidence, and they fall as "
         "you move right.\n\n"
         "High means I would be surprised to be wrong. Medium means more "
         "likely than not. Low means this is one plausible path among "
         "several. Speculative means a direction, not a date.\n\n"
         "> If asked: the grades are the author's, not a survey. Treat them as "
         "a reading aid, not a probability.",
         minutes=2),
    Note(3, "The horizon map",
         "Seven milestones on one rail. The two on the left are already "
         "visible in pilots today; the one on the right is a guess about a "
         "society, not a technology.\n\n"
         "Notice the shape: the first four are about digital work and "
         "science, the last three are about bodies, ageing and what work is "
         "for. The technology arrives first; the social change follows by "
         "a decade.",
         minutes=2),
    Note(4, "The next years",
         "By 2030, agents do most routine digital office work. This is the "
         "one forecast I would bet on. The tools already exist; what changes "
         "is reliability on long tasks, and the willingness to let them run "
         "unsupervised.\n\n"
         "The signpost is an agent completing a week of work with no human "
         "check-in. When that is normal, the rest of this slide follows.\n\n"
         "> If asked: entry-level desk jobs shrink first because they are "
         "mostly the routine part. The senior job changes less, and later.",
         minutes=2),
    Note(5, "The next decade",
         "By 2040, AI runs the experiment and the human chooses the "
         "question. Automated labs close the loop from hypothesis to result. "
         "Whole business functions run on agents with a small human crew.\n\n"
         "This is the decade where countries diverge: some share the gains "
         "through universal services, some end up with a compute divide.\n\n"
         "> If asked: the wage split is the mechanism. Scarce judgement is "
         "paid more, routine cognition less, and that gap is political.",
         minutes=2),
    Note(6, "Toward 2050",
         "By 2050, most paid work is supervision, judgement and care. The "
         "2040s are when physical labour follows digital labour, because "
         "robots get cheap. At that point the question stops being jobs and "
         "becomes distribution.\n\n"
         "Confidence is low here. The technology path is plausible; the "
         "social response is genuinely open.",
         minutes=2),
    Note(7, "Beyond 2050",
         "Past 2050 the error bars cover every outcome, so this slide is a "
         "direction, not a date. Capability is not the question any more; "
         "who decides is.\n\n"
         "Concentration of control is the risk. Broad participation is the "
         "prize. Everything on this slide depends on which one wins.",
         minutes=1),
    Note(8, "Impact by domain",
         "The same forecasts, laid out by domain so you can read across a row. "
         "Work changes first, daily life last, and the grade falls as you "
         "move right in every row.\n\n"
         "> If asked: the matrix is deliberately one pill per cell. It is a "
         "map, not an inventory.",
         minutes=2),
    Note(9, "What has to be true",
         "Everything so far was a forecast. This slide is the bill for it: "
         "what each horizon actually depends on, and the state of each one "
         "today.\n\n"
         "Read down a column, not across. The near column is mostly amber - "
         "partial, with the gap named under each pill. The far columns are "
         "mostly red, and red is the honest colour for a capability nobody "
         "has yet.\n\n"
         "The bottom row is the three enablers that sit under every column: "
         "energy, chips, and public trust. Lose any one and every date on "
         "this deck moves right.\n\n"
         "> If asked: the empty cell is not an oversight. By the 2040s the "
         "compute question is answered, and that row asks for nothing new.",
         minutes=1),
    Note(10, "What would change this",
         "Three things bring every date forward: cheaper compute, agents that "
         "are reliable for weeks, and robots at consumer prices. Three things "
         "push them back: energy and chips as the bottleneck, one serious "
         "safety failure, and regulation that freezes key sectors.\n\n"
         "The dates will be wrong. The direction is the forecast.",
         minutes=1),
]
