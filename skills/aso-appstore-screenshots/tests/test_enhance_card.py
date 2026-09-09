"""Tests for enhance_card.py — scene prompt + polaroid framing + composite."""
import enhance_card


def test_build_prompt_includes_scene_description():
    prompt = enhance_card.build_prompt(
        "A red sofa in a sunlit Madrid apartment.",
    )
    assert "sunlit Madrid apartment" in prompt
    # Scene-only prompt: insists on no card framing in the AI output.
    assert "no card frame" in prompt
    assert "SCENE:" in prompt


def test_build_prompt_short_enough():
    prompt = enhance_card.build_prompt("Some scene description here.")
    # Wrapper is ~80 words. Total under 200.
    assert len(prompt.split()) < 200


def test_build_prompt_rejects_empty():
    import pytest
    with pytest.raises(ValueError):
        enhance_card.build_prompt("")


def test_api_size_scales_up_to_min_pixel_budget():
    # Photo area 760x560 (slot 1 dims) — short side 560 < 1024, must scale up.
    w, h = enhance_card._api_size_for_photo(760, 560, min_side=1024)
    assert min(w, h) >= 1024
    assert w % 16 == 0 and h % 16 == 0
    # Aspect preserved (within rounding).
    assert abs((w / h) - (760 / 560)) < 0.05


def test_api_size_passthrough_when_already_big():
    w, h = enhance_card._api_size_for_photo(2048, 1536, min_side=1024)
    assert w >= 2048 and h >= 1536
    assert w % 16 == 0 and h % 16 == 0


def test_render_card_produces_polaroid_with_white_margin(tmp_path):
    from PIL import Image
    # A red scene, 1024x768.
    scene = Image.new("RGBA", (1024, 768), (255, 0, 0, 255))
    card = enhance_card.render_card(
        scene=scene,
        card_w=760, card_h=560,
        inner_margin=25,
        corner_r=40,
        tags=[],
        tag_font_path=None,
    )
    assert card.size == (760, 560)
    # Corner pixel (outside the rounded mask) is fully transparent.
    assert card.getpixel((0, 0))[3] == 0
    # White margin pixel (just inside the rounded corner, between outer edge
    # and inset photo): the white surface shows through.
    assert card.getpixel((10, 250))[:3] == (255, 255, 255)
    # Photo center pixel is the scene's red.
    assert card.getpixel((380, 280))[:3] == (255, 0, 0)


def test_render_card_draws_tag_overlay():
    """Tag capsule paints over the scene at the requested position."""
    from PIL import Image
    scene = Image.new("RGBA", (1024, 768), (255, 0, 0, 255))
    card = enhance_card.render_card(
        scene=scene,
        card_w=760, card_h=560,
        inner_margin=25,
        corner_r=40,
        tags=[{
            "text": "X",
            "position": "bottom-center",
            "bg_color": "#000000FF",
            "text_color": "#FFFFFF",
            "font_size": 20,
        }],
        tag_font_path=None,  # use Pillow default; works without an installed font
    )
    # Tag sits at bottom-center of the photo region. Sample a few pixels just
    # above the photo's bottom edge near the center — must not be pure red.
    cx, cy = 760 // 2, 560 - 50
    px = card.getpixel((cx, cy))
    assert px[:3] != (255, 0, 0), "tag overlay did not paint over the scene"


def test_composite_card_with_shadow(tmp_path):
    from PIL import Image
    scaffold = Image.new("RGBA", (1320, 2868), (255, 215, 240, 255))
    card = Image.new("RGBA", (760, 560), (255, 0, 0, 255))
    final = enhance_card.composite_card_with_shadow(
        scaffold=scaffold,
        card=card,
        position=(60, 1020),
    )
    # Card paints at (60, 1020). Sample inside the card.
    px = final.getpixel((60 + 100, 1020 + 100))
    assert px[:3] == (255, 0, 0)


def test_enhance_with_reuse_scene_skips_api_call(monkeypatch, tmp_path):
    """--reuse-scene-from path must bypass the OpenAI call entirely."""
    import json
    from PIL import Image

    # Saved scene from a previous run.
    scene_path = tmp_path / "scene.png"
    Image.new("RGBA", (1024, 768), (0, 200, 100, 255)).save(scene_path)

    # Build a hero-mode scaffold + sidecar.
    scaffold_path = tmp_path / "scaffold.png"
    Image.new("RGBA", (1320, 2868), (255, 215, 240, 255)).convert("RGB").save(scaffold_path)
    sidecar_path = tmp_path / "scaffold.meta.json"
    json.dump(
        {
            "device": "iphone-6.9",
            "canvas": [1320, 2868],
            "panel_mode": "hero",
            "breakout_zone": [60, 1020, 760, 560],
            "screen_rect": [185, 787, 948, 2055],
            "background": {"style": "plain", "colors": ["#FFD7F0"]},
        },
        open(sidecar_path, "w"),
    )

    # OpenAI client must NOT be touched when reusing a scene.
    def boom(*args, **kwargs):
        raise AssertionError(
            "OpenAI client constructed during --reuse-scene-from; should not happen"
        )
    monkeypatch.setattr(enhance_card, "OpenAI", boom)

    enhance_card.enhance(
        scaffold_path=str(scaffold_path),
        creative_direction="",
        output_card=str(tmp_path / "card.png"),
        output_final=str(tmp_path / "final.png"),
        reuse_scene_from=str(scene_path),
        tag_font_path=None,
        tags=[{"text": "Foto Principal", "position": "bottom-center",
               "bg_color": "#000000B0", "font_size": 20}],
    )
    # Card produced, final produced, scene preserved.
    assert (tmp_path / "card.png").exists()
    assert (tmp_path / "final.png").exists()
    assert scene_path.exists()
