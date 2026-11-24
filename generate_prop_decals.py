"""
generate_prop_decals.py — Generates Crisp 2D Workshop & Prop Decal Textures via Pillow
Saves all PNG textures into `generated_textures/`:
  1. welder_panel.png        — MIG Welder control panel (digital ampere LED, dial scales, high-voltage warning)
  2. pressure_gauge.png      — Argon/CO2 manometer white dial with radial ticks & needle
  3. gas_tank_label.png      — Industrial gas cylinder hazard diamond & spec decal
  4. license_plate.png       — Classic Indonesian workshop license plate ("B 1976 MK")
  5. oil_bottle_label.png    — Retro motor oil jug label ("SAE 20W-50")
  6. poster_safety_first.png — Workshop "SAFETY FIRST / UTAMAKAN KESELAMATAN" wall sign
  7. poster_service_chart.png— Technical automotive blueprint & service schedule wall chart
  8. poster_retro_oil.png    — Vintage garage oil advertisement poster
  9. hazard_stripe.png       — Yellow-and-black diagonal industrial wall dado hazard stripe
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent
DECALS_DIR = PROJECT_ROOT / "generated_textures"


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _make_welder_panel(out_dir: Path) -> None:
    W, H = 512, 384
    img = Image.new("RGBA", (W, H), (32, 36, 44, 255))
    d = ImageDraw.Draw(img)

    # Outer industrial bezel & rivets
    d.rounded_rectangle([8, 8, W - 8, H - 8], radius=18, outline=(180, 188, 200, 255), width=5, fill=(38, 42, 52, 255))
    for rx, ry in [(26, 26), (W - 26, 26), (26, H - 26), (W - 26, H - 26)]:
        d.ellipse([rx - 7, ry - 7, rx + 7, ry + 7], fill=(140, 148, 160, 255), outline=(20, 22, 28, 255), width=2)

    # Red brand header bar
    d.rounded_rectangle([24, 22, W - 24, 72], radius=8, fill=(196, 48, 38, 255), outline=(22, 20, 26, 255), width=3)
    d.text((38, 34), "WELDMASTER MIG-250 PRO", fill=(250, 246, 236, 255), font=_load_font(26))

    # Glowing Digital Ampere & Voltage LED Readouts
    for bx, label, val, led_col in [
        (32, "CURRENT (AMPS)", "185 A", (255, 72, 52, 255)),
        (210, "ARC VOLTAGE", "22.4V", (72, 245, 130, 255)),
    ]:
        d.text((bx, 86), label, fill=(190, 198, 212, 255), font=_load_font(14))
        d.rounded_rectangle([bx, 108, bx + 156, 174], radius=8, fill=(14, 16, 20, 255), outline=(95, 104, 118, 255), width=3)
        d.text((bx + 18, 120), val, fill=led_col, font=_load_font(36))

    # High-Voltage Yellow Hazard Triangle Sticker on top-right
    tri = [(436, 92), (484, 174), (388, 174)]
    d.polygon(tri, fill=(242, 196, 36, 255), outline=(22, 20, 24, 255))
    d.line(tri + [tri[0]], fill=(22, 20, 24, 255), width=5)
    bolt = [(439, 114), (424, 142), (438, 142), (430, 166), (452, 136), (437, 136)]
    d.polygon(bolt, fill=(22, 20, 24, 255))

    # Two Graduated Rotary Dial Scales (Voltage & Wire Feed Speed)
    for cx, cy, title in [(135, 278, "VOLTAGE"), (315, 278, "WIRE SPEED")]:
        d.text((cx - 46, cy - 84), title, fill=(214, 220, 230, 255), font=_load_font(15))
        for step in range(11):
            ang = math.radians(135.0 + step * 27.0)
            r0, r1 = 50, 64
            x0, y0 = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0
            x1, y1 = cx + math.cos(ang) * r1, cy + math.sin(ang) * r1
            col = (245, 92, 66, 255) if step >= 8 else (230, 235, 242, 255)
            d.line([(x0, y0), (x1, y1)], fill=col, width=4)
        d.ellipse([cx - 42, cy - 42, cx + 42, cy + 42], fill=(26, 28, 36, 255), outline=(224, 168, 42, 255), width=4)

    # Power Rocker Switch & Green Status Lamp
    d.rounded_rectangle([418, 228, 476, 326], radius=8, fill=(24, 26, 32, 255), outline=(130, 138, 150, 255), width=3)
    d.rounded_rectangle([426, 236, 468, 280], radius=5, fill=(215, 52, 42, 255))
    d.text((434, 248), "ON", fill=(255, 255, 255, 255), font=_load_font(16))
    d.text((431, 294), "OFF", fill=(160, 166, 175, 255), font=_load_font(14))

    img.save(out_dir / "welder_panel.png")


def _make_pressure_gauge(out_dir: Path) -> None:
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2

    # Brass outer rim + white enamel dial face
    d.ellipse([6, 6, S - 6, S - 6], fill=(178, 138, 58, 255), outline=(28, 22, 26, 255), width=6)
    d.ellipse([20, 20, S - 20, S - 20], fill=(248, 245, 236, 255), outline=(36, 32, 36, 255), width=4)

    # Red danger zone arc (top-right)
    d.arc([34, 34, S - 34, S - 34], start=315, end=45, fill=(216, 48, 38, 255), width=12)

    # Graduated pressure ticks
    for i in range(25):
        ang = math.radians(135.0 + i * (270.0 / 24.0))
        r_in = 74 if i % 4 == 0 else 84
        r_out = 98
        w = 4 if i % 4 == 0 else 2
        d.line(
            [(cx + math.cos(ang) * r_in, cy + math.sin(ang) * r_in),
             (cx + math.cos(ang) * r_out, cy + math.sin(ang) * r_out)],
            fill=(28, 26, 32, 255), width=w
        )

    d.text((cx - 24, cy + 36), "BAR", fill=(32, 30, 36, 255), font=_load_font(20))
    d.text((cx - 34, cy - 48), "AR/CO2", fill=(56, 64, 76, 255), font=_load_font(16))

    # Crisp black indicator needle pointing to ~165 BAR
    n_ang = math.radians(248.0)
    d.line(
        [(cx - math.cos(n_ang) * 22, cy - math.sin(n_ang) * 22),
         (cx + math.cos(n_ang) * 82, cy + math.sin(n_ang) * 82)],
        fill=(206, 38, 32, 255), width=6
    )
    d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(32, 30, 36, 255))

    img.save(out_dir / "pressure_gauge.png")


def _make_gas_tank_label(out_dir: Path) -> None:
    W, H = 512, 256
    img = Image.new("RGBA", (W, H), (242, 238, 226, 255))
    d = ImageDraw.Draw(img)

    d.rectangle([6, 6, W - 6, H - 6], outline=(28, 32, 36, 255), width=6)
    d.rectangle([16, 16, W - 16, 66], fill=(34, 118, 72, 255))
    d.text((28, 26), "ARGON 82% / CO2 18% SHIELDING GAS", fill=(255, 255, 255, 255), font=_load_font(21))

    # Green DOT Class 2.2 Non-Flammable Gas Diamond
    dm = [(96, 84), (162, 150), (96, 216), (30, 150)]
    d.polygon(dm, fill=(38, 146, 82, 255), outline=(20, 24, 24, 255))
    d.line(dm + [dm[0]], fill=(20, 24, 24, 255), width=4)
    d.text((82, 178), "2.2", fill=(255, 255, 255, 255), font=_load_font(18))

    d.text((186, 88), "UN 1956 COMPRESSED GAS", fill=(28, 30, 36, 255), font=_load_font(20))
    d.text((186, 122), "WORKING PRESS: 200 BAR", fill=(54, 58, 66, 255), font=_load_font(18))
    d.text((186, 152), "TEST PRESS:    300 BAR", fill=(54, 58, 66, 255), font=_load_font(18))

    # Barcode strips
    for bx in range(188, 472, 9):
        bw = 5 if (bx // 9) % 3 == 0 else 2
        d.rectangle([bx, 188, bx + bw, 228], fill=(22, 22, 26, 255))

    img.save(out_dir / "gas_tank_label.png")


def _make_license_plate(out_dir: Path) -> None:
    W, H = 512, 128
    img = Image.new("RGBA", (W, H), (24, 26, 30, 255))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, W - 6, H - 6], radius=14, outline=(238, 240, 244, 255), width=6, fill=(22, 24, 28, 255))
    d.text((58, 18), "B 1976 MK", fill=(244, 246, 250, 255), font=_load_font(66))
    d.text((212, 92), "11 • 28", fill=(218, 222, 230, 255), font=_load_font(22))
    for bx in (32, W - 32):
        d.ellipse([bx - 7, 24, bx + 7, 38], fill=(170, 176, 186, 255))
    img.save(out_dir / "license_plate.png")


def _make_oil_bottle_label(out_dir: Path) -> None:
    W, H = 256, 256
    img = Image.new("RGBA", (W, H), (238, 172, 34, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([8, 8, W - 8, H - 8], outline=(24, 20, 24, 255), width=6, fill=(244, 238, 220, 255))
    d.rectangle([14, 14, W - 14, 78], fill=(204, 44, 34, 255))
    d.text((24, 28), "TURBO-LUBE", fill=(255, 248, 230, 255), font=_load_font(28))
    d.text((32, 98), "SAE 20W-50", fill=(24, 26, 34, 255), font=_load_font(28))
    d.text((38, 142), "HEAVY DUTY", fill=(58, 64, 76, 255), font=_load_font(22))
    # Checkered racing stripe at bottom
    sq = 22
    for row in range(2):
        for col in range(10):
            c = (24, 24, 28, 255) if (row + col) % 2 == 0 else (245, 245, 245, 255)
            d.rectangle([18 + col * sq, 188 + row * sq, 18 + (col + 1) * sq, 188 + (row + 1) * sq], fill=c)
    img.save(out_dir / "oil_bottle_label.png")


def _make_poster_safety_first(out_dir: Path) -> None:
    W, H = 512, 680
    img = Image.new("RGBA", (W, H), (240, 234, 216, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([10, 10, W - 10, H - 10], outline=(26, 24, 28, 255), width=10)

    # Diagonal hazard header
    d.rectangle([20, 20, W - 20, 130], fill=(238, 184, 32, 255), outline=(26, 24, 28, 255), width=5)
    for sx in range(-120, W + 120, 56):
        d.polygon([(sx, 130), (sx + 28, 130), (sx + 88, 20), (sx + 60, 20)], fill=(28, 26, 30, 255))
    d.rounded_rectangle([54, 42, W - 54, 108], radius=10, fill=(28, 26, 30, 255))
    d.text((88, 54), "SAFETY FIRST!", fill=(248, 204, 42, 255), font=_load_font(42))

    # Green Safety Banner
    d.rectangle([32, 152, W - 32, 224], fill=(32, 128, 76, 255), outline=(26, 24, 28, 255), width=4)
    d.text((52, 170), "UTAMAKAN KESELAMATAN", fill=(255, 255, 255, 255), font=_load_font(30))

    # Bold Welding Goggles Icon Illustration
    d.ellipse([96, 262, 246, 412], fill=(42, 92, 78, 255), outline=(26, 24, 28, 255), width=10)
    d.ellipse([266, 262, 416, 412], fill=(42, 92, 78, 255), outline=(26, 24, 28, 255), width=10)
    d.rectangle([238, 322, 274, 352], fill=(26, 24, 28, 255))
    d.ellipse([128, 290, 168, 324], fill=(220, 248, 236, 255))
    d.ellipse([298, 290, 338, 324], fill=(220, 248, 236, 255))

    d.text((54, 448), "WAJIB SAAT MENGELAS:", fill=(192, 42, 34, 255), font=_load_font(30))
    d.text((58, 502), "1. GUNAKAN KACAMATA LAS", fill=(32, 30, 36, 255), font=_load_font(25))
    d.text((58, 548), "2. PASTIKAN DONGKRAK AMAN", fill=(32, 30, 36, 255), font=_load_font(25))
    d.text((58, 594), "3. JAUHKAN BAHAN MUDAH", fill=(32, 30, 36, 255), font=_load_font(25))
    d.text((92, 626), "TERBAKAR DARI PERCIKAN", fill=(32, 30, 36, 255), font=_load_font(23))

    img.save(out_dir / "poster_safety_first.png")


def _make_poster_service_chart(out_dir: Path) -> None:
    W, H = 512, 680
    img = Image.new("RGBA", (W, H), (34, 68, 108, 255))
    d = ImageDraw.Draw(img)

    # Blueprint grid
    for gx in range(0, W, 32):
        d.line([(gx, 0), (gx, H)], fill=(52, 94, 142, 255), width=1)
    for gy in range(0, H, 32):
        d.line([(0, gy), (W, gy)], fill=(52, 94, 142, 255), width=1)

    d.rectangle([14, 14, W - 14, H - 14], outline=(232, 244, 255, 255), width=6)
    d.text((40, 36), "SPESIFIKASI & JADWAL", fill=(240, 248, 255, 255), font=_load_font(32))
    d.text((40, 78), "SERVIS BENGKEL KLASIK", fill=(168, 214, 255, 255), font=_load_font(26))

    # Blueprint car silhouette diagram
    pts = [(68, 268), (74, 224), (156, 214), (206, 162), (336, 162), (392, 216), (444, 226), (446, 268)]
    d.polygon(pts, outline=(240, 248, 255, 255), fill=(44, 86, 134, 255))
    d.line(pts + [pts[0]], fill=(240, 248, 255, 255), width=5)
    for wx in (142, 368):
        d.ellipse([wx - 36, 238, wx + 36, 310], fill=(28, 54, 88, 255), outline=(240, 248, 255, 255), width=5)

    # Dimension lines & torque chart bars
    d.line([(68, 336), (446, 336)], fill=(255, 212, 76, 255), width=3)
    d.text((186, 344), "3.950 MM WHEELBASE", fill=(255, 212, 76, 255), font=_load_font(18))

    specs = [
        ("OLI MESIN", 0.85, (242, 186, 52, 255)),
        ("TEKANAN REM", 0.72, (92, 218, 142, 255)),
        ("ARUS LAS MIG", 0.92, (98, 198, 255, 255)),
        ("TORSI RODA", 0.78, (242, 112, 86, 255)),
    ]
    for idx, (lbl, frac, bcol) in enumerate(specs):
        by = 404 + idx * 62
        d.text((42, by), lbl, fill=(235, 244, 255, 255), font=_load_font(20))
        d.rectangle([216, by + 2, 462, by + 28], outline=(200, 224, 248, 255), width=2)
        d.rectangle([220, by + 6, int(220 + 238 * frac), by + 24], fill=bcol)

    img.save(out_dir / "poster_service_chart.png")


def _make_poster_retro_oil(out_dir: Path) -> None:
    W, H = 512, 680
    img = Image.new("RGBA", (W, H), (188, 48, 36, 255))
    d = ImageDraw.Draw(img)

    # Cream inner vintage border
    d.rounded_rectangle([18, 18, W - 18, H - 18], radius=22, fill=(246, 234, 204, 255), outline=(28, 22, 24, 255), width=8)
    d.rounded_rectangle([36, 36, W - 36, 168], radius=14, fill=(28, 36, 52, 255))
    d.text((58, 56), "GARASI MEKANIK", fill=(246, 194, 52, 255), font=_load_font(38))
    d.text((92, 110), "EST. 1976 • CUSTOM WELD", fill=(240, 236, 224, 255), font=_load_font(22))

    # Bold Gear + Oil Drop Emblem in Center
    cx, cy = W // 2, 346
    for i in range(12):
        ang = math.radians(i * 30.0)
        gx, gy = cx + math.cos(ang) * 116, cy + math.sin(ang) * 116
        d.ellipse([gx - 22, gy - 22, gx + 22, gy + 22], fill=(204, 52, 38, 255))
    d.ellipse([cx - 108, cy - 108, cx + 108, cy + 108], fill=(204, 52, 38, 255), outline=(28, 22, 24, 255), width=8)
    d.ellipse([cx - 72, cy - 72, cx + 72, cy + 72], fill=(246, 194, 52, 255), outline=(28, 22, 24, 255), width=6)
    # Oil drop shape
    d.polygon([(cx, cy - 48), (cx + 34, cy + 14), (cx - 34, cy + 14)], fill=(28, 32, 42, 255))
    d.ellipse([cx - 34, cy - 10, cx + 34, cy + 48], fill=(28, 32, 42, 255))

    d.rectangle([42, 512, W - 42, 624], fill=(204, 52, 38, 255), outline=(28, 22, 24, 255), width=5)
    d.text((68, 528), "SUPER MOTOR OIL", fill=(255, 248, 226, 255), font=_load_font(34))
    d.text((112, 578), "PERFORMA TINGGI • 20W-50", fill=(248, 210, 82, 255), font=_load_font(20))

    img.save(out_dir / "poster_retro_oil.png")


def _make_hazard_stripe(out_dir: Path) -> None:
    W, H = 512, 64
    img = Image.new("RGBA", (W, H), (232, 178, 32, 255))
    d = ImageDraw.Draw(img)
    step = 64
    for sx in range(-H, W + H, step):
        d.polygon(
            [(sx, H), (sx + step // 2, H), (sx + step // 2 + H, 0), (sx + H, 0)],
            fill=(26, 26, 32, 255),
        )
    d.rectangle([0, 0, W - 1, 4], fill=(20, 20, 24, 255))
    d.rectangle([0, H - 5, W - 1, H - 1], fill=(20, 20, 24, 255))
    img.save(out_dir / "hazard_stripe.png")


def generate_all_decals(out_dir: Path = DECALS_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    _make_welder_panel(out_dir)
    _make_pressure_gauge(out_dir)
    _make_gas_tank_label(out_dir)
    _make_license_plate(out_dir)
    _make_oil_bottle_label(out_dir)
    _make_poster_safety_first(out_dir)
    _make_poster_service_chart(out_dir)
    _make_poster_retro_oil(out_dir)
    _make_hazard_stripe(out_dir)
    print(f"[Decals] Generated 9 high-res workshop & prop PNG decals in {out_dir}")
    return out_dir


if __name__ == "__main__":
    generate_all_decals()
