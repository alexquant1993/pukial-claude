#!/usr/bin/env python3
"""Hero card generator for ASO scaffolds.

Phase 7 (hero slots only). Calls /v1/images/generations on gpt-image-2 to
paint a full-bleed scene, then Pillow handles all card framing
deterministically: polaroid-style white margin, rounded outer corners,
optional tag overlays (e.g. "Foto Principal", "GRATIS"), and drop shadow at
composite time. No chroma-key.

The AI never sees the scaffold, the headline, or the app UI.
"""
import argparse
import base64
import io
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from openai import OpenAI

PROMPT_WRAPPER = """A magazine-quality photoreal scene that fills the entire canvas edge-to-edge. The image must be ONE coherent photograph — no card frame, no white border, no rounded corners, no drop shadow, no UI chrome, no text overlays, no labels, no decorative elements, no collage. Just the photograph.

SCENE:
{scene_description}

Fill the full image with the scene. No whitespace, no padding, no margins, no vignette."""

CARD_INNER_MARGIN_DEFAULT = 25
CARD_CORNER_R_DEFAULT = 40
TAG_FONT_SIZE_DEFAULT = 26

SHADOW_OFFSET = (8, 14)
SHADOW_BLUR = 24
SHADOW_ALPHA = 110
SHADOW_PAD = 60


def build_prompt(scene_description: str) -> str:
    if not scene_description or not scene_description.strip():
        raise ValueError("creative_direction must be non-empty for hero slots")
    return PROMPT_WRAPPER.replace("{scene_description}", scene_description.strip())


def _round_up_to_mult(n: int, mult: int = 16) -> int:
    return ((n + mult - 1) // mult) * mult


def _parse_hex_color(s: str) -> tuple:
    s = s.lstrip("#")
    if len(s) == 6:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
    if len(s) == 8:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4, 6))
    raise ValueError(f"invalid hex color: {s!r}")


def _api_size_for_photo(photo_w: int, photo_h: int, min_side: int = 1024) -> tuple:
    """Scale the photo aspect up so the short side meets the API minimum."""
    short = min(photo_w, photo_h)
    if short >= min_side:
        return _round_up_to_mult(photo_w), _round_up_to_mult(photo_h)
    s = min_side / short
    return _round_up_to_mult(int(photo_w * s)), _round_up_to_mult(int(photo_h * s))


