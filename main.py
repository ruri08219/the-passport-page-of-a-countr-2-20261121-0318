#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

Draws, with Pillow only, a fictional passport spread for the Tidal Republic
of Merrow: a data page (left) and a visa/stamp page (right). Deterministic:
fixed palette, fixed geometry, no network, no time/hash randomness.
Writes /output/entry.png (1024x1024 PNG).
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- palette ---
NAVY = (11, 31, 51)          # outer background
CREAM = (247, 241, 222)      # paper
CREAM_DARK = (238, 230, 203)
INK = (24, 42, 58)           # main text
TEAL = (18, 90, 96)
TEAL_DARK = (10, 62, 70)
GOLD = (176, 138, 54)
GOLD_LIGHT = (201, 164, 92)
RULE = (120, 110, 88)
GUILLOCHE = (214, 203, 170)
AQUA = (214, 236, 232)       # visa sticker
AQUA_EDGE = (120, 170, 165)
STAMP_TEAL = (16, 96, 104)
STAMP_PURPLE = (88, 62, 150)
STAMP_GREEN = (34, 120, 74)
STAMP_RED = (178, 44, 44)
PHOTO_BG = (185, 201, 212)
PHOTO_DOT = (168, 186, 199)
SKIN = (216, 178, 140)
SKIN_DARK = (198, 158, 120)
HAIR = (38, 48, 62)
JACKET = (46, 90, 107)

SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
SERIF_B = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

W = H = 1024


def font(path, size):
    return ImageFont.truetype(path, size)


def centre(draw, cx, y, text, fnt, fill):
    draw.text((cx - draw.textlength(text, font=fnt) / 2, y), text,
              font=fnt, fill=fill)


def mrz_check(s):
    """ICAO 9303 check digit, weights 7, 3, 1."""
    total = 0
    for i, ch in enumerate(s):
        if ch == "<":
            v = 0
        elif ch.isdigit():
            v = int(ch)
        else:
            v = 10 + ord(ch) - 65
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def mrz_lines():
    name = "LINDQVIST<<ANOUK<FREYA"
    name = name + "<" * (39 - len(name))
    line1 = "P<MRW" + name
    doc = "004817293"
    dob = "910314"
    exp = "340501"
    personal = "<" * 14
    cd_doc = mrz_check(doc)
    cd_dob = mrz_check(dob)
    cd_exp = mrz_check(exp)
    cd_per = mrz_check(personal)
    # Composite check digit (ICAO 9303): over document number + its check
    # digit, date of birth + its check digit, date of expiry + its check
    # digit, and personal number + its check digit. Nationality and sex
    # are NOT part of the composite.
    composite = doc + cd_doc + dob + cd_dob + exp + cd_exp \
        + personal + cd_per
    line2 = (doc + cd_doc + "MRW" + dob + cd_dob + "F" + exp + cd_exp
             + personal + cd_per + mrz_check(composite))
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


def guilloche(draw, x0, y0, x1, y1):
    """Faint procedural wavy lines across a paper page."""
    for k in range(14):
        yy = y0 + 18 + k * ((y1 - y0 - 36) // 13)
        pts = []
        for x in range(x0 + 8, x1 - 8, 6):
            pts.append((x, yy + 5 * math.sin((x - x0) / 34.0 + k * 0.9)))
        draw.line(pts, fill=GUILLOCHE, width=1)
    for k in range(6):
        cx = x0 + 30 + k * ((x1 - x0 - 60) // 5)
        for r in (26, 40, 54):
            draw.arc([cx - r, y0 + 26 - r, cx + r, y0 + 26 + r],
                     200, 340, fill=GUILLOCHE, width=1)


def circular_text(base, cx, cy, radius, text, fnt, fill, start_deg=-90,
                  clockwise=True):
    """Draw text along a circle, letters upright on the ring.

    Letter spacing is derived from the measured average glyph width so
    neighbouring letters never overlap on the ring.
    """
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    probe = ImageDraw.Draw(base)
    avg_w = probe.textlength(text, font=fnt) / max(len(text), 1)
    step = math.degrees(avg_w * 1.08 / radius)
    span = step * len(text)
    for i, ch in enumerate(text):
        ang = -90 - span / 2 + (i + 0.5) * step
        rad = math.radians(ang)
        x = cx + radius * math.cos(rad)
        y = cy + radius * math.sin(rad)
        glyph = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glyph)
        gd.text((20, 20), ch, font=fnt, fill=fill + (255,),
                anchor="mm")
        glyph = glyph.rotate(-(ang + 90) if clockwise else -(ang - 90),
                             resample=Image.BICUBIC, center=(20, 20))
        layer.alpha_composite(glyph, (int(x) - 20, int(y) - 20))
    base.alpha_composite(layer)


def stamp_layer(size, draw_fn, angle):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer))
    return layer.rotate(angle, resample=Image.BICUBIC, expand=False)


