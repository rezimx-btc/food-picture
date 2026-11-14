#!/usr/bin/env python3
"""Golden Omakase Lift — procedural food photograph, stdlib only.

Renders a lavish sushi omakase platter in warm golden-hour light:
chopsticks lifting a glistening salmon nigiri high above a dark
lacquered platter, with a thin soy drip falling from it.

No third-party imports. PNG is encoded by hand (zlib + struct).
Deterministic: fixed seed, no time, no network, no randomness from
the environment. Output: food.png, 1024x1024, under 1 MiB.
"""

import hashlib
import math
import random
import struct
import zlib

W = 1024
H = 1024
OUT = "food.png"

RNG = random.Random(20261114)

# ---------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def put(x, y, r, g, b):
    """Opaque write, clamped."""
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        buf[i] = clamp255(r)
        buf[i + 1] = clamp255(g)
        buf[i + 2] = clamp255(b)


def blend(x, y, r, g, b, a):
    """Alpha-blend a colour over the pixel at (x, y)."""
    if a <= 0.0 or not (0 <= x < W and 0 <= y < H):
        return
    if a >= 1.0:
        put(x, y, int(r), int(g), int(b))
        return
    i = _idx(x, y)
    ia = 1.0 - a
    buf[i] = clamp255(buf[i] * ia + r * a)
    buf[i + 1] = clamp255(buf[i + 1] * ia + g * a)
    buf[i + 2] = clamp255(buf[i + 2] * ia + b * a)


def lerp(c0, c1, t):
    return (c0[0] + (c1[0] - c0[0]) * t,
            c0[1] + (c1[1] - c0[1]) * t,
            c0[2] + (c1[2] - c0[2]) * t)


def clamp255(v):
    v = int(v)
    return 0 if v < 0 else (255 if v > 255 else v)


# ---------------------------------------------------------------- shapes
def vgrad(y0, y1, c0, c1):
    """Vertical gradient over the whole canvas between y0 and y1."""
    for y in range(max(0, y0), min(H, y1)):
        t = (y - y0) / max(1, y1 - y0)
        c = lerp(c0, c1, t)
        r, g, b = int(c[0]), int(c[1]), int(c[2])
        base = y * W * 3
        for x in range(W):
            i = base + x * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b


def ellipse(cx, cy, rx, ry, c_top, c_bottom, alpha=1.0, shear=0.0):
    """Filled ellipse, vertical gradient, optional horizontal shear."""
    x0 = max(0, int(cx - rx - abs(shear) * ry - 2))
    x1 = min(W - 1, int(cx + rx + abs(shear) * ry + 2))
    y0 = max(0, int(cy - ry - 2))
    y1 = min(H - 1, int(cy + ry + 2))
    for y in range(y0, y1 + 1):
        dy = (y - cy) / ry
        if abs(dy) > 1.0:
            continue
        t = (y - (cy - ry)) / (2.0 * ry)
        c = lerp(c_top, c_bottom, t)
        r, g, b = c
        half = rx * math.sqrt(max(0.0, 1.0 - dy * dy))
        sx = cx + shear * (y - cy)
        xa = max(x0, int(sx - half))
        xb = min(x1, int(sx + half))
        for x in range(xa, xb + 1):
            blend(x, y, r, g, b, alpha)


def disc(cx, cy, r, colour, alpha=1.0):
    """Flat filled circle."""
    ellipse(cx, cy, r, r, colour, colour, alpha)


def sphere(cx, cy, r, c_hi, c_mid, c_edge, spec=True, spec_a=0.85):
    """Glossy ball: radial gradient + specular highlight."""
    x0 = max(0, int(cx - r - 1))
    x1 = min(W - 1, int(cx + r + 1))
    y0 = max(0, int(cy - r - 1))
    y1 = min(H - 1, int(cy + r + 1))
    lx, ly = cx - r * 0.38, cy - r * 0.42  # light from upper left
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            dx = (x - cx) / r
            dy = (y - cy) / r
            d2 = dx * dx + dy * dy
            if d2 > 1.0:
                continue
            d = math.sqrt(d2)
            if d < 0.55:
                c = lerp(c_hi, c_mid, d / 0.55)
            else:
                c = lerp(c_mid, c_edge, (d - 0.55) / 0.45)
            # specular dot near the light
            sdx = (x - lx) / (r * 0.30)
            sdy = (y - ly) / (r * 0.30)
            sd2 = sdx * sdx + sdy * sdy
            if spec and sd2 < 1.0:
                sa = (1.0 - sd2) * spec_a
                c = lerp(c, (255, 255, 255), sa * 0.75)
            blend(x, y, c[0], c[1], c[2], 1.0)


