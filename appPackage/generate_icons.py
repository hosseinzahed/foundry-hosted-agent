"""Generate Teams app package icons for the researcher agent.

Produces the two files the Teams manifest expects:
  color.png    192x192, full-bleed artwork
  outline.png   32x32, transparent background, single-colour glyph

Shapes are drawn on a supersampled canvas and downsampled with LANCZOS,
because Pillow's draw primitives are not anti-aliased on their own.
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).parent
SS = 8  # supersampling factor

GRADIENT_TOP = (43, 95, 227)
GRADIENT_BOTTOM = (122, 63, 242)
WHITE = (255, 255, 255, 255)


def _vertical_gradient(size: int) -> Image.Image:
    gradient = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(size - 1, 1)
        gradient.putpixel(
            (0, y),
            tuple(
                round(top + (bottom - top) * t)
                for top, bottom in zip(GRADIENT_TOP, GRADIENT_BOTTOM)
            ),
        )
    return gradient.resize((size, size), Image.NEAREST)


def _draw_magnifier(draw: ImageDraw.ImageDraw, size: int, stroke: float,
                    colour: tuple[int, int, int, int], with_lines: bool) -> None:
    """Draw a magnifying glass centred in a square of the given size."""
    cx, cy = size * 0.44, size * 0.42
    radius = size * 0.26
    w = stroke

    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        outline=colour,
        width=round(w),
    )

    # Handle runs at 45 degrees from the rim towards the lower right.
    start = radius + w * 0.15
    end = radius + size * 0.20
    offset = 0.70710678  # cos/sin of 45 degrees
    draw.line(
        [cx + start * offset, cy + start * offset,
         cx + end * offset, cy + end * offset],
        fill=colour,
        width=round(w),
    )
    # Rounded cap on the handle tip.
    tip = w / 2
    draw.ellipse(
        [cx + end * offset - tip, cy + end * offset - tip,
         cx + end * offset + tip, cy + end * offset + tip],
        fill=colour,
    )

    if not with_lines:
        return

    # Three shortening rules inside the lens, suggesting a page of findings.
    line_w = w * 0.85
    widths = (0.62, 0.78, 0.50)
    for i, rel in enumerate(widths):
        y = cy + (i - 1) * radius * 0.52
        half = radius * rel / 2
        draw.line([cx - half, y, cx + half, y], fill=colour, width=round(line_w))
        draw.ellipse([cx - half - line_w / 2, y - line_w / 2,
                      cx - half + line_w / 2, y + line_w / 2], fill=colour)
        draw.ellipse([cx + half - line_w / 2, y - line_w / 2,
                      cx + half + line_w / 2, y + line_w / 2], fill=colour)


def build_color(final: int = 192) -> Image.Image:
    size = final * SS
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size - 1, size - 1], radius=round(size * 0.22), fill=255
    )
    canvas.paste(_vertical_gradient(size).convert("RGBA"), (0, 0), mask)

    _draw_magnifier(
        ImageDraw.Draw(canvas), size, stroke=size * 0.055,
        colour=WHITE, with_lines=True,
    )
    return canvas.resize((final, final), Image.LANCZOS)


def build_outline(final: int = 32) -> Image.Image:
    size = final * SS
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Heavier relative stroke so the glyph survives being shown at 32 px.
    _draw_magnifier(
        ImageDraw.Draw(canvas), size, stroke=size * 0.085,
        colour=WHITE, with_lines=False,
    )
    return canvas.resize((final, final), Image.LANCZOS)


def main() -> None:
    for name, image in (("color.png", build_color()), ("outline.png", build_outline())):
        path = OUT_DIR / name
        image.save(path, "PNG")
        print(f"{name}: {image.size[0]}x{image.size[1]} mode={image.mode} "
              f"bytes={path.stat().st_size}")


if __name__ == "__main__":
    main()
