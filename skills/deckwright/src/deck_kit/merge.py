"""OOXML slide transplant: copy whole slides - with their layout, master,
theme and media - from a source .pptx into a destination .pptx at chosen
positions.

Why it works:
 - Relationship ids are *part-local*, so copied parts keep their original
   rIds. Only the relationship *targets* are rewritten to the new part names.
   The only rIds minted fresh are the ones added to
   ppt/_rels/presentation.xml.rels.
 - Every copied part gets a brand-new, non-colliding name in the destination.
 - Presentation-scope ids that must be unique - p:sldId/@id, p:sldMasterId/@id,
   p:sldLayoutId/@id - are re-minted above the destination's current maximum.
   The p:sldLayoutId values live inside the copied *master* parts.
 - Parts deliberately not copied: notesSlide, bound to the source's
   notesMaster, and modern comments, bound to the source's authors.xml. Their
   relationships are stripped and the matching <p:ext> comment anchor is
   removed from the slide XML, so no dangling r:id remains.
 - The hidden flag is show="0" on the <p:sld> ROOT element, not on p:sldId in
   presentation.xml. Verified empirically against PowerPoint COM.

This module never opens a Presentation: python-pptx has no model for a foreign
slide's master, and a half-modelled package is harder to reason about than the
zip.

    from deck_kit.merge import merge
    merge(dest, src, [(1, 4, False), (2, 7, True)], out)
    # (source slide index 1-based, target position 1-based in the FINAL deck,
    #  hidden?)
"""

import os
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PNS = "http://schemas.openxmlformats.org/presentationml/2006/main"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

DEFAULT_CT = {
    "png": "image/png", "jpeg": "image/jpeg", "jpg": "image/jpeg",
    "gif": "image/gif", "emf": "image/x-emf", "wmf": "image/x-wmf",
    "wdp": "image/vnd.ms-photo", "svg": "image/svg+xml", "tiff": "image/tiff",
    "bin": "application/vnd.openxmlformats-officedocument.oleObject",
    "mp4": "video/mp4", "m4a": "audio/mp4", "wav": "audio/wav",
    "fntdata": "application/x-fontdata",
}
DROP_TYPES = {"notesSlide", "comments", "commentAuthors"}
COMMENT_EXT_URI = "{6950BFC3-D8DA-4A85-94F7-54DA5524770B}"


def read_package(path):
    with zipfile.ZipFile(str(path)) as z:
        return {n: z.read(n) for n in z.namelist()}


def refuse_in_place(out_path, in_path):
    """Refuse when the resolved output path equals a resolved input path.

    Every writer in this module and its siblings (`fonts.transplant`,
    `fonts.embed`, `scripts/dump_text.py`) can be asked, directly or by a
    careless caller, to overwrite the very file it reads. Shared here so
    each site fails the same way rather than four writers each getting one
    chance to forget it - `scripts/dump_text.py` had exactly that gap, with
    `references/04` instructing a reader to run it against the author's live
    deck.
    """
    out_resolved = Path(out_path).resolve()
    for candidate in in_path if isinstance(in_path, (list, tuple)) else (in_path,):
        if candidate is None:
            continue
        if out_resolved == Path(candidate).resolve():
            raise ValueError(
                "refusing to overwrite the input file %s - the author's file "
                "is frequently open in PowerPoint and locked, and writing "
                "over it would destroy their manual edits with no undo"
                % candidate)