def rrect(x0, y0, x1, y1, rad, c_top, c_bottom, alpha=1.0):
    """Filled rounded rectangle with a vertical gradient."""
    for y in range(max(0, y0), min(H, y1 + 1)):
        t = (y - y0) / max(1, y1 - y0)
        c = lerp(c_top, c_bottom, t)
        r, g, b = c
        for x in range(max(0, x0), min(W, x1 + 1)):
            # corner cut-out test
            cx = min(max(x, x0 + rad), x1 - rad)
            cy = min(max(y, y0 + rad), y1 - rad)
            if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                blend(x, y, r, g, b, alpha)


def thick_line(x0, y0, x1, y1, w0, w1, c0, c1):
    """Tapered thick line drawn as a chain of discs."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(2, int(length))
    for s in range(steps + 1):
        t = s / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        w = w0 + (w1 - w0) * t
        c = lerp(c0, c1, t)
        disc(int(x), int(y), max(1.0, w / 2.0), c)


def hline(y, x0, x1, r, g, b, a):
    for x in range(max(0, x0), min(W, x1 + 1)):
        blend(x, y, r, g, b, a)


# ---------------------------------------------------------------- PNG out
def _chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- scene
def draw_background():
    # Golden-hour backdrop: warm amber glow fading into a deep table.
    vgrad(0, 620, (250, 205, 140), (196, 128, 66))
    vgrad(620, H, (122, 74, 38), (58, 32, 16))
    # Soft sun glow, upper left.
    for r in range(420, 0, -6):
        a = 0.05 * (1.0 - r / 430.0)
        disc(300, 150, r, (255, 226, 170), a)
    # Wood planks on the table.
    for py in (640, 760, 880, 990):
        hline(py, 0, W, 46, 24, 10, 0.55)
        hline(py + 2, 0, W, 210, 150, 96, 0.18)
    # Wood grain: long soft sine streaks.
    for _ in range(90):
        gy = RNG.randint(640, 1010)
        gx = RNG.randint(0, W)
        glen = RNG.randint(120, 420)
        gcol = (96, 58, 28) if RNG.random() < 0.5 else (150, 100, 55)
        for s in range(glen):
            x = gx + s
            if x >= W:
                break
            yy = gy + int(3 * math.sin(s / 47.0 + gy))
            blend(x, yy, gcol[0], gcol[1], gcol[2], 0.10)


def draw_platter():
    # Soft shadow under the platter.
    ellipse(512, 905, 430, 62, (20, 10, 5), (20, 10, 5), alpha=0.45)
    # Dark lacquered wood platter, rounded, with a warm rim.
    rrect(96, 470, 928, 962, 46, (52, 32, 24), (22, 12, 8))
    rrect(112, 486, 912, 946, 38, (38, 22, 16), (16, 9, 6))
    # Glossy sheen sweeping across the lacquer.
    ellipse(512, 640, 380, 130, (255, 220, 160), (255, 220, 160), alpha=0.05)
    ellipse(300, 560, 200, 70, (255, 235, 190), (255, 235, 190), alpha=0.06)
    # Thin gold rim line.
    for x in range(130, 895):
        blend(x, 492, 214, 164, 92, 0.35)
        blend(x, 940, 214, 164, 92, 0.22)


def rice_mound(cx, cy, rx, ry, shear=0.0):
    """White sushi-rice mound: soft base + individual grains."""
    ellipse(cx, cy, rx, ry, (250, 246, 238), (214, 204, 190), shear=shear)
    ellipse(cx, cy - ry * 0.25, rx * 0.8, ry * 0.55,
            (255, 252, 246), (235, 228, 216), alpha=0.8, shear=shear)
    # Individual grains: tiny pale ellipses with subtle shading.
    for _ in range(46):
        gx = cx + RNG.uniform(-rx * 0.85, rx * 0.85)
        gy = cy + RNG.uniform(-ry * 0.7, ry * 0.75)
        # keep the grain inside the mound
        nx = (gx - cx) / rx
        ny = (gy - cy) / ry
        if nx * nx + ny * ny > 0.85:
            continue
        shade = RNG.uniform(-14, 16)
        gr = RNG.uniform(4, 9)
        ellipse(gx, gy, gr, gr * 0.55,
                (255 + shade, 252 + shade, 246 + shade),
                (226 + shade, 216 + shade, 202 + shade),
                alpha=0.85, shear=RNG.uniform(-0.4, 0.4))


def salmon_slice(cx, cy, rx, ry, shear=0.0):
    """Glistening salmon draped over rice: orange gradient + fat stripes."""
    ellipse(cx, cy, rx, ry, (255, 158, 92), (226, 92, 44), shear=shear)
    # Fat stripes: pale curved bands across the fish.
    for k, off in enumerate((-0.45, -0.15, 0.15, 0.45)):
        sy = cy + off * ry
        ellipse(cx + shear * (sy - cy), sy, rx * 0.92, ry * 0.16,
                (255, 214, 178), (255, 196, 150), alpha=0.55, shear=shear)
    # Wet gloss: bright streak top-left + small specular dots.
    ellipse(cx - rx * 0.30, cy - ry * 0.42, rx * 0.42, ry * 0.30,
            (255, 236, 210), (255, 236, 210), alpha=0.38, shear=shear)
    disc(cx - rx * 0.45, cy - ry * 0.45, 5, (255, 255, 255), 0.75)
    disc(cx + rx * 0.25, cy - ry * 0.55, 3, (255, 255, 255), 0.6)


def tuna_slice(cx, cy, rx, ry, shear=0.0):
    """Ruby tuna: deep red gradient, fine pale striations, high gloss."""
    ellipse(cx, cy, rx, ry, (214, 62, 78), (146, 22, 34), shear=shear)
    for off in (-0.5, -0.2, 0.1, 0.4):
        sy = cy + off * ry
        ellipse(cx + shear * (sy - cy), sy, rx * 0.9, ry * 0.10,
                (255, 170, 160), (255, 170, 160), alpha=0.35, shear=shear)
    ellipse(cx - rx * 0.28, cy - ry * 0.40, rx * 0.40, ry * 0.28,
            (255, 200, 190), (255, 200, 190), alpha=0.30, shear=shear)
    disc(cx - rx * 0.42, cy - ry * 0.42, 5, (255, 255, 255), 0.7)


def nigiri(cx, cy, kind, shear=0.0, scale=1.0):
    """One nigiri: rice mound + fish slice draped over it."""
    rx, ry = 92 * scale, 34 * scale
    rice_mound(cx, cy + 16 * scale, rx, ry, shear=shear)
    if kind == "salmon":
        salmon_slice(cx, cy - 6 * scale, rx * 1.02, ry * 1.05, shear=shear)
    else:
        tuna_slice(cx, cy - 6 * scale, rx * 1.02, ry * 1.05, shear=shear)
    # Nori-free shadow line where fish meets rice.
    ellipse(cx, cy + 12 * scale, rx * 0.95, ry * 0.30,
            (120, 60, 30), (120, 60, 30), alpha=0.18, shear=shear)


def draw_gunkan(cx, cy, scale=1.0):
    """Gunkan maki: nori cup packed with glistening ikura pearls."""
    # Shiso leaf under the cup.
    ellipse(cx - 52 * scale, cy + 4 * scale, 62 * scale, 17 * scale,
            (46, 110, 52), (28, 76, 34), alpha=0.95, shear=0.3)
    ellipse(cx - 52 * scale, cy + 1 * scale, 52 * scale, 11 * scale,
            (70, 140, 66), (70, 140, 66), alpha=0.5, shear=0.3)
    # Nori cup.
    ellipse(cx, cy, 74 * scale, 46 * scale, (26, 34, 20), (12, 16, 10))
    ellipse(cx, cy - 6 * scale, 64 * scale, 38 * scale,
            (44, 56, 32), (20, 28, 16))
    rice_mound(cx, cy - 2 * scale, 58 * scale, 26 * scale)
    # Ikura pearls: orange spheres with bright speculars.
    pearls = [(-30, -14, 15), (-8, -20, 16), (16, -18, 15), (34, -10, 13),
              (-20, 2, 14), (4, -2, 15), (26, 4, 13), (-38, 4, 11),
              (10, 12, 12), (-10, 14, 11)]
    for px, py, pr in pearls:
        sphere(cx + px * scale, cy + py * scale, pr * scale,
               (255, 176, 92), (240, 120, 40), (176, 74, 14), spec_a=0.9)
    # A few pearls spilling beside the cup.
    sphere(cx + 82 * scale, cy + 26 * scale, 12 * scale,
           (255, 176, 92), (240, 120, 40), (176, 74, 14))
    sphere(cx + 100 * scale, cy + 34 * scale, 10 * scale,
           (255, 176, 92), (240, 120, 40), (176, 74, 14))


def draw_wasabi(cx, cy, scale=1.0):
    """Wasabi mound: bumpy green peaks."""
    ellipse(cx, cy + 8 * scale, 46 * scale, 26 * scale,
            (96, 148, 52), (58, 96, 30))
    for ox, oy, rr in [(-18, -6, 20), (2, -14, 22), (20, -4, 18),
                       (-6, 4, 18), (14, 8, 15)]:
        sphere(cx + ox * scale, cy + oy * scale, rr * scale,
               (150, 196, 84), (110, 164, 60), (66, 106, 34), spec_a=0.5)
    # Spiky tips.
    for tx, ty in [(-14, -30), (4, -38), (20, -26)]:
        thick_line(cx + tx * scale, cy + ty * scale + 16,
                   cx + tx * scale, cy + ty * scale,
                   5, 1, (140, 186, 78), (110, 164, 60))


def draw_ginger(cx, cy, scale=1.0):
    """Pickled ginger: layered pale-pink petals."""
    for ox, oy, rr, a in [(-16, 6, 26, 0.9), (10, -4, 28, 0.95),
                          (2, 12, 24, 0.9), (22, 10, 18, 0.85)]:
        ellipse(cx + ox * scale, cy + oy * scale, rr * scale, rr * 0.62 * scale,
                (250, 196, 196), (232, 150, 158), alpha=a, shear=0.35)
    ellipse(cx, cy, 14 * scale, 8 * scale,
            (255, 224, 222), (255, 224, 222), alpha=0.7)


def draw_soy_dish(cx, cy, scale=1.0):
    """Small black soy-sauce dish with a reflective surface."""
    ellipse(cx, cy + 16 * scale, 62 * scale, 16 * scale,
            (10, 8, 8), (10, 8, 8), alpha=0.5)
    ellipse(cx, cy, 62 * scale, 30 * scale, (30, 24, 24), (12, 10, 10))
    ellipse(cx, cy - 2 * scale, 52 * scale, 22 * scale,
            (74, 38, 20), (30, 14, 8))
    # Reflective streaks on the soy surface.
    ellipse(cx - 12 * scale, cy - 6 * scale, 26 * scale, 6 * scale,
            (255, 220, 180), (255, 220, 180), alpha=0.35)
    disc(cx + 16 * scale, cy - 8 * scale, 3, (255, 240, 210), 0.6)
    # Rim highlight.
    for x in range(int(cx - 52 * scale), int(cx + 52 * scale)):
        t = (x - (cx - 52 * scale)) / (104 * scale)
        blend(x, int(cy - 24 * scale + 6 * math.sin(t * math.pi)),
              220, 200, 180, 0.25)

# ---------------------------------------------------------------- hero
def draw_chopsticks():
    """Two lacquered-wood chopsticks entering from the top-right corner."""
    # Back stick (slightly darker, behind the nigiri).
    thick_line(1010, 30, 640, 330, 15, 7, (122, 76, 34), (96, 58, 26))
    thick_line(1010, 34, 640, 330, 3, 2, (190, 140, 80), (150, 108, 58))
    # Front stick (lighter, in front of the nigiri).
    thick_line(1024, 108, 668, 372, 15, 7, (146, 94, 44), (112, 70, 30))
    thick_line(1024, 112, 668, 372, 3, 2, (210, 158, 92), (168, 122, 66))
    # Decorative gold bands near the top ends.
    for bx, by in [(946, 78), (962, 66)]:
        disc(bx, by, 9, (216, 168, 96), 0.9)
    for bx, by in [(972, 148), (986, 136)]:
        disc(bx, by, 9, (216, 168, 96), 0.9)


def draw_lifted_nigiri():
    """Hero salmon nigiri held high by the chopsticks, tilted, glossy."""
    cx, cy = 622, 348
    # Soft shadow cast on the platter far below.
    ellipse(600, 560, 120, 26, (20, 10, 5), (20, 10, 5), alpha=0.30)
    # Rice mound, tilted by shear.
    rice_mound(cx, cy + 26, 96, 36, shear=0.35)
    # Salmon draped over, tilted the same way.
    salmon_slice(cx + 4, cy - 2, 100, 40, shear=0.35)
    # Extra wet gloss on the hero piece: broad highlight + beads.
    ellipse(cx - 22, cy - 26, 46, 14, (255, 244, 224), (255, 244, 224),
            alpha=0.45, shear=0.35)
    disc(cx - 46, cy - 30, 6, (255, 255, 255), 0.85)
    disc(cx + 18, cy - 34, 4, (255, 255, 255), 0.7)
    # A bead of soy clinging to the lower edge.
    sphere(cx + 52, cy + 30, 9, (120, 64, 32), (74, 38, 18), (34, 16, 8),
           spec_a=0.8)


def draw_soy_drip():
    """Thin glossy soy drip falling from the lifted nigiri to the platter."""
    # The strand: dark, glossy, slightly wavy.
    for s in range(120):
        t = s / 120.0
        y = 392 + s
        x = 668 + int(4 * math.sin(s / 18.0))
        w = 5.0 - 2.0 * t
        disc(x, y, w, (58, 28, 12), 0.95)
        disc(x - 1, y, max(1.0, w * 0.35), (150, 96, 50), 0.5)
    # Droplet swelling at the bottom of the strand.
    sphere(668, 516, 11, (120, 64, 32), (74, 38, 18), (30, 14, 6))
    # Splash mark where a previous drop landed on the lacquer.
    ellipse(668, 552, 26, 7, (74, 38, 18), (74, 38, 18), alpha=0.8)
    ellipse(660, 550, 10, 3, (150, 96, 50), (150, 96, 50), alpha=0.5)


def draw_garnish():
    """Scallion rings, sesame seeds, shiso and avocado accents."""
    # Scallion rings scattered on the platter.
    for _ in range(14):
        sx = RNG.randint(150, 880)
        sy = RNG.randint(500, 930)
        if 480 < sy < 560 and 500 < sx < 740:
            continue  # keep the hero shadow area clean
        disc(sx, sy, 7, (52, 130, 52), 0.95)
        disc(sx, sy, 4, (190, 220, 130), 0.95)
        disc(sx, sy, 2, (60, 90, 40), 0.9)
    # Sesame seeds: tiny toasted ovals.
    for _ in range(60):
        sx = RNG.randint(140, 890)
        sy = RNG.randint(500, 935)
        sh = RNG.uniform(-10, 20)
        ellipse(sx, sy, 4, 2.4, (240 + sh, 214 + sh, 170 + sh),
                (214 + sh, 186 + sh, 140 + sh), alpha=0.9,
                shear=RNG.uniform(-0.6, 0.6))
    # Avocado fan: vertical stack of slices along the right edge.
    for k in range(4):
        ax = 888
        ay = 606 + k * 20
        ellipse(ax, ay, 15, 30, (168, 200, 96), (110, 150, 58),
                alpha=0.95, shear=0.15)
        ellipse(ax - 2, ay - 4, 9, 20, (200, 226, 140), (200, 226, 140),
                alpha=0.5, shear=0.15)


def draw_vignette():
    """Warm vignette: darken + warm the corners, lift the centre."""
    for y in range(H):
        for x in range(W):
            dx = (x - 512) / 512.0
            dy = (y - 470) / 540.0
            d2 = dx * dx + dy * dy
            if d2 > 0.55:
                a = min(0.32, (d2 - 0.55) * 0.45)
                blend(x, y, 40, 18, 6, a)


def main():
    draw_background()
    draw_platter()
    # Back row: tuna, salmon, tuna — slightly softer, behind the front row.
    nigiri(300, 600, "tuna", shear=-0.15, scale=0.92)
    nigiri(512, 588, "salmon", shear=0.05, scale=0.95)
    nigiri(724, 600, "tuna", shear=0.18, scale=0.92)
    draw_gunkan(258, 742, scale=1.0)
    draw_wasabi(830, 772, scale=0.95)
    draw_ginger(884, 862, scale=0.9)
    draw_soy_dish(838, 512, scale=0.95)
    # Front row: salmon, tuna, salmon — the money row.
    nigiri(330, 830, "salmon", shear=-0.12, scale=1.0)
    nigiri(540, 848, "tuna", shear=0.08, scale=1.02)
    nigiri(748, 830, "salmon", shear=0.15, scale=1.0)
    draw_garnish()
    draw_soy_drip()
    draw_lifted_nigiri()
    draw_chopsticks()
    draw_vignette()
    n = write_png(OUT)
    digest = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    print(f"wrote {OUT}: {W}x{H}, {n} bytes, sha256={digest}")


if __name__ == "__main__":
    main()
