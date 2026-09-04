Your upload pipeline is almost certainly stripping the EXIF orientation tag without first applying it.

A phone camera sensor is fixed in the body, so when someone shoots in portrait the phone does not rotate the pixels. It writes them out in sensor order and records an `Orientation` tag meaning "rotate this 90° clockwise before display". The gallery app on their phone honours that tag, Preview or Explorer on your laptop honours it, and browsers honour it too when a plain `<img>` points straight at the file. What does not honour it is a decode-and-re-encode step: ImageMagick, Pillow and sharp all hand you a raw pixel buffer in the file's stored order, and writing that buffer back out discards the metadata unless you ask for it to be preserved. What lands in your bucket is a file whose pixels are sideways and which no longer carries the tag saying so. Every viewer downstream then renders it sideways. The repeatability is the tell: the wrongness is a property of the derived file, so re-uploading the same source runs the same transform and produces the same broken output every time.

It is not every photo because most photos have `Orientation` 1 and need no correction. Anything shot with the phone held in its native orientation, every screenshot, anything that has been through an editor that already baked in the rotation, and captures from the many Android devices that rotate at capture time all arrive upright with nothing for you to lose.

Before changing anything, confirm that this is what is happening. Take one photo that displays wrongly, get the original off the phone, and compare it against what you stored:

```
exiftool -Orientation -ImageWidth -ImageHeight original.jpg stored-derivative.jpg
```

If the original reads something like `Rotate 90 CW` and the derivative reads `Horizontal (normal)` or has no orientation tag at all while keeping the original's width and height, your resizer is the culprit. If instead the derivative still carries the tag and still displays wrongly, the problem is on the rendering side and you should look for a `image-orientation: none` rule in your CSS, or for a `<canvas>` in the upload preview path, since canvas drawing ignores orientation unless you pass `{imageOrientation: 'from-image'}` to `createImageBitmap`.

The tag has eight values, and you will want them to hand while reading `exiftool` output:

| Value | Meaning |
|---|---|
| 1 | Normal |
| 2 | Mirrored horizontally |
| 3 | Rotated 180° |
| 4 | Mirrored vertically |
| 5 | Mirrored horizontally, then rotated 90° CCW |
| 6 | Rotated 90° CW |
| 7 | Mirrored horizontally, then rotated 90° CW |
| 8 | Rotated 90° CCW |

The fix is to normalise once, at ingest, before anything else touches the image: apply the transform to the pixels, then set the tag to 1 or drop the metadata entirely. Every library has a one-liner for it, and each of these handles all eight values including the mirrored ones:

```python
# Pillow
from PIL import Image, ImageOps
img = ImageOps.exif_transpose(Image.open(upload))   # returns upright pixels, tag cleared
```

```js
// sharp
await sharp(input).rotate().resize(1600).toFile(out)  // .rotate() with no argument means "auto-orient from EXIF"
```

```
# ImageMagick
magick input.jpg -auto-orient -resize 1600x output.jpg
```

Do this at the top of the pipeline rather than inside each derivative-generating step, so thumbnails, previews and full-size renditions all inherit correct pixels from a single normalisation. The mirrored values matter more than they look: front-camera selfies on some devices land on 2 or 7, and a naive implementation that only handles 3, 6 and 8 will leave those subtly flipped rather than obviously sideways, which is harder to notice and worse to discover late.

That leaves the photos already stored wrong. If you kept the originals, regenerate the derivatives through the corrected pipeline and you are done. If you did not, the information is gone and no amount of processing will recover it, because the stored file is now a perfectly valid upright-looking image of a sideways scene. In that case give users a rotate control on their own photos and let them repair what they care about. A rotate control is worth adding regardless, since scanned images, photos from cameras with a broken orientation sensor, and images shot while lying down will always slip through.

For a regression test, the [exif-orientation-examples](https://github.com/recurser/exif-orientation-examples) set gives you eight fixture images, one per value, each depicting a scene that is unmistakably wrong when handled incorrectly. Running all eight through your ingest path and asserting the output pixels match a known-good reference catches the mirrored cases that a single portrait test photo will not.