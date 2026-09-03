Almost certainly EXIF orientation: the camera stored the photo in the sensor's native rotation plus a tag saying "turn this 90° right when you display it," and something in your upload pipeline is throwing the tag away while keeping the unrotated pixels.

That explains each part of what you are seeing. A phone held sideways does not usually rotate the pixels it writes to disk; it writes them as the sensor read them and records an Orientation value from 1 to 8 in the EXIF block. The phone's own gallery and your laptop's image viewer both read that value and rotate at display time, so the file looks right in both places. When your server resizes or re-encodes the upload, most image libraries decode to a raw pixel buffer, which has no concept of orientation, and then write out a new file with no EXIF at all. The rotation instruction is gone and the pixels were never turned, so the result is sideways. It is deterministic because it is a property of the file, not of the network or the browser, and it hits only some photos because only photos shot in a rotated grip carry a non-default tag. Screenshots, images already processed by a messaging app, and photos from cameras that bake the rotation into the pixels all arrive with Orientation 1 and pass through unharmed.

Two other places the same loss happens, worth checking if the server is not the culprit. If you resize client-side before upload by drawing into a `<canvas>`, `drawImage` in most browsers gives you the oriented image but the canvas export carries no EXIF, and in older engines it gave you the raw unoriented pixels instead. And if you serve the original file through a CDN or proxy that re-encodes for format conversion, that layer can strip metadata just as readily as your own code.

To confirm before changing anything, compare the tag on the original against the stored copy:

```
exiftool -Orientation -n original.jpg stored.jpg
```

An original reading 6 or 8 next to a stored file reading nothing, or reading 1, is the whole diagnosis.

The fix is to normalize at ingest: rotate the pixels to match the tag, then write the tag as 1 or drop metadata entirely. Every common library has this built in, and the bug is almost always that the one-line call was never made.

| Library | Loses orientation | Honours it |
|---|---|---|
| Pillow | `Image.open(f)` then resize | `ImageOps.exif_transpose(Image.open(f))` first |
| sharp | `sharp(buf).resize(...)` | `sharp(buf).rotate().resize(...)` |
| ImageMagick | `convert in.jpg -resize ...` | `convert in.jpg -auto-orient -resize ...` |
| libvips CLI | `vipsthumbnail in.jpg` | `vipsthumbnail --rotate in.jpg` |
| Go imaging | `imaging.Open(path)` | `imaging.Open(path, imaging.AutoOrientation(true))` |

Note that sharp's `.rotate()` with no argument means "apply EXIF orientation," not "turn 90°," which reads as a no-op and gets deleted by well-meaning cleanup. Baking the rotation in and then stripping EXIF is also the right call for privacy, since the same block usually carries GPS coordinates and a device serial.

Before you backfill the photos already stored wrong, be aware that you may not be able to tell which ones they are. Once the pipeline has stripped the metadata, a sideways file and a correctly oriented file look identical to a program: both say "no orientation tag, display as-is." If you still hold the untouched originals, the backfill is straightforward, since you re-derive every stored copy from the original with the corrected pipeline and the tag is there to tell you what to do. If the originals were discarded, you cannot script the repair reliably. Your options are to guess with a face or horizon detector and accept a wrong-way error rate, or to show users their own photos and let them rotate. Given that, get the ingest fix deployed first so the affected set stops growing, and check your retention policy for originals before you plan the cleanup.