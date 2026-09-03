Your upload pipeline is discarding the photo's EXIF orientation tag instead of applying it. Fix it by rotating the pixels themselves at ingest, then writing the orientation back as "normal".

Phone cameras almost never rotate the image data when you turn the handset. The sensor reads out in its fixed orientation and the camera records how the phone was held as a small metadata field, EXIF Orientation, which takes one of eight values covering the three rotations and their mirrored counterparts. Every viewer that understands EXIF, including the phone's own gallery and Preview or Photos on your laptop, reads that field and rotates on the fly, so the file looks correct everywhere you have checked. The pixel buffer underneath was sideways the whole time.

That explains all three of your symptoms. Only some photos are affected because only some were shot with the phone held in a non-default orientation; the rest carry orientation value 1 and need no correction. The result is identical on every re-upload because nothing here is random: the same tag is being dropped the same way each time. And the file looks fine on your laptop because you are opening the original, not the processed copy your site serves.

The culprit is nearly always the resize or re-encode step. ImageMagick's `-strip`, a naive `sharp` resize, and any client-side canvas resize all produce output with the metadata gone and the pixels untouched, which turns a correctly-tagged sideways image into an untagged sideways image. Browsers do honour orientation on `<img>` by default now, so the tag would have saved you if it had survived.

Apply the rotation before anything else touches the image, and do it with a call that handles all eight values rather than a hand-rolled switch on 3, 6 and 8:

- ImageMagick: `convert in.jpg -auto-orient -resize 1600x out.jpg`, with `-auto-orient` before both the resize and any `-strip`
- sharp (Node): `sharp(input).rotate().resize(1600).toBuffer()`, where `.rotate()` with no argument means "use EXIF"
- Pillow (Python): `ImageOps.exif_transpose(img)` immediately after opening
- libvips: `vips_autorot`, or `thumbnail` with `auto_rotate` left on

One consequence worth catching before it bites you: rotating by 90° swaps width and height. If you store dimensions, generate crops, or compute aspect ratios from the raw decode, those values are wrong for exactly the affected photos, and correcting the orientation without recomputing them will produce stretched thumbnails instead of sideways ones.

Existing uploads will stay broken, since the originals may already have been re-encoded without the tag. If you kept the untouched originals, a backfill job over them is straightforward. If you did not, you are left with reprocessing what you have and accepting that the orientation information for those files is gone.