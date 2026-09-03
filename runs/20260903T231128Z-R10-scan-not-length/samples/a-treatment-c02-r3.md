Those photos carry an EXIF `Orientation` tag, and something in your upload pipeline is dropping the tag without applying the rotation it describes.

A phone camera sensor has a fixed relationship to the body of the phone, so the pixels it writes out are always in the same physical orientation no matter how the person was holding it. Rather than rotating several megapixels of data at capture time, the camera records how the phone was held as a small tag in the file header: value 1 for upright, 6 for rotated 90° clockwise, 3 for upside down, and so on. The phone's gallery reads that tag and rotates on display, and so does Preview or the Photos app on your laptop, which is why the file looks correct everywhere you have checked it. The pixel data underneath was sideways the whole time.

This also explains the two things that look odd about the symptom. It is deterministic because the orientation is a fixed property of the file, not of the upload; the same bytes go in and the same wrong result comes out. And it affects only some photos because a landscape shot taken with the phone held in its natural orientation gets tag value 1, needs no correction, and survives any pipeline unharmed. Only the photos shot in portrait, or upside down, or in the other landscape direction, depend on the tag being honoured.

The place it usually breaks is your server-side derivative generation. A resize step in ImageMagick, libvips, Pillow or sharp decodes the file to a raw pixel buffer, scales it, and re-encodes. The raw buffer has no metadata attached, so unless you explicitly ask for auto-rotation the output is the sideways pixels with the tag now gone, and no downstream viewer can rescue it. The other common culprit is client-side downscaling in a `<canvas>` before upload: `drawImage` ignores orientation, so the canvas bakes in the wrong rotation before the file ever reaches you. Modern browsers do honour the tag when rendering an `<img>` directly, so if your originals display correctly but your thumbnails do not, the resize step is where to look first.

The fix is to normalise at ingest: apply the rotation to the actual pixels as the first operation, then reset or strip the tag so nothing rotates a second time. Each toolchain has a one-call idiom for this.

| Toolchain | Call | Gotcha |
|---|---|---|
| libvips / sharp | `sharp(input).rotate()` with no arguments | `.rotate(90)` does something different; the argless form reads EXIF |
| ImageMagick | `-auto-orient` | Must come before `-strip` and before the resize, or you strip the tag you were about to read |
| Pillow | `ImageOps.exif_transpose(img)` | Returns a new image; the tag is not applied in place by `Image.open` |
| Browser canvas | `createImageBitmap(file, {imageOrientation: 'from-image'})` | Plain `drawImage` from an `<img>` ignores orientation entirely |

Resist the temptation to hand-roll this by mapping the tag to a rotation angle. Four of the eight values (2, 4, 5 and 7) include a mirror flip, and a rotation-only implementation silently produces mirrored images for those. They are rare in phone camera output but common in scanned and edited files, and a mirrored photo is a subtler bug to notice than a sideways one.

For the images already stored, whether you can repair them depends on what you kept. If you still have the originals, re-derive the thumbnails through the corrected pipeline and the problem resolves itself. If the pipeline overwrote the originals with stripped, unrotated pixels, the orientation information is genuinely gone and no automated pass can recover it; you would have to detect the affected assets by upload date, then either accept them or offer the affected users a re-upload.

To verify the fix, use the standard set of eight test JPEGs covering every orientation value, one per tag. Run them through your full path from upload to rendered thumbnail and confirm all eight come out upright and unmirrored. HEIC files from iPhones carry the same tag and deserve a pass through the same test, since some decoders handle their orientation differently from JPEG.