def _draw_tag(
    card: Image.Image,
    tag: dict,
    photo_box: tuple,
    default_font_path: str,
) -> None:
    """Draw one capsule-tag overlay on the photo area of the card."""
    text = tag["text"]
    position = tag.get("position", "bottom-center")
    bg_color = _parse_hex_color(tag.get("bg_color", "#000000B0"))
    text_color = _parse_hex_color(tag.get("text_color", "#FFFFFF"))
    font_size = int(tag.get("font_size", TAG_FONT_SIZE_DEFAULT))
    font_path = tag.get("font_path", default_font_path)
    edge_margin = int(tag.get("edge_margin", 18))
    pad_h = int(tag.get("padding_h", 16))
    pad_v = int(tag.get("padding_v", 9))
    cap_corner_r = int(tag.get("corner_r", 20))

    if font_path:
        font = ImageFont.truetype(font_path, font_size)
    else:
        # Fall back to a system sans-serif at the requested size — never
        # PIL's bitmap default, which ignores font_size and renders tiny.
        for sysf in ("/Library/Fonts/SF-Pro-Display-Bold.otf",
                     "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                     "/System/Library/Fonts/Helvetica.ttc",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            if os.path.exists(sysf):
                font = ImageFont.truetype(sysf, font_size); break
        else:
            font = ImageFont.load_default(size=font_size)
    dummy = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    cap_w = text_w + 2 * pad_h
    cap_h = text_h + 2 * pad_v

    px, py, pw, ph = photo_box
    if position == "bottom-center":
        cx = px + (pw - cap_w) // 2
        cy = py + ph - cap_h - edge_margin
    elif position == "bottom-left":
        cx, cy = px + edge_margin, py + ph - cap_h - edge_margin
    elif position == "bottom-right":
        cx, cy = px + pw - cap_w - edge_margin, py + ph - cap_h - edge_margin
    elif position == "top-left":
        cx, cy = px + edge_margin, py + edge_margin
    elif position == "top-right":
        cx, cy = px + pw - cap_w - edge_margin, py + edge_margin
    elif position == "top-center":
        cx = px + (pw - cap_w) // 2
        cy = py + edge_margin
    else:
        raise ValueError(f"unknown tag position: {position!r}")

    cap_layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
    cd = ImageDraw.Draw(cap_layer)
    cd.rounded_rectangle(
        [cx, cy, cx + cap_w, cy + cap_h],
        radius=cap_corner_r, fill=bg_color,
    )
    cd.text(
        (cx + pad_h - bbox[0], cy + pad_v - bbox[1]),
        text, font=font, fill=text_color,
    )
    card.alpha_composite(cap_layer)


def render_card(
    scene: Image.Image,
    card_w: int,
    card_h: int,
    inner_margin: int,
    corner_r: int,
    tags: list,
    tag_font_path: str,
) -> Image.Image:
    """Build the polaroid-style card: white surface, photo inset, optional
    tag overlays on the photo, rounded outer corners."""
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    photo_w = card_w - 2 * inner_margin
    photo_h = card_h - 2 * inner_margin
    scene_resized = scene.resize((photo_w, photo_h), Image.LANCZOS).convert("RGBA")
    inner_corner_r = max(corner_r - 14, 6)
    photo_mask = Image.new("L", (photo_w, photo_h), 0)
    ImageDraw.Draw(photo_mask).rounded_rectangle(
        [0, 0, photo_w, photo_h], radius=inner_corner_r, fill=255,
    )
    card.paste(scene_resized, (inner_margin, inner_margin), photo_mask)

    if tags:
        photo_box = (inner_margin, inner_margin, photo_w, photo_h)
        for tag in tags:
            _draw_tag(card, tag, photo_box, tag_font_path)

    outer_mask = Image.new("L", (card_w, card_h), 0)
    ImageDraw.Draw(outer_mask).rounded_rectangle(
        [0, 0, card_w, card_h], radius=corner_r, fill=255,
    )
    card.putalpha(outer_mask)
    return card


def composite_card_with_shadow(
    scaffold: Image.Image,
    card: Image.Image,
    position: tuple,
) -> Image.Image:
    """Composite card onto scaffold with a drop shadow shaped by card alpha."""
    cw, ch = card.size
    sw = cw + 2 * SHADOW_PAD
    sh = ch + 2 * SHADOW_PAD
    silhouette = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    tint = Image.new("RGBA", (cw, ch), (0, 0, 0, SHADOW_ALPHA))
    silhouette.paste(tint, (SHADOW_PAD, SHADOW_PAD), card.split()[3])
    shadow = silhouette.filter(ImageFilter.GaussianBlur(SHADOW_BLUR))

    px, py = position
    scaffold.alpha_composite(
        shadow,
        (px - SHADOW_PAD + SHADOW_OFFSET[0], py - SHADOW_PAD + SHADOW_OFFSET[1]),
    )
    scaffold.alpha_composite(card, (px, py))
    return scaffold


def _load_meta(scaffold_path: str) -> dict:
    meta_path = os.path.splitext(scaffold_path)[0] + ".meta.json"
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Sidecar not found: {meta_path}")
    with open(meta_path) as f:
        return json.load(f)


def enhance(
    scaffold_path: str,
    creative_direction: str,
    output_card: str,
    output_final: str,
    model: str = "gpt-image-2",
    quality: str = "high",
    inner_margin: int = CARD_INNER_MARGIN_DEFAULT,
    corner_r: int = CARD_CORNER_R_DEFAULT,
    tags: list = None,
    tag_font_path: str = None,
    output_scene: str = None,
    reuse_scene_from: str = None,
) -> None:
    meta = _load_meta(scaffold_path)
    if meta.get("panel_mode") != "hero" or not meta.get("breakout_zone"):
        raise ValueError(
            "enhance_card requires a hero-mode scaffold with breakout_zone"
        )
    zone_x, zone_y, card_w, card_h = meta["breakout_zone"]
    photo_w = card_w - 2 * inner_margin
    photo_h = card_h - 2 * inner_margin
    if photo_w <= 0 or photo_h <= 0:
        raise ValueError(
            f"inner_margin ({inner_margin}) too large for card "
            f"{card_w}x{card_h}"
        )

    if reuse_scene_from:
        raw = Image.open(reuse_scene_from)
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY env var not set. "
                "Export it before running enhance_card.py, or pass "
                "--reuse-scene-from to skip the AI call."
            )
        req_w, req_h = _api_size_for_photo(photo_w, photo_h)
        prompt = build_prompt(creative_direction)
        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=f"{req_w}x{req_h}",
            quality=quality,
            n=1,
        )
        raw = Image.open(io.BytesIO(base64.b64decode(response.data[0].b64_json)))

    # Always persist the raw scene so future variants (locale/platform
    # replications, tag-text changes) can re-render the framing without
    # another AI call. Default location is alongside output_card.
    scene_path = output_scene or os.path.join(
        os.path.dirname(output_card) or ".", "scene.png"
    )
    raw.convert("RGBA").save(scene_path, format="PNG")

    card = render_card(
        scene=raw,
        card_w=card_w,
        card_h=card_h,
        inner_margin=inner_margin,
        corner_r=corner_r,
        tags=tags or [],
        tag_font_path=tag_font_path,
    )
    card.save(output_card, format="PNG")

    scaffold = Image.open(scaffold_path).convert("RGBA")
    final = composite_card_with_shadow(scaffold, card, (zone_x, zone_y))
    final.convert("RGB").save(output_final, "PNG")


