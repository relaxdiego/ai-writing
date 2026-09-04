Almost certainly EXIF orientation: the camera wrote the pixels in the sensor's native landscape order and recorded a separate "rotate this by 90°" tag, and something in your upload pipeline is dropping or ignoring that tag.

That explains every part of the pattern you describe. The phone's gallery and your laptop's image viewer both read the tag and rotate on display, so the file looks correct everywhere except your site. Only some photos are affected, because a photo taken with the phone held in its native orientation gets Orientation=1 and needs no correction, while the ones held sideways or upside down get 3, 6 or 8. And the result is stable across re-uploads because nothing here is racy or random: the same tag on the same file goes through the same code path and produces the same wrong pixels.

There are two distinct failure modes and they need different fixes, so find out which one you have before changing anything. Take a photo that renders sideways, and run `exiftool -Orientation -ImageWidth -ImageHeight` on both the original file from the phone and the exact derivative your site serves:

- The original has Orientation 6 (or 3, or 8) and the served file has Orientation 1 or no tag at all, with the pixels still unrotated. Your resize or metadata-stripping step discarded the tag without applying it. This is the common case, and it is especially common when the strip was added deliberately to remove GPS coordinates: the same operation that drops location also drops orientation.
- Both files carry the same non-1 tag. Then the pixels are fine and something on the display side is ignoring the tag. Modern browsers honour it in `<img>` by default, so suspect a `image-orientation: none` in your CSS, or a client-side resize that drew the image into a `<canvas>`, which reads raw pixels and knows nothing about EXIF.

The fix in either case is to normalise once at ingest rather than to preserve the tag and hope every consumer respects it. Bake the rotation into the pixels, then strip metadata, then generate derivatives. Every mainstream library has a one-call auto-orient:

```python
# Pillow
from PIL import Image, ImageOps
img = ImageOps.exif_transpose(Image.open(upload))   # applies tag, clears it
```

```js
// sharp — .rotate() with no argument means "honour EXIF"
await sharp(buffer).rotate().resize(1600).toFile(out)
```

```
# ImageMagick
magick input.jpg -auto-orient -resize 1600x out.jpg
```

Order matters more than it looks. Auto-orient has to run before any resize or crop, or you will crop the wrong region of a sideways image, and before the metadata strip, or you are back where you started. Use the library's auto-orient rather than hand-writing `if orientation == 6: rotate(270)`, because four of the eight values (2, 4, 5, 7) include a mirror flip, and a rotation-only mapping silently produces mirrored people and backwards text on those.

Two things to check downstream once the pipeline is fixed. Width and height swap for the 90° cases, so if you record dimensions at upload time for aspect-ratio placeholders or layout, record them after orienting or you will trade a rotation bug for a stretched-thumbnail bug. And note that HEIC uploads from iPhones carry the same tag, so whatever converts HEIC to JPEG needs the same treatment.

Existing bad images are only repairable if you kept the originals with metadata intact. If you did, re-run them through the corrected pipeline. If your ingest already stripped EXIF from the stored master, the orientation information is gone and no amount of processing will recover it; those images need either manual rotation or a re-upload.