def draw_portrait(draw, x, y, w, h):
    """Stylised duotone passport portrait: tide pilot, tied-back hair."""
    draw.rectangle([x, y, x + w, y + h], fill=PHOTO_BG)
    # halftone dots
    for gy in range(y + 8, y + h, 14):
        for gx in range(x + 8, x + w, 14):
            draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=PHOTO_DOT)
    # shoulders / jacket
    draw.polygon([(x + 8, y + h), (x + 34, y + 128), (x + 52, y + 118),
                  (x + w - 52, y + 118), (x + w - 34, y + 128),
                  (x + w - 8, y + h)], fill=JACKET)
    # shirt V
    draw.polygon([(x + 58, y + 120), (x + 74, y + 142), (x + 90, y + 120)],
                 fill=CREAM)
    # neck
    draw.rectangle([x + 62, y + 96, x + 86, y + 124], fill=SKIN_DARK)
    # head
    draw.ellipse([x + 44, y + 22, x + 104, y + 104], fill=SKIN)
    # hair: bun at the back-top first (behind the cap), then a cap over
    # the crown, forehead re-exposed, and locks down both sides so the
    # hair reads as tied back rather than a headband
    draw.ellipse([x + 84, y + 2, x + 108, y + 28], fill=HAIR)  # bun
    draw.pieslice([x + 40, y + 14, x + 108, y + 88], 180, 360, fill=HAIR)
    draw.ellipse([x + 52, y + 32, x + 96, y + 74], fill=SKIN)  # forehead
    draw.rectangle([x + 42, y + 44, x + 54, y + 96], fill=HAIR)  # left lock
    draw.rectangle([x + 94, y + 44, x + 106, y + 96], fill=HAIR)  # right lock
    # minimal features: eyes, brows, nose, mouth
    draw.line([x + 58, y + 62, x + 68, y + 62], fill=INK, width=2)
    draw.line([x + 80, y + 62, x + 90, y + 62], fill=INK, width=2)
    draw.line([x + 57, y + 55, x + 69, y + 54], fill=HAIR, width=2)
    draw.line([x + 79, y + 54, x + 91, y + 55], fill=HAIR, width=2)
    draw.line([x + 74, y + 64, x + 73, y + 76], fill=SKIN_DARK, width=2)
    draw.arc([x + 64, y + 80, x + 84, y + 92], 20, 160, fill=(150, 90, 70),
             width=2)
    # soft cheek shading
    draw.arc([x + 46, y + 66, x + 62, y + 88], 300, 60, fill=SKIN_DARK,
             width=2)
    draw.rectangle([x, y, x + w, y + h], outline=INK, width=2)


