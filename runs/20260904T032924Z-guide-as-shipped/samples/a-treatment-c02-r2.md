The photos carry an EXIF `Orientation` tag, and something in your upload pipeline is dropping that tag without rotating the actual pixels.

Phone cameras don't rotate the image when you turn the phone. The sensor writes pixels in its own fixed order and records how the phone was held as a number from 1 to 8 in the EXIF header. A viewer is expected to read that number and rotate on display, which is why the photo looks right in the phone's gallery and right in Preview or the Photos app on your laptop. Value 1 means "already upright," and that is what you get whenever the phone was held in its native orientation — which is why only some photos are affected. The rest carry 3, 6 or 8, and they depend on a viewer honouring the flag.

The break almost always happens at resize time. Your server generates thumbnails or web-sized derivatives, the imaging library decodes to a raw pixel buffer, resizes, and re-encodes without copying the EXIF block. The derivative now has no orientation flag, so the browser correctly displays it as stored: sideways. The same photo re-uploaded produces the same wrong result because none of this is random — the flag is a fixed property of the file, and your pipeline mishandles it the same way every time. A second, less common variant is client-side: if you draw the image to a `<canvas>` to crop or compress before upload, canvas gives you unoriented pixels too, and the file you send to the server is genuinely rotated wrong. Modern browsers do respect the flag for a plain `<img>`, so if the original renders correctly in an `<img>` tag but your derivative doesn't, the resize step is the culprit.

To confirm before changing anything, compare the original against what you serve:

```
exiftool -n -Orientation -ImageWidth -ImageHeight original.jpg derived.jpg
```

An original with `Orientation: 6` and a derived file with no orientation at all, at the same width and height, is the whole bug in two lines of output.

The fix is to normalise at ingest rather than to preserve the tag downstream. Bake the rotation into the pixels as the first operation after decoding, then write out a file whose orientation is 1 or absent, so every consumer of that image — your resizer, your CDN, an email client, a PDF export — is looking at pixels that are already upright. In practice that is one call:

- **sharp / libvips:** `sharp(input).rotate()` with no argument, before any `.resize()`.
- **ImageMagick:** `convert in.jpg -auto-orient -resize 1200x out.jpg`, with `-auto-orient` ahead of the resize.
- **Pillow:** `img = ImageOps.exif_transpose(img)` immediately after `Image.open`.
- **Go:** `imaging.AutoOrient` from `disintegration/imaging` or its maintained forks.

Order matters in the ImageMagick and Pillow cases: rotating after you resize gives you a correctly oriented image with the wrong aspect ratio, because a 90° rotation swaps width and height. That swap is the thing most likely to break something else downstream. Any width and height you recorded at upload, any aspect ratio you use to reserve layout space, and any crop coordinates stored against the original need to be computed after the rotation, not before. If you cache dimensions in the database, they are wrong today for exactly the affected photos.

For the images already uploaded, whether you can repair them depends on whether you kept the originals. If you did, reprocessing through the corrected pipeline fixes everything, and you can narrow the job to files whose stored orientation was ever 3, 5, 6, 7 or 8. If you only kept the processed derivatives, the flag is gone and there is nothing left in the file that says which way is up; recovering those means either a heuristic like face or horizon detection, which will get some wrong, or asking users to rotate their own photos. That asymmetry is a good argument for retaining originals separately from derivatives if you don't already.