#!/usr/bin/env python3
"""Golden Omakase Lift — entrypoint for make.fun food-picture-01.

Publishes the pre-rendered food.png as the competition entry:
copies it to /output/entry.png after verifying it is a real PNG
with the expected dimensions and size, then prints a short
confirmation (dimensions, bytes, sha256).

Stdlib only. Deterministic: the same input bytes always produce
the same output bytes. Run: python3 main.py
"""

import hashlib
import os
import shutil
import struct
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "food.png")
OUT_DIR = "/output"
OUT = os.path.join(OUT_DIR, "entry.png")

MAX_BYTES = 1 * 1024 * 1024        # 1 MiB size cap
MAX_WIDTH = 1024                   # dimension caps
MAX_HEIGHT = 1024


def read_png_header(path):
    """Return (width, height) from the PNG magic + IHDR, or raise."""
    with open(path, "rb") as f:
        head = f.read(33)
    if len(head) < 33 or head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file (bad magic bytes)")
    length, ctype = struct.unpack(">I4s", head[8:16])
    if ctype != b"IHDR" or length != 13:
        raise ValueError("not a PNG file (missing IHDR chunk)")
    width, height, depth, colour = struct.unpack(">IIBB", head[16:26])
    if depth != 8 or colour != 2:
        raise ValueError(
            f"unexpected PNG format: bit depth {depth}, colour type "
            f"{colour} (expected 8-bit RGB)")
    return width, height


def main():
    if not os.path.isfile(SRC):
        print(f"error: source image not found: {SRC}", file=sys.stderr)
        print("run: python3 render.py", file=sys.stderr)
        return 1

    size = os.path.getsize(SRC)
    if size > MAX_BYTES:
        print(f"error: {SRC} is {size} bytes, over the {MAX_BYTES} cap",
              file=sys.stderr)
        return 1

    width, height = read_png_header(SRC)
    if width > MAX_WIDTH or height > MAX_HEIGHT:
        print(f"error: {width}x{height} exceeds the "
              f"{MAX_WIDTH}x{MAX_HEIGHT} cap", file=sys.stderr)
        return 1

    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.copyfile(SRC, OUT)
    if os.path.getsize(OUT) != size:
        print("error: copied output size does not match the source",
              file=sys.stderr)
        return 1

    data = open(OUT, "rb").read()
    digest = hashlib.sha256(data).hexdigest()
    print(f"entry published: {OUT}")
    print(f"dimensions: {width}x{height}")
    print(f"bytes: {len(data)}")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