def draw_coat_of_arms(draw, cx, top):
    """Shield, lighthouse with rays, three waves, three stars."""
    # stars above the shield
    for sx in (cx - 42, cx, cx + 42):
        sy = top + 6
        star = [(sx, sy - 7), (sx + 2, sy - 2), (sx + 7, sy - 2),
                (sx + 3, sy + 2), (sx + 5, sy + 7), (sx, sy + 4),
                (sx - 5, sy + 7), (sx - 3, sy + 2), (sx - 7, sy - 2),
                (sx - 2, sy - 2)]
        draw.polygon(star, fill=GOLD)
    # shield
    sh = [(cx - 30, top + 18), (cx + 30, top + 18), (cx + 30, top + 52),
          (cx, top + 72), (cx - 30, top + 52)]
    draw.polygon(sh, outline=TEAL_DARK, width=3)
    draw.polygon([(cx - 26, top + 22), (cx + 26, top + 22),
                  (cx + 26, top + 50), (cx, top + 66),
                  (cx - 26, top + 50)], fill=(226, 238, 234))
    # lighthouse
    draw.polygon([(cx - 6, top + 28), (cx + 6, top + 28), (cx + 4, top + 52),
                  (cx - 4, top + 52)], fill=TEAL)
    draw.polygon([(cx - 9, top + 24), (cx + 9, top + 24), (cx, top + 16)],
                 fill=GOLD)
    draw.rectangle([cx - 7, top + 30, cx + 7, top + 34], fill=CREAM)
    # light rays
    for dx, dy in ((-22, -4), (-26, 2), (22, -4), (26, 2)):
        draw.line([cx + (dx // 3), top + 28, cx + dx, top + 28 + dy],
                  fill=GOLD, width=2)
    # three waves below the lighthouse
    for wy in (top + 54, top + 59, top + 64):
        draw.arc([cx - 20, wy - 4, cx - 6, wy + 4], 0, 180, fill=TEAL,
                 width=2)
        draw.arc([cx - 6, wy - 4, cx + 8, wy + 4], 0, 180, fill=TEAL,
                 width=2)
        draw.arc([cx + 8, wy - 4, cx + 22, wy + 4], 0, 180, fill=TEAL,
                 width=2)


def field(draw, x, y, label, value, value_size=19, label_size=10):
    draw.text((x, y), label, font=font(SANS, label_size), fill=RULE)
    draw.text((x, y + 13), value, font=font(SANS_B, value_size), fill=INK)


def draw_left_page(img, draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=CREAM)
    draw.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], outline=RULE, width=1)
    draw.rectangle([x0 + 9, y0 + 9, x1 - 9, y1 - 9], outline=RULE, width=1)
    guilloche(draw, x0, y0, x1, y1)

    draw_coat_of_arms(draw, (x0 + x1) // 2, y0 + 16)
    cy = (x0 + x1) // 2
    centre(draw, cy, y0 + 96, "TIDAL REPUBLIC OF MERROW",
           font(SERIF_B, 23), TEAL_DARK)
    centre(draw, cy, y0 + 124, "PASSPORT  ·  PASPOR MERROWAN",
           font(SERIF, 14), INK)
    draw.line([x0 + 40, y0 + 148, x1 - 40, y0 + 148], fill=GOLD, width=2)

    # document line
    centre(draw, cy, y0 + 158, "Type  P      Code  MRW      No.  MRW 004 817 293",
           font(SANS_B, 15), INK)

    # portrait, top-left
    px, py = x0 + 24, y0 + 196
    draw_portrait(draw, px, py, 148, 188)

    # fields right of the portrait
    fx = px + 168
    field(draw, fx, py + 2, "SURNAME", "LINDQVIST", 21)
    field(draw, fx, py + 52, "GIVEN NAMES", "ANOUK FREYA", 19)
    field(draw, fx, py + 100, "NATIONALITY", "MERROWAN", 19)
    field(draw, fx, py + 146, "DATE OF BIRTH", "14 MAR 1991", 19)

    # fields below the portrait, full width
    fy = py + 208
    field(draw, x0 + 24, fy, "PLACE OF BIRTH", "PORT MERROW", 19)
    field(draw, x0 + 250, fy, "SEX", "F", 19)
    field(draw, x0 + 300, fy, "OCCUPATION", "TIDE PILOT", 19)
    fy += 52
    field(draw, x0 + 24, fy, "DATE OF ISSUE", "02 MAY 2024", 19)
    field(draw, x0 + 250, fy, "DATE OF EXPIRY", "01 MAY 2034", 19)
    fy += 52
    field(draw, x0 + 24, fy, "AUTHORITY", "MINISTRY OF TIDES — PORT MERROW",
          16)
    # holder's signature, filling the blank run above the MRZ
    sy = fy + 56
    draw.text((x0 + 24, sy), "SIGNATURE OF HOLDER", font=font(SANS, 10),
              fill=RULE)
    draw.text((x0 + 24, sy + 14), "Anouk Freya Lindqvist",
              font=font("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 22),
              fill=INK)
    draw.line([x0 + 24, sy + 44, x0 + 240, sy + 44], fill=RULE, width=1)

    # machine-readable zone
    line1, line2 = mrz_lines()
    mz = y1 - 96
    draw.rectangle([x0 + 16, mz - 8, x1 - 16, mz + 62], fill=(255, 255, 255))
    draw.rectangle([x0 + 16, mz - 8, x1 - 16, mz + 62], outline=RULE, width=1)
    mf = font(MONO, 16)
    draw.text((x0 + 22, mz), line1, font=mf, fill=INK)
    draw.text((x0 + 22, mz + 24), line2, font=mf, fill=INK)
    centre(draw, cy, y1 - 26,
           "THIS PASSPORT REMAINS THE PROPERTY OF THE TIDAL REPUBLIC OF MERROW",
           font(SANS, 9), RULE)


def draw_right_page(img, draw, x0, y0, x1, y1):
    draw.rectangle([x0, y0, x1, y1], fill=CREAM)
    draw.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], outline=RULE, width=1)
    draw.rectangle([x0 + 9, y0 + 9, x1 - 9, y1 - 9], outline=RULE, width=1)
    guilloche(draw, x0, y0, x1, y1)

    cx = (x0 + x1) // 2
    centre(draw, cx, y0 + 22, "VISAS", font(SERIF_B, 24), TEAL_DARK)
    draw.text((x1 - 78, y0 + 30), "PAGE 12", font=font(SANS_B, 13),
              fill=INK)
    draw.line([x0 + 40, y0 + 56, x1 - 40, y0 + 56], fill=GOLD, width=2)

    # --- visa sticker: Kingdom of Nordfell ---
    vx0, vy0, vx1, vy1 = x0 + 28, y0 + 74, x1 - 28, y0 + 216
    draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=10, fill=AQUA,
                           outline=AQUA_EDGE, width=2)
    draw.rounded_rectangle([vx0 + 6, vy0 + 6, vx1 - 6, vy1 - 6], radius=8,
                           outline=AQUA_EDGE, width=1)
    vcx = (vx0 + vx1) // 2
    centre(draw, vcx, vy0 + 12, "KINGDOM OF NORDFELL  —  VISA",
           font(SERIF_B, 17), (20, 60, 70))
    centre(draw, vcx, vy0 + 40, "SINGLE ENTRY", font(SANS_B, 14), INK)
    centre(draw, vcx, vy0 + 62, "No. NF-8841-552",
           font(MONO, 14), INK)
    centre(draw, vcx, vy0 + 84, "Issued 21 AUG 2024 at Port Merrow  ·  Valid 90 days",
           font(SANS, 13), INK)
    centre(draw, vcx, vy0 + 106, "Fee 40 TM  ·  TIDE-MARK",
           font(SANS_B, 13), INK)

    # --- round arrival stamp: Port Merrow, 17 JUN 2024 ---
    sx, sy, sr = x0 + 108, y0 + 300, 72
    layer = stamp_layer(img.size, lambda d: (
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr],
                  outline=STAMP_TEAL, width=4),
        d.ellipse([sx - sr + 12, sy - sr + 12, sx + sr - 12, sy + sr - 12],
                  outline=STAMP_TEAL, width=2),
        circular_text(img, sx, sy, sr - 16,
                      "PORT MERROW · TIDAL REPUBLIC OF MERROW · ",
                      font(SANS_B, 11), STAMP_TEAL),
        d.text((sx, sy - 16), "ARRIVED", font=font(SANS_B, 15),
               fill=STAMP_TEAL, anchor="mm"),
        d.text((sx, sy + 6), "17 JUN 2024", font=font(SANS_B, 14),
               fill=STAMP_TEAL, anchor="mm"),
    ), -8)
    img.alpha_composite(layer)

    # --- rectangular departure stamp: 03 SEP 2024 ---
    dx0, dy0, dx1, dy1 = x0 + 236, y0 + 252, x1 - 30, y0 + 348
    dcx, dcy = (dx0 + dx1) // 2, (dy0 + dy1) // 2
    layer = stamp_layer(img.size, lambda d: (
        d.rectangle([dx0, dy0, dx1, dy1], outline=STAMP_PURPLE, width=4),
        d.rectangle([dx0 + 7, dy0 + 7, dx1 - 7, dy1 - 7],
                    outline=STAMP_PURPLE, width=1),
        d.text((dcx, dy0 + 22), "DEPARTED", font=font(SANS_B, 16),
               fill=STAMP_PURPLE, anchor="mm"),
        d.text((dcx, dy0 + 46), "PORT MERROW", font=font(SANS_B, 15),
               fill=STAMP_PURPLE, anchor="mm"),
        d.text((dcx, dy0 + 70), "03 SEP 2024", font=font(SANS_B, 15),
               fill=STAMP_PURPLE, anchor="mm"),
    ), 6)
    img.alpha_composite(layer)

    # --- round green stamp: Isles of Brenna, 12–19 JAN 2025 ---
    bx, by, br = x0 + 108, y0 + 486, 66
    layer = stamp_layer(img.size, lambda d: (
        d.ellipse([bx - br, by - br, bx + br, by + br],
                  outline=STAMP_GREEN, width=4),
        d.ellipse([bx - br + 11, by - br + 11, bx + br - 11, by + br - 11],
                  outline=STAMP_GREEN, width=2),
        circular_text(img, bx, by, br - 14,
                      "ISLES OF BRENNA · ENTERED · ",
                      font(SANS_B, 11), STAMP_GREEN),
        d.text((bx, by - 12), "ENTERED", font=font(SANS_B, 13),
               fill=STAMP_GREEN, anchor="mm"),
        d.text((bx, by + 8), "12 JAN 2025", font=font(SANS_B, 13),
               fill=STAMP_GREEN, anchor="mm"),
        d.text((bx, by + 28), "EXIT 19 JAN 2025", font=font(SANS_B, 11),
               fill=STAMP_GREEN, anchor="mm"),
    ), 5)
    img.alpha_composite(layer)

    # --- small red fee stamp ---
    fx0, fy0, fx1, fy1 = x0 + 252, y0 + 440, x1 - 34, y0 + 516
    fcx, fcy = (fx0 + fx1) // 2, (fy0 + fy1) // 2
    layer = stamp_layer(img.size, lambda d: (
        d.rectangle([fx0, fy0, fx1, fy1], outline=STAMP_RED, width=3),
        d.text((fcx, fy0 + 20), "TIDE FEE PAID", font=font(SANS_B, 14),
               fill=STAMP_RED, anchor="mm"),
        d.text((fcx, fy0 + 42), "12 TM", font=font(SANS_B, 16),
               fill=STAMP_RED, anchor="mm"),
    ), -7)
    img.alpha_composite(layer)

    # --- conditions of entry (the telling detail) ---
    cx0, cy0, cx1, cy1 = x0 + 28, y0 + 576, x1 - 28, y0 + 736
    draw.rectangle([cx0, cy0, cx1, cy1], fill=(255, 252, 240),
                   outline=TEAL_DARK, width=2)
    ccx = (cx0 + cx1) // 2
    centre(draw, ccx, cy0 + 10, "CONDITIONS OF ENTRY",
           font(SANS_B, 14), TEAL_DARK)
    draw.line([cx0 + 30, cy0 + 34, cx1 - 30, cy0 + 34], fill=GOLD, width=1)
    lines = [
        "This passport is valid for travel BY SEA ONLY.",
        "The Republic of Merrow has no airport.",
        "Entry is permitted at LOW TIDE only — consult",
        "the official tide table at the harbour office.",
        "Vessels must clear the causeway before the",
        "tide turns.",
    ]
    for i, ln in enumerate(lines):
        centre(draw, ccx, cy0 + 44 + i * 18, ln, font(SANS, 13), INK)

    # --- archipelago map ---
    mx0, my0, mx1, my1 = x0 + 28, y0 + 756, x1 - 28, y1 - 44
    draw.rectangle([mx0, my0, mx1, my1], fill=(226, 238, 234),
                   outline=RULE, width=1)
    # seven isles, drawn as small polygons
    isles = [
        [(mx0 + 60, my0 + 58), (mx0 + 84, my0 + 40), (mx0 + 108, my0 + 52),
         (mx0 + 100, my0 + 74), (mx0 + 74, my0 + 78)],
        [(mx0 + 150, my0 + 30), (mx0 + 168, my0 + 22), (mx0 + 182, my0 + 34),
         (mx0 + 170, my0 + 46), (mx0 + 154, my0 + 44)],
        [(mx0 + 210, my0 + 66), (mx0 + 232, my0 + 54), (mx0 + 252, my0 + 68),
         (mx0 + 240, my0 + 86), (mx0 + 216, my0 + 84)],
        [(mx0 + 120, my0 + 100), (mx0 + 138, my0 + 90), (mx0 + 156, my0 + 100),
         (mx0 + 146, my0 + 116), (mx0 + 124, my0 + 114)],
        [(mx0 + 270, my0 + 100), (mx0 + 288, my0 + 92), (mx0 + 302, my0 + 104),
         (mx0 + 292, my0 + 118), (mx0 + 274, my0 + 116)],
        [(mx0 + 190, my0 + 128), (mx0 + 204, my0 + 120), (mx0 + 216, my0 + 130),
         (mx0 + 206, my0 + 142), (mx0 + 192, my0 + 140)],
        [(mx0 + 320, my0 + 52), (mx0 + 334, my0 + 44), (mx0 + 346, my0 + 54),
         (mx0 + 336, my0 + 66), (mx0 + 322, my0 + 64)],
    ]
    for isle in isles:
        draw.polygon(isle, fill=(178, 208, 198), outline=TEAL_DARK)
    # capital dot on the largest isle
    draw.ellipse([mx0 + 78, my0 + 54, mx0 + 88, my0 + 64], fill=STAMP_RED)
    draw.text((mx0 + 92, my0 + 52), "Port Merrow", font=font(SANS_B, 11),
              fill=INK)
    # compass rose
    ccx2, ccy2 = mx1 - 46, my0 + 40
    draw.ellipse([ccx2 - 14, ccy2 - 14, ccx2 + 14, ccy2 + 14],
                 outline=TEAL_DARK, width=1)
    draw.polygon([(ccx2, ccy2 - 12), (ccx2 + 3, ccy2), (ccx2, ccy2 + 12),
                  (ccx2 - 3, ccy2)], fill=TEAL_DARK)
    draw.text((ccx2 - 3, ccy2 - 26), "N", font=font(SANS_B, 10),
              fill=TEAL_DARK)
    centre(draw, (mx0 + mx1) // 2, my1 - 22,
           "MERROW ARCHIPELAGO  ·  61°14′ N  8°02′ W  ·  SEVEN ISLES",
           font(SANS_B, 11), INK)


def main():
    img = Image.new("RGBA", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    # two cream pages with a centre gutter
    draw_left = ImageDraw.Draw(img)
    draw_left_page(img, draw_left, 24, 24, 500, 1000)
    draw_right_page(img, ImageDraw.Draw(img), 524, 24, 1000, 1000)
    # gutter shadow between the pages
    draw.line([502, 24, 502, 1000], fill=(6, 18, 30), width=2)
    draw.line([522, 24, 522, 1000], fill=(6, 18, 30), width=2)

    out = img.convert("RGB")
    os.makedirs("/output", exist_ok=True)
    out.save("/output/entry.png", format="PNG", optimize=True)


if __name__ == "__main__":
    main()
