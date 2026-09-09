"""End-to-end tests for compose.py orchestration."""
import json
import os
from PIL import Image
import compose


def test_compose_clean_slot_writes_scaffold_and_sidecar(
    sample_ui_path, tmp_output, assets_dir
):
    sidecar = tmp_output.replace(".png", ".meta.json")
    compose.compose(
        device="iphone-6.9",
        bg_style="plain",
        bg_colors=["#FFD7F0"],
        verb="TEST",
        desc="DESCRIPTOR LINE",
        text_color="#BC004B",
        screenshot_path=sample_ui_path,
        frame_path=os.path.join(assets_dir, "iphone-6.9-frame.png"),
        output_path=tmp_output,
    )
    out = Image.open(tmp_output)
    assert out.size == (1320, 2868)
    meta = json.load(open(sidecar))
    assert meta["device"] == "iphone-6.9"
    assert meta["canvas"] == [1320, 2868]
    assert meta["panel_mode"] == "clean"
    assert meta["background"] == {"style": "plain", "colors": ["#FFD7F0"]}
    assert meta["screen_rect"][2] > 0   # screen width > 0
    assert meta["breakout_zone"] is None


def test_compose_hero_slot_records_breakout_zone(
    sample_ui_path, tmp_output, assets_dir
):
    sidecar = tmp_output.replace(".png", ".meta.json")
    compose.compose(
        device="iphone-6.9",
        bg_style="plain",
        bg_colors=["#FFD7F0"],
        verb="GIVE",
        desc="ITEMS",
        text_color="#BC004B",
        screenshot_path=sample_ui_path,
        frame_path=os.path.join(assets_dir, "iphone-6.9-frame.png"),
        output_path=tmp_output,
        breakout_zone=(60, 950, 760, 820),
    )
    meta = json.load(open(sidecar))
    assert meta["panel_mode"] == "hero"
    assert meta["breakout_zone"] == [60, 950, 760, 820]
