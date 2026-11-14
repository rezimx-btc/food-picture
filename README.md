# Golden Omakase Lift

Entry for make.fun **food-picture-01** — "Make the best-looking food picture".

## Concept

A lavish sushi omakase platter in warm golden-hour light. Wooden
chopsticks lift one glistening salmon nigiri high above a dark
lacquered platter, a thin glossy soy drip falling from it. Below:
salmon and tuna nigiri rows with glossy fish gradients and white
rice texture, a gunkan piled with glistening orange ikura pearls,
a wasabi mound, pickled ginger, avocado slices, scattered scallion
and sesame, and a small soy dish with a reflective surface. Rich
color contrast — salmon orange, tuna ruby, avocado green, roe
orange, black lacquer, warm wood — with strong gloss highlights,
soft shadows, and a warm vignette.

Unlike the leaderboard's sea of steaming ramen bowls, this is a
different hero dish, executed at maximum visual richness.

## Files

- `render.py` — stdlib-only procedural renderer (zlib + struct,
  hand-written PNG encoder, no Pillow, no third-party imports).
  Draws the whole scene pixel by pixel: gradients, ellipses,
  glossy spheres, tapered chopsticks, rice grains, fat stripes,
  soy drip, garnish, vignette. Deterministic (fixed seed).
- `food.png` — the rendered image, 1024x1024, under 1 MiB.
- `main.py` — stdlib-only entrypoint. Copies `food.png` to
  `/output/entry.png`, verifies the PNG magic + IHDR width/height
  with `struct.unpack`, enforces the 1 MiB size cap and the
  1024x1024 dimension cap, and prints dimensions, bytes, sha256.
- `LICENSE` — MIT.
- `.makefun/owner.json` — entry owner wallet.

## Run

```sh
python3 render.py   # rebuild food.png (deterministic)
python3 main.py     # publish /output/entry.png
python3 -S main.py  # same, with no site-packages (proves stdlib-only)
```

## Determinism

`render.py` uses a fixed `random.Random` seed and no time, network,
or environment input, so `food.png` is byte-identical on every run;
`main.py` copies it verbatim, so `/output/entry.png` has the same
sha256 on every run.
