# -*- coding: utf-8 -*-
"""Generate Hawaa PNG/ICO branding assets from vector-like drawing primitives."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "resources" / "branding"
OUT.mkdir(parents=True, exist_ok=True)

PRIMARY_DARK = (19, 78, 74, 255)
PRIMARY = (15, 118, 110, 255)
ACCENT = (217, 119, 6, 255)
WHITE = (255, 255, 255, 255)
GOLD = (251, 191, 36, 255)
SLATE = (15, 23, 42, 255)
MUTED = (100, 116, 139, 255)
SURFACE = (248, 250, 252, 255)


def font(size: int, bold: bool = False, arabic: bool = False):
    candidates = []
    if arabic:
        candidates.extend([
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Medium.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        ])
    candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ])
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def rounded_gradient(size: int, radius: int = None) -> Image.Image:
    radius = radius or int(size * 0.20)
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pix = grad.load()
    for y in range(size):
        for x in range(size):
            tx = x / max(1, size - 1)
            ty = y / max(1, size - 1)
            t = min(1, max(0, (tx * 0.55 + ty * 0.45)))
            if t < 0.65:
                u = t / 0.65
                c = tuple(int(PRIMARY_DARK[i] * (1 - u) + PRIMARY[i] * u) for i in range(4))
            else:
                u = (t - 0.65) / 0.35
                c = tuple(int(PRIMARY[i] * (1 - u) + ACCENT[i] * u) for i in range(4))
            pix[x, y] = c
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    m = max(3, int(size * 0.07))
    d.rounded_rectangle([m, m, size - m, size - m], radius=radius, fill=255)
    base.alpha_composite(grad, (0, 0))
    base.putalpha(mask)
    return base


def draw_symbol(size: int, badge: str | None = None) -> Image.Image:
    img = rounded_gradient(size)
    d = ImageDraw.Draw(img)
    # translucent ledger card
    x1, y1 = int(size * 0.23), int(size * 0.30)
    x2, y2 = int(size * 0.77), int(size * 0.72)
    d.rounded_rectangle([x1, y1, x2, y2], radius=int(size * 0.10), fill=(255, 255, 255, 42))
    line_w = max(3, int(size * 0.06))
    left = int(size * 0.30)
    right = int(size * 0.70)
    ys = [int(size * 0.38), int(size * 0.49), int(size * 0.60)]
    for i, y in enumerate(ys):
        end = right if i < 2 else int(size * 0.55)
        d.line([left, y, end, y], fill=WHITE, width=line_w, joint="curve")
    # trend mark
    tw = max(3, int(size * 0.052))
    pts = [
        (int(size * 0.61), int(size * 0.63)),
        (int(size * 0.70), int(size * 0.52)),
        (int(size * 0.79), int(size * 0.60)),
    ]
    d.line(pts, fill=GOLD, width=tw, joint="curve")
    r = max(3, int(size * 0.030))
    d.ellipse([pts[-1][0] - r, pts[-1][1] - r, pts[-1][0] + r, pts[-1][1] + r], fill=GOLD)
    if badge:
        br = int(size * 0.16)
        bx, by = int(size * 0.72), int(size * 0.70)
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 255, 255, 245))
        d.ellipse([bx - br, by - br, bx + br, by + br], outline=(219, 228, 232, 255), width=max(1, int(size * 0.012)))
        f = font(max(8, int(size * 0.13)), bold=True)
        text = badge[:2]
        bbox = d.textbbox((0, 0), text, font=f)
        d.text((bx - (bbox[2]-bbox[0]) / 2, by - (bbox[3]-bbox[1]) / 2 - int(size * 0.01)), text, font=f, fill=PRIMARY_DARK)
    return img


def logo_png() -> Image.Image:
    w, h = 720, 220
    img = Image.new("RGBA", (w, h), SURFACE)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=36, fill=SURFACE, outline=(219, 228, 232, 255), width=2)
    # shadow + symbol
    symbol = draw_symbol(150).resize((150, 150), Image.LANCZOS)
    shadow = Image.new("RGBA", (190, 190), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([20, 20, 170, 170], radius=34, fill=(15, 23, 42, 80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow, (22, 18))
    img.alpha_composite(symbol, (42, 35))
    # Arabic text might not shape in PIL, but the SVG version keeps it as text for Qt/browser renderers.
    title_font = font(46, bold=True, arabic=True)
    sub_font = font(24, bold=False, arabic=True)
    # Place right-aligned Arabic title.
    title = "هوى الشام"
    subtitle = "نظام الحسابات الداخلية"
    tb = d.textbbox((0, 0), title, font=title_font)
    sb = d.textbbox((0, 0), subtitle, font=sub_font)
    d.text((670 - (tb[2]-tb[0]), 58), title, font=title_font, fill=SLATE)
    d.text((670 - (sb[2]-sb[0]), 112), subtitle, font=sub_font, fill=MUTED)
    d.rounded_rectangle([395, 166, 670, 173], radius=4, fill=PRIMARY)
    d.rounded_rectangle([395, 166, 520, 173], radius=4, fill=ACCENT)
    return img


def save_icon_set():
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    images = []
    for s in sizes:
        img = draw_symbol(s)
        img.save(OUT / f"app_icon_{s}.png")
        images.append(img)
    images[-1].save(OUT / "app.ico", sizes=[(s, s) for s in sizes])
    images[-1].save(OUT / "installer.ico", sizes=[(s, s) for s in sizes])
    # File icons: keep the same brand mark with short badges.
    proj = [draw_symbol(s, "P") for s in sizes]
    proj[-1].save(OUT / "project_file.ico", sizes=[(s, s) for s in sizes])
    backup = [draw_symbol(s, "B") for s in sizes]
    backup[-1].save(OUT / "backup_file.ico", sizes=[(s, s) for s in sizes])


if __name__ == "__main__":
    logo_png().save(OUT / "app_logo.png")
    draw_symbol(512).save(OUT / "app_symbol_512.png")
    save_icon_set()
    print(f"Generated branding assets in {OUT}")