def write_package(path, parts):
    """[Content_Types].xml goes first - every writer in the source repository
    honours this invariant.

    Atomic: written to a `.tmp` sibling and moved into place with
    `os.replace`, so an interrupt mid-write leaves the original file (or
    nothing) rather than a truncated pptx - opening the target with mode
    "w" truncates it before a single byte of the new content is written.
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", parts["[Content_Types].xml"])
        for name, data in parts.items():
            if name != "[Content_Types].xml":
                z.writestr(name, data)
    os.replace(str(tmp), str(path))


def slide_order(parts):
    """Slide part names in presentation order."""
    pres = ET.fromstring(parts["ppt/presentation.xml"])
    rels = ET.fromstring(parts["ppt/_rels/presentation.xml.rels"])
    rmap = {r.get("Id"): r.get("Target") for r in rels}
    return [_resolve("ppt/presentation.xml", rmap[s.get("{%s}id" % RT)])
            for s in pres.find("{%s}sldIdLst" % PNS)]


RID_ATTR = re.compile(r'r:(?:id|embed|link|pict|dm|lo|qs|cs)="(rId\d+)"')


def _rels_owner(rels_name):
    """The part a .rels file describes.

    The package-root rels is named `_rels/.rels`, with nothing before the
    `_rels/` segment, so a regex requiring a preceding directory silently
    fails to match it and leaves `owner` as the rels path itself - which
    resolves every root relationship against `_rels/` and reports four
    missing parts on a perfectly valid deck. rpartition handles both shapes.
    """
    head, _, tail = rels_name.rpartition("_rels/")
    return head + tail[:-len(".rels")]


def _resolve_from(base_part, target):
    """_resolve, but tolerant of an empty base - the package root.

    `_resolve` derives a directory by rsplitting the base part on "/", so a
    base with no "/" at all (e.g. "x") returns itself, not "". Only a base
    that already ends in "/" - i.e. an empty final segment - yields the empty
    directory _resolve needs to resolve `target` straight against the root.
    """
    if not base_part:
        return _resolve("/", target)
    return _resolve(base_part, target)


def dangling_refs(parts):
    """Every reference in the package that does not resolve.

    Two directions, because they fail differently: a relationship whose target
    part is absent, and an r:id used in a part's XML with no matching
    relationship. PowerPoint reports both as 'needs repair' and neither is
    visible from Python until you look.
    """
    problems = []
    for name, data in parts.items():
        if not name.endswith(".rels"):
            continue
        owner = _rels_owner(name)
        for rel in ET.fromstring(data):
            if rel.get("TargetMode") == "External":
                continue
            target = _resolve_from(owner, rel.get("Target"))
            if target not in parts:
                problems.append("%s -> %s (missing part)" % (name, target))
    for name, data in parts.items():
        if not (name.endswith(".xml") and name.startswith("ppt/")):
            continue
        rels = parts.get(_relspath(name))
        known = {r.get("Id") for r in ET.fromstring(rels)} if rels else set()
        for rid in sorted(set(RID_ATTR.findall(data.decode("utf-8")))):
            if rid not in known:
                problems.append("%s uses %s with no relationship" % (name, rid))
    return sorted(problems)


def _relspath(part):
    d, f = part.rsplit("/", 1)
    return "%s/_rels/%s.rels" % (d, f)


def _resolve(base_part, target):
    """Resolve a relationship target relative to the part's directory."""
    d = base_part.rsplit("/", 1)[0]
    parts = d.split("/") + target.split("/")
    out = []
    for p in parts:
        if p == "..":
            out.pop()
        elif p not in ("", "."):
            out.append(p)
    return "/".join(out)


def _relto(from_part, to_part):
    a = from_part.split("/")[:-1]
    b = to_part.split("/")
    i = 0
    while i < len(a) and i < len(b) - 1 and a[i] == b[i]:
        i += 1
    return "/".join([".."] * (len(a) - i) + b[i:])


def _maxnum(names, pattern):
    n = [int(m.group(1)) for m in (re.match(pattern, x) for x in names) if m]
    return max(n) if n else 0


