"""The embedded-font transplant.

PowerPoint strips embedded fonts when a human saves the file, so every
generated version has to put them back. The transplant is not a file copy: the
<p:embeddedFontLst> block has to be spliced into ppt/presentation.xml
immediately after <p:notesSz/>, its relationship ids re-minted against the
destination's presentation.xml.rels, and [Content_Types].xml given a Default
for the fntdata extension.

Fonts are embedded whole, never subset. The engagement set
SaveSubsetFonts = $false deliberately: a subset renders the characters the
deck had on the day it was embedded, and boxes for everything a later editor
types.
"""

import re

from .merge import read_package, refuse_in_place, write_package

FONT_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/font"


def font_parts(parts):
    return sorted(n for n in parts
                  if n.startswith("ppt/fonts/") and n.endswith(".fntdata"))


def _add_font_rels(parts, targets):
    """Append one relationship per font target; return old rid -> new rid."""
    rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    used = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels)]
    nxt = (max(used) + 1) if used else 1
    mapping, added = {}, []
    for old_rid in sorted(targets, key=lambda r: int(r[3:])):
        new_rid = "rId%d" % nxt
        nxt += 1
        mapping[old_rid] = new_rid
        added.append('<Relationship Id="%s" Type="%s" Target="%s"/>'
                     % (new_rid, FONT_RT, targets[old_rid]))
    parts["ppt/_rels/presentation.xml.rels"] = rels.replace(
        "</Relationships>", "".join(added) + "</Relationships>").encode("utf-8")
    return mapping


def _splice(parts, block):
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    if "<p:embeddedFontLst" in pres:
        raise AssertionError("destination already declares embedded fonts")
    m = re.search(r"<p:notesSz[^>]*/>", pres)
    if not m:
        raise AssertionError("no <p:notesSz/> in presentation.xml; the splice point is undefined")
    parts["ppt/presentation.xml"] = (pres[:m.end()] + block + pres[m.end():]).encode("utf-8")


def _content_type_default(parts):
    ct = parts["[Content_Types].xml"].decode("utf-8")
    if 'Extension="fntdata"' not in ct:
        ct = ct.replace("<Override", '<Default Extension="fntdata" '
                        'ContentType="application/x-fontdata"/><Override', 1)
    parts["[Content_Types].xml"] = ct.encode("utf-8")


def transplant(dest_path, src_path, out_path, expect_parts):
    """Copy the donor's embedded-font setup into a destination that has none.

    `expect_parts` is required and asserted exactly. A donor that lost a face
    between versions must stop the build: a deck missing its bold renders in a
    substitute face on every machine that lacks it, which is the failure
    embedding exists to prevent, and nothing downstream would notice.
    """
    refuse_in_place(out_path, (dest_path, src_path))
    src = read_package(src_path)
    out = read_package(dest_path)
    if font_parts(out):
        raise AssertionError("destination already has embedded fonts")

    src_pres = src["ppt/presentation.xml"].decode("utf-8")
    found = re.search(r"<p:embeddedFontLst>.*?</p:embeddedFontLst>", src_pres, re.S)
    if not found:
        raise AssertionError("donor declares no embeddedFontLst")
    block = found.group(0)

    src_rels = src["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    targets = {m.group(1): m.group(2) for m in re.finditer(
        r'<Relationship Id="(rId\d+)" Type="[^"]*/font" Target="([^"]+)"/>', src_rels)}
    if len(targets) != expect_parts:
        raise AssertionError(
            "donor has %d font relationships, expected exactly %d"
            % (len(targets), expect_parts))

    for target in targets.values():
        part = "ppt/" + target.lstrip("/")
        if part in out:
            raise AssertionError("font part name collision: %s" % part)
        out[part] = src[part]

    ridmap = _add_font_rels(out, targets)
    block = re.sub(r'r:id="(rId\d+)"', lambda m: 'r:id="%s"' % ridmap[m.group(1)], block)
    _splice(out, block)
    _content_type_default(out)
    write_package(out_path, out)
    return len(targets)


def embed(dest_path, out_path, faces):
    """Write .fntdata parts from TTF files and declare them. FIXTURES ONLY.

    A real .fntdata part is an EOT stream, not a font file: PowerPoint's own
    parts carry an EOT header whose FontDataSize is smaller than the part and
    whose `LP` magic sits at offset 34. This writes the sfnt bytes raw, which
    is enough for `transplant` to copy and count them and enough for every
    unit test in this module.

    It is now MEASURED, not merely unknown, to be NOT enough for PowerPoint:
    a raw-sfnt donor built by this function survives `transplant` and the
    doubled COM open with no repair, but a real PowerPoint save discards it
    completely - 2 parts become 0, with `<p:embeddedFontLst>`, both
    relationships and the `fntdata` content-type Default all removed. A
    genuine EOT-wrapped donor behaves differently under the same save: parts
    shrink (21 -> 16 on one measured file) and every survivor is rewritten,
    which is PowerPoint parsing what it recognises and re-embedding locally
    installed faces, not passing the bytes through. Raw sfnt is not repaired
    or ignored, it is discarded outright, because PowerPoint never parses it
    as a font in the first place. See docs/decisions.md, "catalogue item 1".

    The Phase 2 gate uses this route deliberately anyway, in place of
    `scripts/embed_fonts.ps1` (the COM donor route, which sets
    `EmbedTrueTypeFonts` - absent from this machine's PowerPoint automation
    surface entirely, DISP_E_UNKNOWNNAME). On a machine where COM embedding
    is unavailable, this function is the only way to exercise `transplant`'s
    plumbing (splice position, rId re-minting, content-type Default) at all;
    it is not, and was never meant to be, a substitute for what a real
    embedded-font donor is.

    `faces` is a sequence of (typeface, regular_path, bold_path or None).
    """
    refuse_in_place(out_path, dest_path)
    out = read_package(dest_path)
    if font_parts(out):
        raise AssertionError("destination already has embedded fonts")

    entries, targets, n = [], {}, 0
    for typeface, regular, bold in faces:
        variants = []
        for tag, path in (("regular", regular), ("bold", bold)):
            if path is None:
                continue
            n += 1
            out["ppt/fonts/font%d.fntdata" % n] = open(str(path), "rb").read()
            rid = "rId%d" % n          # donor-local; _add_font_rels re-mints
            targets[rid] = "fonts/font%d.fntdata" % n
            variants.append('<p:%s r:id="%s"/>' % (tag, rid))
        entries.append('<p:embeddedFont><p:font typeface="%s" pitchFamily="34" '
                       'charset="0"/>%s</p:embeddedFont>' % (typeface, "".join(variants)))

    ridmap = _add_font_rels(out, targets)
    block = "<p:embeddedFontLst>%s</p:embeddedFontLst>" % "".join(entries)
    block = re.sub(r'r:id="(rId\d+)"', lambda m: 'r:id="%s"' % ridmap[m.group(1)], block)
    _splice(out, block)
    _content_type_default(out)
    write_package(out_path, out)
    return n
