"""Speaker notes for the walkthrough. One Note per file position; the
teleprompter and the PPTX notes pane are both generated from this list."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from deck_kit.notes import Note

TITLE = "Walkthrough"

NOTES = [
    Note(1, "Cover", "Welcome. This is one deck through the whole pipeline.", minutes=1),
    Note(2, "The loop",
         "Four stages and one loop: spec, HTML draft, native build, integration.\n\n"
         "Three kinds of check, kept distinct: file, visual, content.\n\n"
         "> If asked: the HTML draft is disposable once the builder exists.",
         minutes=2),
]
