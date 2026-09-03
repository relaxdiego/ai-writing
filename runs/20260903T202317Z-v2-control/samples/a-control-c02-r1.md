## What's happening

Almost certainly **EXIF orientation**.

Phone cameras don't rotate pixels when you turn the phone. The sensor always writes its native landscape pixel grid, and the camera app records *how the phone was held* as a small metadata tag — EXIF `Orientation`, a value from 1 to 8 meaning things like "rotate 90° CW when displaying" or "rotate 180°."

So a portrait photo from a phone is often literally a landscape image plus a note saying "turn me." Anything that reads the note renders it correctly; anything that ignores or discards the note shows you the raw sensor pixels — sideways.

That explains each of your symptoms:

- **Correct on the phone, correct on your laptop** — the phone gallery and Preview/Photos honor the tag.
- **Not every photo** — only ones shot in a non-default rotation get a tag other than 1. Photos taken "the normal way," screenshots, and images that have already been through an editor come out fine.
- **Same wrong result every time** — it's not a race or a flake, it's a fixed property of that file. Same tag in, same wrong pixels out.

## Where the tag gets lost

Two places, and it's worth finding out which one is yours:

**1. Your server-side image processing (most likely).** When you generate thumbnails or resized derivatives, the library decodes to a raw pixel buffer, resizes, and re-encodes. Unless you explicitly ask, the orientation tag is either dropped or copied through incorrectly — and now the pixels are wrong *and* there's no note to fix them. This is the classic version of this bug.

**2. Client-side resizing before upload.** If you shrink images in the browser with a `<canvas>` before uploading, `drawImage` writes raw pixels and canvas output carries no EXIF at all. The user's own preview looks right (the browser honored the tag) but what you receive is pre-broken.

A third, less common cause: browsers have honored EXIF orientation in `<img>` for years now, but a CSS reset containing `image-orientation: none` will switch that off. Worth a grep if the originals display wrong too.

**To confirm in about a minute**, take one bad photo and run:

```bash
exiftool -Orientation -ImageWidth -ImageHeight original.jpg
exiftool -Orientation -ImageWidth -ImageHeight served-thumbnail.jpg
```

If the original says something like `Rotate 90 CW` and the thumbnail says `Horizontal (normal)` with the width and height unswapped, you've found it.

## The fix

**Normalize orientation once, at upload time.** Bake the rotation into the actual pixels, then reset the tag to 1. Every downstream consumer — your app, your CDN, a partner API, an ML pipeline — then gets an image that is what it says it is.

Most libraries have a one-liner:

```js
// sharp (Node) — .rotate() with no args auto-orients from EXIF
await sharp(input).rotate().resize(1200, null, { withoutEnlargement: true }).toFile(out)
```

```python
# Pillow
from PIL import Image, ImageOps
img = ImageOps.exif_transpose(Image.open(input))
```

```bash
# ImageMagick
magick input.jpg -auto-orient -resize 1200x output.jpg
```

Go: `imaging.AutoOrient`. libvips: `autorot`. imgproxy and thumbor both do it by default.

Three things to get right while you're in there:

- **Order matters.** Auto-orient *before* resizing or cropping. If you resize first with hardcoded dimensions, you'll fit the image to the wrong axis.
- **Dimensions swap.** A 4032×3024 file with orientation 6 becomes 3024×4032. If you store width/height in your database, or drive aspect-ratio containers or smart-crop from those numbers, recompute them after the rotation, not before.
- **Don't just strip EXIF.** Stripping metadata without rotating first is strictly worse — it converts a recoverable problem into an unrecoverable one. Rotate, then strip. (And do strip: EXIF from phones carries GPS coordinates you probably don't want to serve publicly.)

## Cleaning up what's already broken

Whether existing bad images are fixable depends on what you kept:

- **If you still have the untouched originals**, this is just a backfill. Re-run derivative generation through the fixed pipeline. Easiest to scope by regenerating everything rather than trying to identify which ones are wrong.
- **If your pipeline overwrote originals with stripped versions**, the orientation information is gone and no amount of processing will recover it. Your options are a heuristic pass (face/horizon detection is decent but not reliable enough to run unsupervised) or letting users fix their own.

Either way, **add a manual rotate button** to the photo UI. It's cheap, it handles the backfill gap, and it covers the residual cases — some camera apps and editors write inconsistent tags, so a small tail of images will be wrong no matter how correct your pipeline is.

## Guarding against regression

Grab the standard EXIF orientation test suite — the eight `Landscape_1.jpg` … `Landscape_8.jpg` / `Portrait_1..8` fixtures, freely available and designed for exactly this. Each is labeled with an arrow so a wrong result is obvious. Run all sixteen through your upload path in CI and assert the output dimensions and a few corner pixels. This bug reappears every time someone swaps an image library or adds a "fast path," so it's worth pinning down.

Also worth checking whether you accept HEIC from iPhones — it uses orientation the same way, and HEIC→JPEG conversion is a separate code path that often needs its own fix.