def merge(dest_path, src_path, specs, out_path, verbose=True):
    refuse_in_place(out_path, (dest_path, src_path))
    dest = read_package(dest_path)
    src = read_package(src_path)

    dnames = set(dest)
    base = lambda p: p.rsplit("/", 1)[-1]

    counters = {
        "ppt/slides/slide%d.xml": _maxnum([base(x) for x in dnames], r"slide(\d+)\.xml$"),
        "ppt/slideLayouts/slideLayout%d.xml": _maxnum([base(x) for x in dnames], r"slideLayout(\d+)\.xml$"),
        "ppt/slideMasters/slideMaster%d.xml": _maxnum([base(x) for x in dnames], r"slideMaster(\d+)\.xml$"),
        "ppt/theme/theme%d.xml": _maxnum([base(x) for x in dnames], r"theme(\d+)\.xml$"),
        "ppt/tags/tag%d.xml": _maxnum([base(x) for x in dnames], r"tag(\d+)\.xml$"),
        "ppt/embeddings/oleObject%d.bin": _maxnum([base(x) for x in dnames], r"oleObject(\d+)\.bin$"),
    }
    media_n = [0]

    def newname(part):
        """Mint a fresh, free destination part name for a source part."""
        for tmpl in counters:
            head, tail = tmpl.split("%d")
            if part.startswith(head) and part.endswith(tail):
                while True:
                    counters[tmpl] += 1
                    cand = tmpl % counters[tmpl]
                    if cand not in dnames:
                        return cand
        if part.startswith("ppt/media/"):
            ext = part.rsplit(".", 1)[-1]
            while True:
                media_n[0] += 1
                cand = "ppt/media/mrg%d.%s" % (media_n[0], ext)
                if cand not in dnames:
                    return cand
        # generic fallback: keep folder, prefix the filename
        d, f = part.rsplit("/", 1)
        i = 0
        while True:
            i += 1
            cand = "%s/mrg%d_%s" % (d, i, f)
            if cand not in dnames:
                return cand

    mapping = {}          # src part -> dest part
    to_write = []         # src parts to copy, in discovery order

    def collect(part):
        """Transitively collect `part` and everything it depends on."""
        if part in mapping:
            return mapping[part]
        nn = newname(part)
        mapping[part] = nn
        dnames.add(nn)
        to_write.append(part)
        rp = _relspath(part)
        if rp in src:
            for rel in ET.fromstring(src[rp]):
                if rel.get("TargetMode") == "External":
                    continue
                rtype = rel.get("Type").rsplit("/", 1)[-1]
                if rtype in DROP_TYPES:
                    continue
                collect(_resolve(part, rel.get("Target")))
        return nn

    # --- source slide part names in presentation order -----------------------
    src_order = slide_order(src)
    dest_count = len(slide_order(dest))
    final_count = dest_count + len(specs)

    positions = []
    for src_idx, pos, hidden in specs:
        if not (1 <= src_idx <= len(src_order)):
            raise ValueError(
                "spec src_idx=%r is out of range - the donor has %d slide(s), "
                "so src_idx must be between 1 and %d"
                % (src_idx, len(src_order), len(src_order)))
        if not (1 <= pos <= final_count):
            raise ValueError(
                "spec pos=%r is out of range - the final deck has %d "
                "slide(s), so pos must be between 1 and %d"
                % (pos, final_count, final_count))
        positions.append(pos)
    dupes = {p for p in positions if positions.count(p) > 1}
    if dupes:
        raise ValueError(
            "specs name duplicate target position(s) %s - each spec must "
            "land at its own position, or one silently displaces another"
            % sorted(dupes))

    plan = []
    for src_idx, pos, hidden in specs:
        sp = src_order[src_idx - 1]
        plan.append((sp, collect(sp), pos, hidden))

    # --- write the copied parts, rewriting rels targets ----------------------
    out = dict(dest)
    for sp in to_write:
        dp = mapping[sp]
        data = src[sp]
        if sp.startswith("ppt/slides/slide"):
            data = _clean_slide(data)
        out[dp] = data
        rp = _relspath(sp)
        if rp not in src:
            continue
        root = ET.fromstring(src[rp])
        for rel in list(root):
            if rel.get("TargetMode") == "External":
                continue
            rtype = rel.get("Type").rsplit("/", 1)[-1]
            tgt = _resolve(sp, rel.get("Target"))
            if rtype in DROP_TYPES or tgt not in mapping:
                root.remove(rel)
                continue
            rel.set("Target", _relto(dp, mapping[tgt]))
        out[_relspath(dp)] = _ser(root, PKG_REL, "Relationships")

    # --- re-mint presentation-scope IDs on copied masters --------------------
    pres_xml = dest["ppt/presentation.xml"].decode("utf-8")
    used_master_ids = [int(x) for x in re.findall(r'<p:sldMasterId id="(\d+)"', pres_xml)]
    for p in dest:
        if re.match(r"ppt/slideMasters/slideMaster\d+\.xml$", p):
            used_master_ids += [int(x) for x in
                                re.findall(r'<p:sldLayoutId id="(\d+)"', dest[p].decode("utf-8"))]
    nid = [max(used_master_ids + [2147483648]) + 1]

    new_masters = [mapping[p] for p in to_write
                   if re.match(r"ppt/slideMasters/slideMaster\d+\.xml$", p)]
    for mp in new_masters:
        x = out[mp].decode("utf-8")

        def bump(m):
            nid[0] += 1
            return '<p:sldLayoutId id="%d"' % nid[0]
        x = re.sub(r'<p:sldLayoutId id="\d+"', bump, x)
        out[mp] = x.encode("utf-8")

    # --- [Content_Types].xml -------------------------------------------------
    ET.register_namespace("", CT_NS)
    ct = ET.fromstring(dest["[Content_Types].xml"])
    have_def = {e.get("Extension").lower() for e in ct if e.tag.endswith("Default")}
    have_ovr = {e.get("PartName") for e in ct if e.tag.endswith("Override")}
    src_ct = ET.fromstring(src["[Content_Types].xml"])
    src_ovr = {e.get("PartName"): e.get("ContentType")
               for e in src_ct if e.tag.endswith("Override")}
    src_def = {e.get("Extension").lower(): e.get("ContentType")
               for e in src_ct if e.tag.endswith("Default")}
    for sp in to_write:
        dp = mapping[sp]
        pn = "/" + dp
        ctype = src_ovr.get("/" + sp)
        if ctype is None:
            ext = dp.rsplit(".", 1)[-1].lower()
            if ext not in have_def:
                c = src_def.get(ext) or DEFAULT_CT.get(ext)
                if c is None:
                    raise RuntimeError("unknown content type for .%s (%s)" % (ext, sp))
                e = ET.SubElement(ct, "{%s}Default" % CT_NS)
                e.set("Extension", ext)
                e.set("ContentType", c)
                have_def.add(ext)
            continue
        if pn not in have_ovr:
            e = ET.SubElement(ct, "{%s}Override" % CT_NS)
            e.set("PartName", pn)
            e.set("ContentType", ctype)
            have_ovr.add(pn)
    out["[Content_Types].xml"] = _ser(ct, CT_NS, "Types")

    # --- presentation.xml.rels: new rIds for slides + masters ----------------
    prels = ET.fromstring(dest["ppt/_rels/presentation.xml.rels"])
    used = {r.get("Id") for r in prels}
    rn = [max([int(m.group(1)) for m in
               (re.match(r"rId(\d+)$", i) for i in used) if m] or [0])]

    def add_rel(target_part, rtype):
        rn[0] += 1
        rid = "rId%d" % rn[0]
        while rid in used:
            rn[0] += 1
            rid = "rId%d" % rn[0]
        used.add(rid)
        e = ET.SubElement(prels, "{%s}Relationship" % PKG_REL)
        e.set("Id", rid)
        e.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/" + rtype)
        e.set("Target", _relto("ppt/presentation.xml", target_part))
        return rid

    master_rids = [(mp, add_rel(mp, "slideMaster")) for mp in new_masters]
    slide_rids = [(sp, dp, pos, hidden, add_rel(dp, "slide")) for sp, dp, pos, hidden in plan]
    out["ppt/_rels/presentation.xml.rels"] = _ser(prels, PKG_REL, "Relationships")

    # --- presentation.xml: sldMasterIdLst + sldIdLst --------------------------
    px = pres_xml
    if master_rids:
        chunk = "".join('<p:sldMasterId id="%d" r:id="%s"/>' % (nid[0] + 1 + i, rid)
                        for i, (_, rid) in enumerate(master_rids))
        nid[0] += len(master_rids)
        px = px.replace("</p:sldMasterIdLst>", chunk + "</p:sldMasterIdLst>")

    m = re.search(r"<p:sldIdLst>(.*?)</p:sldIdLst>", px, re.S)
    items = re.findall(r"<p:sldId [^>]*/>", m.group(1))
    max_sid = max([int(x) for x in re.findall(r'<p:sldId id="(\d+)"', m.group(1))] or [255])
    for i, (_sp, _dp, pos, _h, rid) in enumerate(sorted(slide_rids, key=lambda t: t[2])):
        max_sid += 1
        items.insert(pos - 1, '<p:sldId id="%d" r:id="%s"/>' % (max_sid, rid))
    px = px[:m.start()] + "<p:sldIdLst>" + "".join(items) + "</p:sldIdLst>" + px[m.end():]
    out["ppt/presentation.xml"] = px.encode("utf-8")

    # --- hidden flag: show="0" on the <p:sld> root ---------------------------
    for _sp, dp, _pos, hidden in plan:
        if not hidden:
            continue
        x = out[dp].decode("utf-8")
        mm = re.search(r"<p:sld(\s[^>]*?)?>", x)
        tag = mm.group(0)
        if 'show="' in tag:
            newtag = re.sub(r'show="[^"]*"', 'show="0"', tag)
        else:
            newtag = tag[:-1].rstrip() + ' show="0">'
        out[dp] = (x[:mm.start()] + newtag + x[mm.end():]).encode("utf-8")

    # --- repack ----------------------------------------------------------
    write_package(out_path, out)

    if verbose:
        for sp, dp, pos, hidden in plan:
            print("  %-24s -> %-26s pos %-3d %s" % (sp, dp, pos, "HIDDEN" if hidden else ""))
        print("  masters copied:", new_masters)
        print("  parts copied:", len(to_write))
    return {sp: dp for sp, dp, _p, _h in plan}


def _clean_slide(data):
    """Strip the modern-comment anchor <p:ext> (its target part is not copied)."""
    x = data.decode("utf-8")
    pat = r'<p:ext uri="%s">.*?</p:ext>' % re.escape(COMMENT_EXT_URI)
    x2 = re.sub(pat, "", x, flags=re.S)
    x2 = x2.replace("<p:extLst></p:extLst>", "")
    return x2.encode("utf-8")


def _ser(root, ns, tagname):
    ET.register_namespace("", ns)
    body = ET.tostring(root, encoding="unicode")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
            + body).encode("utf-8")
