The photos carry an EXIF `Orientation` tag, and something in your upload pipeline is discarding it instead of applying it.

Phone cameras don't rotate pixels when you turn the phone. The sensor always writes rows in the same physical order, and the camera records how the phone was held as a number from 1 to 8 in the file's EXIF metadata. The phone's gallery and your laptop's image viewer read that number and rotate at display time, so the photo looks right. Your site shows the raw pixel order, which for a photo taken in portrait or upside-down landscape is rotated 90, 180 or 270 degrees from what the photographer saw. Only some photos are affected because only some were taken with the phone held away from its default orientation: those files have `Orientation: 1` and need no correction. And it reproduces exactly on re-upload because the wrong value is baked into that specific file, not produced by anything random in the request.

The usual culprit is your server-side resize. Browsers have honoured EXIF orientation for `<img>` since around 2019, so if you were serving the untouched original it would probably look correct. What typically happens instead is that a thumbnailer decodes the JPEG, resizes the pixel buffer, and re-encodes without either applying the rotation or copying the EXIF block across. The output is unrotated pixels with no metadata left to tell anyone so, which is unfixable at display time. Client-side resizing through `<canvas>` before upload does the same thing, and so does `image-orientation: none` in CSS if someone added it.

To confirm which, run `exiftool -Orientation -n` against the original upload and against the derivative your page actually loads. An original with orientation 6 or 8 and a derivative with orientation 1 or none at all tells you the resize step is where it's lost.

The fix is to normalise at ingest rather than at display: rotate the pixels to match the tag, then set the tag to 1 or drop EXIF entirely. Every major library has this built in, and the ordering matters in each case, because auto-orient must run before any resize or crop.

| Library | Call | Note |
|---|---|---|
| sharp (Node) | `.rotate()` with no arguments | Must be called before `.resize()` |
| ImageMagick | `-auto-orient` | Place before `-resize` on the command line |
| Pillow (Python) | `ImageOps.exif_transpose(img)` | Returns a new image; apply to the decoded original |
| libvips | `vips_autorot()` | Or `autorotate` on the thumbnail operation |
| Go | `imaging.AutoOrient` | Wrap the decode |

Two details that are easy to miss. Orientation values 5 through 8 involve a quarter turn, so the image's width and height swap; if you store dimensions or compute an aspect ratio from the pre-rotation values, those records will be wrong too and will need recomputing. And orientations 2, 4, 5 and 7 include a mirror flip, not just a rotation, so a hand-rolled "if 6 rotate 90, if 8 rotate 270" branch will silently mishandle photos from front-facing cameras and some scanners. Use the library call rather than writing the table yourself. The eight-image test set at `recurser/exif-orientation-examples` on GitHub is the standard way to check all the cases.

For the photos already uploaded, whether you can repair them depends on what you kept. If you still have the untouched originals, reprocess them through the corrected pipeline and regenerate the derivatives. If you only kept the stripped derivatives, the orientation information is gone and no amount of processing will recover it; you'd have to detect the rotation visually or ask users to re-upload. Worth checking your storage before assuming either way, since some pipelines strip EXIF only from the public thumbnail and leave the original intact.

One thing to keep while you're in there: stripping EXIF is worth doing for its own sake, since these files usually carry GPS coordinates of wherever the photo was taken and you probably don't want to serve that to the public. Just make sure the strip happens after the rotation is applied to the pixels, not before.