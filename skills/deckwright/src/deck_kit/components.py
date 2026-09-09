"""The component vocabulary: pills, the capability matrix, measured flow.

Everything here measures before it places. Nothing relies on PowerPoint to
fit text, and every overflow reaches the build's warning register rather
than being clipped silently.
"""

from dataclasses import dataclass
from typing import Optional

from pptx.enum.text import MSO_ANCHOR, PP_ALIGN

from .primitives import add_para, icon as place_icon, rrect, rule, settext, textbox
from .xmlfill import alpha_fill, dashed


@dataclass
class PillStyle:
    fill: object
    line: object
    lw: float
    fg: object
    sub_fg: object = None
    bar: object = None          # colour of an underline bar, or None


@dataclass
class Pill:
    title: str
    style: PillStyle
    sub: Optional[str] = None


def pill_w(metrics, pill, pt, sub_pt, pad=20):
    w = metrics.width(pill.title, pt, bold=True) + pad
    if pill.sub:
        w = max(w, metrics.width(pill.sub, sub_pt, bold=False) + pad)
    return w


def draw_pill(slide, x, y, w, h, pill, font, pt, sub_pt, rad=7):
    """One pill. `rad` is the corner radius in pixels.

    A radius is a design-system value, so it is a parameter rather than the
    literal 7 it used to be: a brand whose scale says "sharp by default"
    passes its own control radius and gets a control, not a lozenge. Same
    argument as `matrix_frame`'s `accent` and `icon_key`.
    tests/test_components.py::test_draw_pill_takes_the_brands_control_radius.
    """
    st = pill.style
    sp = rrect(slide, x, y, w, h, fill=st.fill, line=st.line, lw=st.lw, rad=rad)
    settext(sp, [(pill.title, True)], pt, st.fg, font,
            PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE, ls=1.0)
    if pill.sub:
        add_para(sp.text_frame, [(pill.sub, False)], sub_pt,
                 st.sub_fg or st.fg, font, PP_ALIGN.CENTER, ls=1.05)
    if st.bar is not None:
        rule(slide, x + 10, y + h - 6, w - 20, 3, st.bar)
    return sp


def _layout_rows(pills, metrics, pt, sub_pt, avail, gap, pill_h, pill_sub_h):
    sizes = []
    for p in pills:
        pw = pill_w(metrics, p, pt, sub_pt)
        ph = pill_sub_h if p.sub else pill_h
        if p.style.bar is not None:
            ph += 4
        sizes.append((pw, ph))
    rows, cur, curw = [], [], 0.0
    for i, (pw, _) in enumerate(sizes):
        if cur and curw + gap + pw > avail:
            rows.append(cur)
            cur, curw = [], 0.0
        cur.append(i)
        curw += (gap if curw else 0) + pw
    if cur:
        rows.append(cur)
    row_h = [max(sizes[i][1] for i in rw) for rw in rows]
    return sizes, rows, row_h


def flow_pills(slide, cell, pills, metrics, font, warn,
               ladder=(9.5, 9.0, 8.5), sub_pt=9.5, gap=6, rgap=3,
               pill_h=23, pill_sub_h=32, align="center", label=None, rad=7):
    """Wrap pills inside a cell, shrinking through `ladder` if needed.

    Warns when even the last rung does not fit - HEIGHT if the rows do not
    stack inside the cell, OVERFLOW if a pill is wider than the cell - and
    the build then exits non-zero rather than shipping a clipped cell. The
    ladder is the only autoshrink in the kit, and it is explicit.

    `label` names the cell in warnings; without it two cells overflowing by
    the same amount collapse into one entry, since the register is a set.
    `rad` is handed to every pill it draws, so a brand's radius reaches the
    flow without the caller drawing the pills itself.

    Pill heights are pixel constants, so a lower rung narrows a pill without
    shortening it: the ladder reduces height only by fitting more per row.
    """
    x, y, w, h = cell
    avail = w - 12
    if not pills:
        return
    pt = ladder[-1]
    for pt in ladder:
        sizes, rows, row_h = _layout_rows(pills, metrics, pt, sub_pt, avail,
                                          gap, pill_h, pill_sub_h)
        total = sum(row_h) + rgap * (len(rows) - 1)
        widest = max(pw for pw, _ in sizes)
        # Both dimensions decide the rung. Stepping down on height alone
        # leaves a pill drawn at a size that does not fit horizontally when
        # the next rung would have fitted - a build failure with the fix one
        # rung away.
        if total <= h - 6 and widest <= avail:
            break
    if total > h - 6:
        warn.add("HEIGHT", "cell %s %.0f > %.0f tall: %s"
                 % (label or "", total, h - 6, pills[0].title))
    # Height is not the only way to overflow. A single pill wider than the
    # cell wraps onto a row of its own and still fits vertically, so the
    # height check alone reports a clean build while the text runs past the
    # cell edge. Width is checked separately, and it is the check the source
    # repository did not have.
    for pill, (pw, _) in zip(pills, sizes):
        if pw > avail:
            warn.add("OVERFLOW", "pill %.0f > %.0f wide: %s" % (pw, avail, pill.title))
    cy = y + (h - total) / 2.0
    for rw, rh in zip(rows, row_h):
        rww = sum(sizes[i][0] for i in rw) + gap * (len(rw) - 1)
        cx = x + 6 if align == "left" else x + (w - rww) / 2.0
        for i in rw:
            pw, ph = sizes[i]
            draw_pill(slide, cx, cy + (rh - ph) / 2.0, pw, ph, pills[i], font, pt,
                      sub_pt, rad=rad)
            cx += pw + gap
        cy += rh + rgap


