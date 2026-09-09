"""Build one navigable HTML deck out of a directory of slide drafts.

The deliverable when the spec's `**Output:**` line says `html`: the drafts
stop being disposable sketches and become the deck itself. One page,
`<out>/index.html`, carrying every `sNN-*.html` in the drafts directory in
order, each at the 1280x720 canvas the builder would have worked on, with
keyboard and click navigation, a slide counter, and a print stylesheet that
puts one slide on one landscape page - so "print to PDF" in the browser
yields a PDF deck with no PowerPoint anywhere in the chain.

Plain HTML, CSS and JS, no dependencies and **no external network
resources**: every stylesheet and image a draft links is rewritten to a path
relative to the output directory, and an absolute `http://`, `https://` or
protocol-relative URL is refused rather than embedded. A stage page that
fetches a font from a CDN is a deck that renders differently on the client's
machine and not at all on the aeroplane.

The drafts are embedded, not iframed. An iframe would keep each draft's own
document intact, which is tidier, but browsers print an iframe as one clipped
box or not at all - and printing is half of what this page is for.

  python scripts/build_html_deck.py --drafts examples/ai-horizon/drafts \
      --out out/ai-horizon/html --title "AI horizon" --expect-slides 10

`--expect-slides N` is exact and it is the same rule the rest of the QA loop
keeps: a glob that matched four drafts of ten builds a four-slide deck that
looks exactly like a successful build.

Pinned by tests/test_build_html_deck.py.

Run: uv run --offline --no-project --with python-pptx --with pillow \
       python scripts/build_html_deck.py --drafts DIR --out DIR
"""

import argparse
import html
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

# Elements that carry no closing tag. Re-emitting `</img>` is invalid HTML
# and browsers recover from it in different ways.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
# Attributes whose value is a URL this page has to resolve from a new place.
URL_ATTRS = {"src", "href", "poster", "data"}
REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.I)
SLIDE_NAME = re.compile(r"^s(\d+)", re.I)
CANVAS_W, CANVAS_H = 1280, 720


class DraftError(ValueError):
    """A draft this page cannot embed honestly."""


