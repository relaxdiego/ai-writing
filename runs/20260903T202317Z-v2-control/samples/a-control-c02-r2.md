## The cause: EXIF orientation

Phone cameras don't rotate pixels when you turn the phone. The sensor always writes rows in the same physical order, and the camera records *how the phone was held* in a metadata field — the EXIF `Orientation` tag (values 1–8, covering 90°/180°/270° rotations plus mirrored variants).

So a portrait photo is often stored as a landscape pixel buffer plus a note saying "rotate this 90° clockwise before displaying."

- The phone's gallery reads that note. Correct.
- macOS Preview / Windows Photos read that note. Correct.
- Something in your pipeline doesn't. Sideways.

This explains all three of your observations:

- **Not every photo** — only ones shot in a non-default orientation. Photos taken "the right way up," screenshots, images that have passed through WhatsApp/Slack, and most Android photos already have `Orientation=1`, so they're immune.
- **Same wrong result every time** — it's a fixed property of the file's bytes, not a race or a timing bug.
- **Fine locally, wrong on the site** — your viewers honor the tag; your web path doesn't.

## Narrow it down in one step

Download the image *back from your site* and open it in Preview.

- **Still sideways?** Your server-side processing is at fault. This is the common case: a resize/thumbnail step decodes the pixels, strips all metadata (including the orientation tag), and re-encodes — so the "rotate me" note is thrown away while the un-rotated pixels survive.
- **Looks correct?** It's a rendering-side issue. Modern browsers honor EXIF in `<img>` by default, but `image-orientation: none` in CSS disables it, and `canvas.drawImage()` ignores it entirely — so any client-side crop/resize/preview will be wrong.

## The fix: normalize once, at upload

Bake the rotation into the pixels at ingest, then reset the tag so nothing rotates twice. Every major library has a one-liner:

```js
// sharp (Node) — .rotate() with no args applies EXIF orientation
await sharp(input).rotate().toFile(output);
```

```python
# Pillow (Python)
from PIL import Image, ImageOps
img = ImageOps.exif_transpose(Image.open(input))   # returns upright image, tag cleared
```

```bash
# ImageMagick — must come before any resize
magick input.jpg -auto-orient -resize 1600x1600 output.jpg
```

Store the normalized file as your canonical version; derive all thumbnails and variants from it. After that, orientation stops being something the rest of your stack has to think about.

**The one trap:** if you rotate the pixels but leave `Orientation` set to 6, viewers that honor EXIF will rotate *again* and you've made it worse. The calls above handle this, but verify with `exiftool -Orientation output.jpg` — it should read 1 or be absent.

## Also worth doing

- **Backfill.** Existing uploads are already broken and won't fix themselves. Run a job over stored originals: read `Orientation`, and where it isn't 1, re-process and regenerate derived sizes. Guard against running twice on the same file — key off the tag value, not a timestamp.
- **Client-side previews.** If you show a preview before upload, use `createImageBitmap(file, { imageOrientation: 'from-image' })` rather than drawing the raw image to a canvas.
- **HEIC/HEIF.** iPhone's default format uses the same orientation convention. If you transcode HEIC to JPEG, apply orientation in that step too.
- **Video.** The same class of bug exists for video, via a rotation matrix in the MP4 container. If users upload clips, you'll hit it there eventually.

I answered this generally — the repo in this directory looks unrelated to image uploads. If you point me at the actual upload/resize code, I can find the specific line that's dropping the tag.