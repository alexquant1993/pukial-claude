"""Generate a 256x512 blue PNG used as a fake app UI in compose tests."""
import os
from PIL import Image, ImageDraw

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_ui.png")


def main():
    img = Image.new("RGBA", (256, 512), (45, 90, 200, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 40, 236, 80], fill=(255, 255, 255, 255))
    draw.rectangle([20, 100, 236, 140], fill=(255, 255, 255, 255))
    img.save(OUT_PATH, format="PNG")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