def slide_files(drafts):
    """The drafts in slide order: `sNN-*.html`, sorted by NN as a number.

    Sorted numerically rather than lexically because `s10-signposts.html`
    sorts before `s02-how-to-read.html` as a string, and a deck whose slides
    are in the wrong order is a deck nobody notices is wrong until the
    meeting. A repeated number is refused: two files claiming slide 3 have no
    defined order, and picking one silently is how a slide disappears.
    """
    drafts = Path(drafts)
    if not drafts.is_dir():
        raise DraftError("no such drafts directory: %s" % drafts)
    numbered = {}
    for path in sorted(drafts.glob("*.html")):
        match = SLIDE_NAME.match(path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in numbered:
            raise DraftError("two drafts claim slide %d: %s and %s"
                             % (number, numbered[number].name, path.name))
        numbered[number] = path
    if not numbered:
        raise DraftError("no sNN-*.html drafts in %s" % drafts)
    return [numbered[n] for n in sorted(numbered)]


class _Draft(HTMLParser):
    """Split one draft into its title, its stylesheets and its body.

    Every URL is rewritten as it passes: `href` and `src` are resolved
    against the draft's own directory and re-expressed relative to the
    output directory, because the stage page lives somewhere else and a
    draft's `../../../brands/relay/slide.css` means nothing from there.
    """

    def __init__(self, path, out_dir):
        super().__init__(convert_charrefs=True)
        self.path = Path(path)
        self.out_dir = Path(out_dir)
        self.title = None
        self.stylesheets = []          # rewritten hrefs, in document order
        self.styles = []               # inline <style> bodies, hoisted
        self._body = []
        self._in = None                # None | "title" | "style" | "body"
        self._depth = 0

    # -- URL handling ----------------------------------------------------

    def _rewrite(self, value):
        if not value or value.startswith("#") or value.startswith("data:"):
            return value
        if REMOTE.match(value):
            raise DraftError(
                "%s links %s. The stage page carries no external network "
                "resource: a deck that fetches a stylesheet or a font from "
                "the network renders differently on the client's machine "
                "and not at all offline. Commit the file and link it "
                "relatively." % (self.path.name, value))
        target = (self.path.parent / value).resolve()
        return Path(os.path.relpath(target, self.out_dir.resolve())).as_posix()

    def _attrs(self, attrs):
        out = []
        for name, value in attrs:
            if name.lower() in URL_ATTRS and value is not None:
                value = self._rewrite(value)
            out.append((name, value))
        return out

    # -- re-emission -----------------------------------------------------

    def _tag(self, name, attrs, closed=False):
        parts = [name]
        for attr, value in attrs:
            if value is None:
                parts.append(attr)
            else:
                parts.append('%s="%s"' % (attr, html.escape(value, quote=True)))
        return "<%s%s>" % (" ".join(parts), " /" if closed else "")

    def handle_starttag(self, tag, attrs):
        low = tag.lower()
        if low == "title":
            self._in = "title"
            self.title = ""
            return
        if low == "style":
            self._in = "style"
            self.styles.append("")
            return
        if low == "script":
            raise DraftError(
                "%s carries a <script>. A draft is markup and CSS; the stage "
                "page supplies the only script on the page." % self.path.name)
        if low == "body":
            self._in = "body"
            self._depth = 0
            return
        if low == "link":
            attrs = self._attrs(attrs)
            rel = {a: v for a, v in attrs}.get("rel", "").lower()
            href = {a: v for a, v in attrs}.get("href")
            if "stylesheet" in rel and href:
                self.stylesheets.append(href)
            return
        if self._in == "body":
            self._depth += 1
            self._body.append(self._tag(tag, self._attrs(attrs)))

    def handle_startendtag(self, tag, attrs):
        if self._in == "body":
            self._body.append(self._tag(tag, self._attrs(attrs), closed=True))

    def handle_endtag(self, tag):
        low = tag.lower()
        if low in ("title", "style"):
            self._in = None
            return
        if low == "body":
            self._in = None
            return
        if self._in == "body":
            self._depth -= 1
            if low not in VOID:
                self._body.append("</%s>" % tag)

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        elif self._in == "style":
            self.styles[-1] += data          # raw: CSS is not HTML-escaped
        elif self._in == "body":
            self._body.append(html.escape(data, quote=False))

    def handle_comment(self, data):
        # Dropped on purpose. A draft's comment is a note to its author -
        # "DISPOSABLE, the builder is the source of truth" - and the stage
        # page is the deliverable, not the workshop.
        pass

    @property
    def body(self):
        return "".join(self._body).strip()


def read_draft(path, out_dir):
    parser = _Draft(path, out_dir)
    parser.feed(Path(path).read_text(encoding="utf-8"))
    parser.close()
    if not parser.body:
        raise DraftError("%s has an empty <body>" % Path(path).name)
    return parser


STAGE_CSS = """
/* --- the stage: everything below is this page's own, and comes AFTER the
   drafts' stylesheets so that `html, body { width: 1280px; overflow: hidden }`
   - which every slide stylesheet sets, because a draft IS one slide - is
   overridden here rather than fought with !important. */
html, body { width: auto; height: auto; overflow: hidden; background: #0d0d0d }
body.dw-stage { display: flex; flex-direction: column; height: 100vh }
#dw-viewport {
  /* min-height: 0 is load-bearing. A transform does not change layout size,
     so the 720px-tall slide keeps a flex item at its full height unless the
     item is allowed to shrink below its content - and the bar then falls
     below the fold on any window shorter than 720px plus the bar. */
  flex: 1 1 auto; min-height: 0; position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.dw-slide {
  width: %(w)dpx; height: %(h)dpx; flex: 0 0 auto;
  transform: scale(var(--dw-scale, 1)); transform-origin: center center;
  box-shadow: 0 2px 24px rgba(0, 0, 0, .55); background: #fff;
}
.dw-slide[hidden] { display: none }
#dw-bar {
  flex: 0 0 auto; display: flex; align-items: center; gap: 14px;
  padding: 8px 14px; background: #141414; color: #d8d8d8;
  font: 500 12px/1.2 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  letter-spacing: .06em;
}
#dw-bar button {
  font: inherit; color: inherit; background: #242424; border: 1px solid #3a3a3a;
  border-radius: 2px; padding: 4px 12px; cursor: pointer;
}
#dw-bar button:hover { background: #303030 }
#dw-counter { min-width: 72px; text-align: center }
#dw-title { flex: 1 1 auto; overflow: hidden; text-overflow: ellipsis;
            white-space: nowrap; color: #8f8f8f; text-transform: uppercase }

/* --- print: one slide, one landscape page ---------------------------------
   13.333in x 7.5in is 1280x720 CSS px at 96dpi, which is also PowerPoint's
   16:9 page, so a slide fills the sheet at scale 1 with nothing to fit.
   Every slide is shown - the stage hides all but one on screen - and each
   breaks after itself, which is what makes "print to PDF" a deck. */
@page { size: 13.333in 7.5in; margin: 0 }
@media print {
  html, body { background: #fff; height: auto; overflow: visible }
  body.dw-stage { display: block; height: auto }
  #dw-bar { display: none }
  #dw-viewport { display: block; overflow: visible; min-height: 0 }
  .dw-slide, .dw-slide[hidden] {
    display: block; transform: none; box-shadow: none;
    break-after: page; page-break-after: always;
  }
  .dw-slide:last-of-type { break-after: auto; page-break-after: auto }
}
""" % {"w": CANVAS_W, "h": CANVAS_H}

STAGE_JS = """
(function () {
  var slides = [].slice.call(document.querySelectorAll('.dw-slide'));
  var counter = document.getElementById('dw-counter');
  var caption = document.getElementById('dw-title');
  var viewport = document.getElementById('dw-viewport');
  var at = 0;

  function show(i) {
    at = Math.max(0, Math.min(slides.length - 1, i));
    for (var j = 0; j < slides.length; j++) slides[j].hidden = (j !== at);
    counter.textContent = (at + 1) + ' / ' + slides.length;
    caption.textContent = slides[at].getAttribute('data-title') || '';
    if (window.history && history.replaceState) {
      history.replaceState(null, '', '#' + (at + 1));
    }
  }
  function fit() {
    var scale = Math.min(viewport.clientWidth / %(w)d, viewport.clientHeight / %(h)d);
    document.documentElement.style.setProperty('--dw-scale', scale);
  }
  function fromHash() {
    var n = parseInt((location.hash || '').replace('#', ''), 10);
    show(isNaN(n) ? 0 : n - 1);
  }

  document.getElementById('dw-prev').addEventListener('click', function (e) {
    e.stopPropagation(); show(at - 1);
  });
  document.getElementById('dw-next').addEventListener('click', function (e) {
    e.stopPropagation(); show(at + 1);
  });
  // Click navigation: the left third goes back, the rest goes on. A deck is
  // driven forwards, so the forward half is the bigger target.
  viewport.addEventListener('click', function (e) {
    show(e.clientX < viewport.clientWidth / 3 ? at - 1 : at + 1);
  });
  document.addEventListener('keydown', function (e) {
    var k = e.key;
    if (k === 'ArrowRight' || k === 'ArrowDown' || k === 'PageDown' || k === ' ') {
      show(at + 1);
    } else if (k === 'ArrowLeft' || k === 'ArrowUp' || k === 'PageUp') {
      show(at - 1);
    } else if (k === 'Home') { show(0);
    } else if (k === 'End') { show(slides.length - 1);
    } else { return; }
    e.preventDefault();
  });
  window.addEventListener('resize', fit);
  window.addEventListener('hashchange', fromHash);
  fit();
  fromHash();
})();
""" % {"w": CANVAS_W, "h": CANVAS_H}


def build_page(drafts, out_dir, title=None):
    """The whole `index.html` as one string."""
    out_dir = Path(out_dir)
    files = slide_files(drafts)
    parsed = [read_draft(path, out_dir) for path in files]

    sheets, seen = [], set()
    for draft in parsed:
        for href in draft.stylesheets:
            if href not in seen:
                seen.add(href)
                sheets.append(href)

    deck_title = title or Path(drafts).resolve().parent.name or "deck"
    out = ['<!doctype html>', '<html lang="en">', '<head>',
           '<meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<title>%s</title>' % html.escape(deck_title)]
    out += ['<link rel="stylesheet" href="%s">' % html.escape(h, quote=True)
            for h in sheets]
    for block in [d for draft in parsed for d in draft.styles]:
        out.append("<style>%s</style>" % block)
    out += ['<style>%s</style>' % STAGE_CSS, '</head>', '<body class="dw-stage">',
            '<div id="dw-viewport">']
    for index, (path, draft) in enumerate(zip(files, parsed)):
        name = draft.title or path.stem
        out.append('<section class="dw-slide" id="slide-%d" data-title="%s"%s>'
                   % (index + 1, html.escape(name.strip(), quote=True),
                      "" if index == 0 else " hidden"))
        out.append(draft.body)
        out.append('</section>')
    out += ['</div>',
            '<div id="dw-bar">',
            '<button id="dw-prev" type="button">&lsaquo; prev</button>',
            '<span id="dw-counter">1 / %d</span>' % len(files),
            '<button id="dw-next" type="button">next &rsaquo;</button>',
            '<span id="dw-title"></span>',
            '<span>&larr; &rarr; home end &middot; print for PDF</span>',
            '</div>',
            '<script>%s</script>' % STAGE_JS,
            '</body>', '</html>', '']
    return "\n".join(out)


def build(drafts, out_dir, title=None, expect_slides=None):
    out_dir = Path(out_dir)
    count = len(slide_files(drafts))
    if expect_slides is not None and count != expect_slides:
        raise DraftError("expected %d slide draft(s) in %s, found %d"
                         % (expect_slides, drafts, count))
    page = build_page(drafts, out_dir, title)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = out_dir / "index.html"
    index.write_text(page, encoding="utf-8")
    return index, count


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drafts", type=Path, required=True,
                    help="directory of sNN-*.html slide drafts")
    ap.add_argument("--out", type=Path, required=True,
                    help="directory to write index.html into")
    ap.add_argument("--title", default=None, help="the deck's title")
    ap.add_argument("--expect-slides", type=int, default=None,
                    help="exact number of drafts that must be found")
    args = ap.parse_args(argv)
    try:
        index, count = build(args.drafts, args.out, args.title, args.expect_slides)
    except (DraftError, OSError) as exc:
        print("FAIL: %s" % exc)
        return 1
    print("wrote %s (%d slide(s))" % (index, count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
