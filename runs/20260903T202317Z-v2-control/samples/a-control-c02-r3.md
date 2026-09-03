## What's happening

Almost certainly EXIF orientation, and something in your upload pipeline is discarding it.

A phone camera sensor has a fixed physical orientation. When you rotate the phone, the camera doesn't rotate the pixels — it writes them out exactly as the sensor read them and records an EXIF `Orientation` tag saying, in effect, "rotate this 90° clockwise when you display it." There are 8 possible values (1 = as-is, 3 = 180°, 6 = 90° CW, 8 = 270° CW, plus four mirrored variants).

The phone's gallery honors that tag. Preview/Photos on your laptop honors it. Modern browsers honor it too (`image-orientation: from-image` has been the CSS default since ~2020). So the file is fine everywhere *until* something decodes the pixels, re-encodes them without rotating, and drops the metadata — which is exactly what a server-side resize/thumbnail step does by default in ImageMagick, Pillow, and most wrappers. Now you have physically sideways pixels and no tag left to tell anyone.

Your three symptoms all fall out of this:

- **Only some photos** — only shots taken with the phone in an orientation where the tag ≠ 1.
- **Same wrong result every time** — the tag is a property of the file, not of the network or the session.
- **Correct on phone and laptop** — those viewers read the original file, tag intact.

## Confirm it in 30 seconds

```bash
exiftool -Orientation -n original.jpg      # expect 6 or 8 on a "broken" photo
exiftool -Orientation -n stored-copy.jpg   # expect 1 or missing
```

If the original says 6 and your stored derivative says 1 (or has no EXIF at all) while looking sideways, that's the whole bug.

## The fix: normalize once, at ingest

Bake the rotation into the pixels as the first step of processing, *before* any resize or crop, then let the tag be stripped. Don't try to preserve the tag through the pipeline — too many things eat it.

| Stack | Call |
|---|---|
| sharp (Node) | `sharp(buf).rotate()` — no arguments means "auto-orient from EXIF"; must come before `.resize()` |
| libvips CLI | `vips autorot in.jpg out.jpg` (`vipsthumbnail` does it automatically) |
| ImageMagick | `magick in.jpg -auto-orient -strip out.jpg` — `-auto-orient` must precede `-strip` |
| Pillow (Python) | `img = ImageOps.exif_transpose(img)` |
| Intervention (PHP) | `$image->orientate()` |
| imaging (Go) | `imaging.Decode(r, imaging.AutoOrientation(true))` |

Two pitfalls that bite people right after this fix:

1. **Swap the dimensions.** If you record width/height from the pre-rotation metadata, a 4032×3024 landscape-sensor shot that's really portrait will be stored with the wrong aspect ratio, and your layout will still look wrong even though the pixels are now right. Read dimensions *after* auto-orient.
2. **Any client-side resize needs the same treatment.** If you downscale in a canvas before upload, use `createImageBitmap(blob, { imageOrientation: 'from-image' })` rather than assuming the decode is oriented.

While you're at it: auto-orienting and *then* stripping EXIF is also the right privacy move, since these files typically carry GPS coordinates.

## Existing broken images

Once the tag is gone, the file no longer tells you it needs rotating, so there's no reliable automatic backfill.

- **If you kept the originals**, reprocess derivatives from them — clean and complete.
- **If you didn't**, you can't distinguish "sideways" from "deliberately shot that way" programmatically. The practical answer is to ship a small rotate-left/rotate-right control on the user's own photos and let people fix their own. That's worth having permanently anyway, as a safety valve for the cases EXIF gets wrong.

One note on scope: your working directory here looks like a writing repo rather than the site's code, so I've answered this generically. If you point me at the upload/processing code, I can find the exact call that's dropping the orientation and patch it.