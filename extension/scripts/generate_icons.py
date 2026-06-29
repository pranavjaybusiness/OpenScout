"""Generate square Chrome extension icons from the OpenScout logo.

Reads the transparent source logo and writes 16/48/128 px square PNGs
(with transparent padding to keep the logo's aspect ratio) into icons/.
"""

from pathlib import Path

from PIL import Image

EXTENSION_DIR = Path(__file__).resolve().parent.parent
SOURCE = EXTENSION_DIR / "OpenScout logo.png"
OUT_DIR = EXTENSION_DIR / "icons"
SIZES = (16, 48, 128)
# Fraction of the canvas the logo's longest side should occupy.
SCALE = 0.92


def main() -> None:
    logo = Image.open(SOURCE).convert("RGBA")
    OUT_DIR.mkdir(exist_ok=True)

    for size in SIZES:
        target = int(size * SCALE)
        scaled = logo.copy()
        scaled.thumbnail((target, target), Image.LANCZOS)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = ((size - scaled.width) // 2, (size - scaled.height) // 2)
        canvas.paste(scaled, offset, scaled)
        canvas.save(OUT_DIR / f"icon{size}.png")
        print(f"Wrote icons/icon{size}.png")


if __name__ == "__main__":
    main()