def matrix_frame(slide, top, row_h, cols, rows, geom, style, font, icon_dir,
                 hdr_h=32, rgap=8, empty=(), accent=None, icon_key=None,
                 cell_rad=8):
    """Column headers, row labels and cell backgrounds.

    cols  [(header, sublabel), ...]
    rows  [(icon_name, "Line one\\nLine two"), ...]
    geom  dict with left, col_w, col_x, row_label_w
    style the brand's style module

    `accent` is the ink the frame - column headers, the rule under them, the
    row labels - is drawn in, and defaults to the brand's `BLUE` accent role.
    A brand whose accent is a scarce signal colour passes a quieter one:
    `brands/relay` allows one orange element per view, and a frame drawn in it
    spends that budget on furniture. `icon_key` is the colour key in the row
    icons' filenames (`ic_<name>_<key>.png`) and comes from the brand's
    `ICON_KEY`; it used to be the literal string "blue" here, which was one
    brand's value hardcoded in the kit.

    `cell_rad` is the cell's corner radius, for the same reason: a brand
    whose surfaces are square passes 0 and gets rectangles.
    tests/test_components.py::test_matrix_frame_takes_the_brands_surface_radius.

    Returns {(row, col): (x, y, w, h)}.
    """
    col_w, col_x = geom["col_w"], geom["col_x"]
    left, label_w = geom["left"], geom["row_label_w"]
    accent = style.BLUE if accent is None else accent
    icon_key = style.ICON_KEY if icon_key is None else icon_key

    for i, (head, sub) in enumerate(cols):
        x = col_x[i]
        textbox(slide, x + 2, top - 2, col_w, 16, [(head, True)],
                style.T_COL_HEAD, accent, font, upper=True, ls=1.0)
        textbox(slide, x + 2, top + 16, col_w, 12, sub, style.T_COL_SUB,
                style.GREY, font, ls=1.0)
        rule(slide, x, top + hdr_h - 2, col_w, 2, accent)

    cells, y0 = {}, top + hdr_h + rgap
    for r, (icon_name, label) in enumerate(rows):
        y = y0 + r * (row_h + rgap)
        place_icon(slide, icon_dir, icon_name, icon_key, left + 44,
                   y + row_h / 2.0 - 9, 18)
        # Any number of lines, not exactly two: unpacking a fixed pair turns
        # a one-line label into a ValueError from inside the frame.
        lines = label.split("\n")
        t = textbox(slide, left + 58, y, label_w - 64, row_h, [(lines[0], True)],
                    style.T_ROW_LABEL, accent, font, PP_ALIGN.RIGHT,
                    MSO_ANCHOR.MIDDLE, ls=1.15, upper=True)
        for extra in lines[1:]:
            add_para(t.text_frame, [(extra, True)], style.T_ROW_LABEL,
                     accent, font, PP_ALIGN.RIGHT, ls=1.15, upper=True)
        for c in range(len(cols)):
            x = col_x[c]
            box = rrect(slide, x, y, col_w, row_h, fill=style.WHITE,
                        line=style.CELL_BD, lw=0.75, rad=cell_rad)
            if (r, c) in empty:
                box.fill.background()
                dashed(box, style.CELL_BD, 0.9)
                textbox(slide, x, y, col_w, row_h, "-", style.T_BODY, style.MUTED,
                        font, PP_ALIGN.CENTER, MSO_ANCHOR.MIDDLE)
            else:
                alpha_fill(box, style.WHITE, 42)
            cells[(r, c)] = (x, y, col_w, row_h)
    return cells


def explain_box(slide, cell, title, desc, style, font, metrics, warn, max_lines=5):
    x, y, w, h = cell
    rrect(slide, x + 6, y + 6, w - 12, h - 12, fill=style.WHITE,
          line=style.BLUE, lw=1.2, rad=8)
    box = textbox(slide, x + 16, y + 8, w - 32, h - 16, [(title, True)],
                  style.T_CAPTION, style.NAVY, font, anchor=MSO_ANCHOR.MIDDLE, ls=1.15)
    add_para(box.text_frame, [(desc, False)], style.T_CARD_DESC, style.GREY,
             font, PP_ALIGN.LEFT, ls=1.2, space_before=1)
    n = (metrics.lines([(title, True)], style.T_CAPTION, w - 32)
         + metrics.lines([(desc, False)], style.T_CARD_DESC, w - 32))
    if n > max_lines:
        warn.add("WRAP", "explain_box wraps to %d lines: %s" % (n, title))


def loop_line(slide, y, runs, geom, style, font, metrics, warn, h=24):
    """A transversal single-line note.

    Wrap is off, so overrun text simply runs out of the box with nothing to
    stop it. That makes the measurement mandatory rather than optional: this
    was the one component in the module that placed without measuring.
    """
    left, w = geom["left"], geom["width"]
    lb = rrect(slide, left, y, w, h, fill=style.WHITE, line=style.LINE, lw=0.75, rad=6)
    alpha_fill(lb, style.WHITE, 72)
    avail = w - 28
    flat = "".join(r[0] for r in runs)
    if metrics.width(flat, style.T_LOOP, bold=True) > avail:
        warn.add("OVERFLOW", "loop_line wider than %.0f: %s" % (avail, flat[:60]))
    textbox(slide, left + 16, y, avail, h, runs, style.T_LOOP, style.GREY,
            font, anchor=MSO_ANCHOR.MIDDLE, ls=1.0, wrap=False)