def main():
    p = argparse.ArgumentParser(
        description="Generate a hero card (AI scene + Pillow card framing) "
                    "and composite onto a scaffold."
    )
    p.add_argument("--scaffold", required=True)
    p.add_argument("--creative-direction", default="",
                   help="Scene-only description from aso_enhancements.md "
                        "(no card framing language). Required unless "
                        "--reuse-scene-from is given.")
    p.add_argument("--output-card", required=True)
    p.add_argument("--output-final", required=True)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    p.add_argument("--inner-margin", type=int, default=CARD_INNER_MARGIN_DEFAULT,
                   help="White polaroid-style margin around the photo (px).")
    p.add_argument("--corner-r", type=int, default=CARD_CORNER_R_DEFAULT,
                   help="Outer card corner radius (px).")
    p.add_argument("--tags", default="[]",
                   help="JSON list of tag overlays. Each tag: "
                        "{text, position, bg_color, text_color, font_size, ...}.")
    p.add_argument("--tag-font-path", default=None,
                   help="Default font path for tag overlays (TrueType).")
    p.add_argument("--output-scene", default=None,
                   help="Where to save the raw AI scene. Defaults to "
                        "<dir(output_card)>/scene.png.")
    p.add_argument("--reuse-scene-from", default=None,
                   help="Path to an existing scene.png to reuse. Skips the AI "
                        "call. Use this for replicating across locales / "
                        "platforms / tag-text variants without paying again.")
    p.add_argument("--creative-direction-required",
                   action="store_true", default=False,
                   help=argparse.SUPPRESS)
    args = p.parse_args()
    # creative_direction is only consumed when calling the AI; when
    # reusing a scene, accept an empty value so callers can pass --reuse-scene-from
    # without re-quoting the prompt.
    cd = args.creative_direction
    if args.reuse_scene_from and not cd:
        cd = "(reused scene)"
    enhance(
        scaffold_path=args.scaffold,
        creative_direction=cd,
        output_card=args.output_card,
        output_final=args.output_final,
        model=args.model,
        quality=args.quality,
        inner_margin=args.inner_margin,
        corner_r=args.corner_r,
        tags=json.loads(args.tags),
        tag_font_path=args.tag_font_path,
        output_scene=args.output_scene,
        reuse_scene_from=args.reuse_scene_from,
    )


if __name__ == "__main__":
    main()
