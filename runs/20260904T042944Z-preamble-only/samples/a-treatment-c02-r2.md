Almost certainly EXIF orientation: the camera writes the photo in the sensor's native raster order and records how the phone was held in a metadata tag, and something in your upload path is dropping or ignoring that tag.

A phone camera sensor reads out in a fixed orientation regardless of how you hold the device. Rather than rotate the pixels, which costs time and a re-encode, the camera stores the raster as-is and sets an EXIF `Orientation` tag saying "rotate this 90° clockwise when you display it." The phone's gallery reads the tag, and so does Preview or Photos on your laptop, which is why the file looks right everywhere you have checked. Anything that reads the pixel buffer without consulting the tag shows you what the sensor actually recorded, which is the sideways version. Because the tag is baked into the file, the result is perfectly reproducible, which matches the re-upload behaviour you are seeing.

It only affects some photos because a landscape shot held normally gets orientation 1, meaning no transform, and passes through any pipeline unharmed. Portrait shots, upside-down shots, and some screenshots or edited exports carry a non-1 value. Roughly half of a typical camera roll is affected and half is not.

The tag has eight values, and four of them include a mirror, which is the detail that trips up hand-rolled fixes:

| Value | Transform needed to display correctly |
|---|---|
| 1 | none |
| 2 | flip horizontally |
| 3 | rotate 180° |
| 4 | flip vertically |
| 5 | flip horizontally, then rotate 90° counter-clockwise |
| 6 | rotate 90° clockwise |
| 7 | flip horizontally, then rotate 90° clockwise |
| 8 | rotate 90° counter-clockwise |

Phones in practice emit 1, 3, 6 and 8, but a `switch` statement that only handles rotations will silently mirror people's faces on the day some app writes a 5 or a 7. Use a library.

There is a second, nastier variant of this bug that is worth ruling out before you change anything. Modern browsers do honour the tag when rendering an `<img>`, so if you served the uploaded bytes untouched the photos would look right. That means the problem is very likely in your own processing: a resize or thumbnail step that decodes to a raw bitmap, re-encodes without copying EXIF across, and never applies the rotation. The output is a file that is genuinely sideways with no metadata left to say so. That is worse than the original problem, because the correction information is gone rather than merely unread.

The fix is to normalise orientation at ingest, and the ordering matters:

1. As the first step after decode, apply the EXIF transform to the actual pixels and set the tag to 1 or strip EXIF entirely. In sharp, `sharp(input).rotate()` with no argument does exactly this (newer versions spell it `.autoOrient()`). In Pillow, `ImageOps.exif_transpose(img)`. In ImageMagick, `-auto-orient`.
2. Only then resize, crop or generate thumbnails. If you crop first, your crop rectangle is expressed in the sensor's coordinate frame rather than the visual one, and you will cut the wrong part of the image.
3. Store the normalised file as the canonical asset so every downstream consumer, including any native app or email template that does not read EXIF, gets correct pixels.

For the photos already in your bucket, whether you can repair them depends on what your pipeline did to them. If it preserved EXIF and merely ignored it, you can scan for stored files with a non-1 orientation tag and re-run them through the normalising step. If it stripped EXIF while leaving the pixels unrotated, the orientation is unrecoverable from the file alone and an automated backfill is not possible; you would need the originals, if you kept them, or a way for users to rotate their own photos. Check which case you are in before writing the migration, because a backfill that assumes the tag is present will quietly skip every broken file and report success.

Two smaller things to check while you are in there. If any of your CSS sets `image-orientation: none`, remove it, since that explicitly tells the browser to disregard the tag. And if you do any client-side thumbnailing through a canvas, test it specifically: that path has historically been where orientation gets lost, and `createImageBitmap` takes an `imageOrientation` option precisely because of it.