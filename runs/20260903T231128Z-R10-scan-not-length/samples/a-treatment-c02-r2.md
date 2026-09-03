Those photos carry an EXIF `Orientation` tag, and something between the upload and the pixels you serve is discarding the tag without first applying it.

A phone's camera sensor is fixed relative to the body, so turning the phone does not turn the sensor. The JPEG stores the image in sensor order, which for a portrait-held shot means rotated ninety degrees, and records a small integer saying how a viewer should turn it before display. The phone's gallery honours that integer, Preview and Finder honour it, and a browser honours it for a plain `<img>`. The file is correct in every one of those places because each reader applies the tag. That is also why re-uploading changes nothing: the tag is a property of the file, not of the request, so the same file takes the same wrong path every time. And only some photos are affected because a photo taken with the phone held in the camera's native landscape grip gets orientation 1, passes through your pipeline unrotated, and looks fine.

The break is almost certainly your resize or re-encode step. A decoder hands back pixels in sensor order; an encoder writes no orientation tag unless told to, and an explicit metadata strip (often added for privacy or file size) removes it outright. The derivative you store then has neither the rotation baked into its pixels nor the tag that would have told a viewer to rotate. Two display paths can cause the same symptom even without re-encoding, and are worth ruling out if you serve originals untouched: a CSS `background-image`, and anything drawn through `canvas.drawImage`. Neither applies the tag the way `<img>` does.

The fix is to normalise at upload time: rotate the pixels, then reset the tag so nobody rotates them a second time. Order matters, because auto-orient has to happen before the resize and before any strip.

```
magick input.jpg -auto-orient -resize 2048x2048\> -strip output.jpg
```

The equivalents in other stacks are one call each. In sharp, `.rotate()` with no arguments reads the tag and applies it. In Pillow, `ImageOps.exif_transpose(im)`. In libvips, `autorot`. All of them handle the reset correctly, which matters more than it sounds: if you bake the rotation in and leave the original tag at 6, every viewer that honours EXIF will turn the image again and you have moved the bug rather than fixed it.

If you are writing the transform by hand instead, handle all eight values. Code that special-cases only 3, 6 and 8 is common and quietly wrong on the mirrored cases, which show up from front-facing cameras and from some editors.

| Value | Transform to apply |
|---|---|
| 1 | none |
| 2 | flip horizontal |
| 3 | rotate 180 |
| 4 | flip vertical |
| 5 | transpose (flip horizontal, then rotate 270 clockwise) |
| 6 | rotate 90 clockwise |
| 7 | transverse (flip horizontal, then rotate 90 clockwise) |
| 8 | rotate 270 clockwise |

For the photos already stored wrong, whether you can repair them depends on what you kept. If you still hold the untouched original upload, read its tag and regenerate the derivatives through the corrected pipeline. If your pipeline stripped metadata on the way in and the original is gone, the rotation is unrecoverable from the pixels alone and the only honest options are to leave those images as they are or to offer users a rotate control. That control is worth having regardless, since scanned images and screenshots arrive with no orientation tag at all and can still be wrong.

Two smaller things to check while you are in there. HEIC uploads from iPhones carry orientation in a different container field, so confirm your converter carries it across rather than assuming the JPEG path covers it. And if client-side resizing happens before the file is sent, the canvas there needs `createImageBitmap(file, { imageOrientation: 'from-image' })`, or you will strip the rotation before your server ever sees it.