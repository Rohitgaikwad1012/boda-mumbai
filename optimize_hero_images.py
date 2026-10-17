"""Shrink the hero photos so the site loads fast.

Run from your project folder (the one that contains app.py):

    pip install pillow
    python optimize_hero_images.py

Reads every image in assets/hero/ and writes a resized WebP copy into
static/hero/ (numbered 01-, 02-, ... so the order matches the existing
.hero-photo-1, .hero-photo-2, ... classes). Your original files are not touched.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageOps

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default="assets/hero")
    parser.add_argument("--out", default="static/hero")
    parser.add_argument("--width", type=int, default=1600, help="max width in px")
    parser.add_argument("--quality", type=int, default=72, help="WebP quality 1-100")
    args = parser.parse_args()

    src, out = Path(args.src), Path(args.out)
    if not src.is_dir():
        raise SystemExit(f"Folder not found: {src} (run this from the folder that contains app.py)")
    out.mkdir(parents=True, exist_ok=True)

    files = [p for p in sorted(src.iterdir()) if p.suffix.lower() in EXTS]
    total_before = total_after = 0
    for i, path in enumerate(files, start=1):
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width > args.width:
                im = im.resize((args.width, round(im.height * args.width / im.width)), Image.LANCZOS)
            target = out / f"{i:02d}-{path.stem.replace(' ', '_')}.webp"
            im.save(target, "WEBP", quality=args.quality, method=6)
        before, after = path.stat().st_size, target.stat().st_size
        total_before += before
        total_after += after
        print(f"{path.name}: {before/1024:.0f} KB -> {after/1024:.0f} KB")

    print(f"\n{len(files)} images: {total_before/1024:.0f} KB -> {total_after/1024:.0f} KB "
          f"({100 - 100*total_after/max(total_before,1):.0f}% smaller)")


if __name__ == "__main__":
    main()