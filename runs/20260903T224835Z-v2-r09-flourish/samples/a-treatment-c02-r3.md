Almost certainly EXIF orientation: the pixels in those files really are sideways, and a metadata tag tells viewers how far to rotate them. Something in your upload pipeline is discarding that tag without applying it.

Phone cameras have a fixed sensor, so the image always comes off it in the same physical orientation regardless of how the handset was held. Rather than rotate megabytes of pixel data, the camera records an `Orientation` value (one of eight, covering three rotations and their mirrored variants) in the EXIF block. The phone's gallery honours it, Preview and Photos on your laptop honour it, and a current browser honours it too when it renders the original file. Your server does not, which is the asymmetry you are seeing: every viewer you have checked is reading the tag, and the thing that breaks the image is downstream of them.

That also explains the two details you noticed. It is not every photo because a picture taken with the phone held in its "natural" orientation gets `Orientation: 1`, which needs no correction and so survives any pipeline; screenshots and images that have been through an editor often carry no EXIF at all. And the result is identical on every re-upload because nothing here is timing-dependent. The same tag is dropped the same way each time.

The usual culprit is a resize or re-encode step. Libraries such as ImageMagick, sharp and Pillow read the source pixels as-is, write out a derivative that has no EXIF block, and leave the rotation unapplied. Drawing an image to a `<canvas>` does the same thing. So the original may well display correctly in the browser while every thumbnail and web-sized variant you generate from it comes out sideways.

The fix is to normalise at ingest, before any other processing: apply the orientation to the actual pixels, then write the tag out as `1` or strip metadata entirely. Use the library's auto-orient helper rather than rotating by an angle yourself, because four of the eight values involve a mirror flip that a plain rotation will not reproduce.

- sharp: `sharp(input).rotate()` with no argument
- Pillow: `ImageOps.exif_transpose(img)`
- ImageMagick: `-auto-orient`, placed before `-resize`

Stripping the rest of the EXIF at the same time is worth doing on its own account, since it commonly carries GPS coordinates you probably do not want to serve publicly.

For the photos already stored wrong, whether you can repair them depends on what you kept. If the untouched originals are still in object storage, regenerate the derivatives from those and the orientation comes back with them. If the pipeline overwrote the originals, the information is gone and no amount of processing will recover it; you will need a manual rotate control in the UI, which is a reasonable thing to offer users anyway.

Before you ship, test against the eight-image orientation fixture set that circulates for exactly this purpose. A pipeline that handles `1`, `3` and `6` while quietly mangling the mirrored cases is the common half-fix.