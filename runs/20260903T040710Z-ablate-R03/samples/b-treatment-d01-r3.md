# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the remote is a copy, and nothing on the remote ever comes back down. If you want bidirectional sync or a backup tool that can restore, this is the wrong program.

On each run `tug` walks the local tree, compares every file against the corresponding remote object, and uploads only what differs. The comparison is size and modification time by default, which is cheap enough to run on a large tree without thinking about it, and wrong in the rare case where a file changed without its size or mtime moving. The `verify` command exists for when you need certainty rather than speed.

## Installing

With a Go toolchain:

```
go install github.com/yourorg/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are on the releases page. Download, extract, and put the binary somewhere on your `PATH`:

```
curl -L https://github.com/yourorg/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a non-default profile with `--profile`. The environment overrides the file, so `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION` are the right way to configure `tug` in CI, where writing a credentials file is awkward. The `endpoint` setting is what makes non-AWS providers work: point it at MinIO, Backblaze B2, Cloudflare R2 or anything else speaking the S3 API.

## Commands

```
tug push   [flags] <local-dir> s3://<bucket>/<prefix>
tug status [flags] <local-dir> s3://<bucket>/<prefix>
tug verify [flags] <local-dir> s3://<bucket>/<prefix>
```

`push` uploads every local file whose size or mtime differs from the remote object, and every file with no remote object at all. Files that match are skipped without being read.

`status` performs the same comparison and prints what `push` would do, without contacting the bucket for anything but object metadata. It is the read-only half of `push`.

`verify` ignores mtimes and compares content: it fetches each remote object's ETag and checks it against a locally computed checksum. Use it after a migration, or when you suspect an interrupted upload left a truncated object behind. It reports mismatches but does not fix them; re-run `push` for the affected paths.

The flags that matter across all three:

- `--dry-run` — print the planned actions and exit without uploading. `push --dry-run` and `status` overlap heavily; the difference is that `status` is the command you reach for habitually and `--dry-run` is the safety net you attach to a `push` you were about to run for real.
- `--profile <name>` — credentials profile, default `default`.
- `--concurrency <n>` — parallel uploads, default 8.
- `--verbose` — one line per file considered, not just per file transferred.

## Ignoring files

If a `.tugignore` file exists at the root of the local directory, `tug` reads it as a gitignore-syntax pattern list and skips anything it matches. The usual rules apply: blank lines and `#` comments are ignored, a leading `/` anchors to the sync root, a trailing `/` matches directories only, and `!` negates an earlier pattern.

```
# build artefacts
/dist/
*.tmp

# but keep the manifest
!/dist/manifest.json
```

Ignored files are never uploaded and never counted as missing by `status` or `verify`.

## Example

```
$ tug status ./site s3://my-bucket/site
  upload  index.html          (new)
  upload  css/main.css        (size differs)
    skip  img/logo.png
    skip  img/hero.jpg
2 to upload, 2 unchanged, 1.4 MB

$ tug push ./site s3://my-bucket/site
uploaded index.html      (4.1 kB)
uploaded css/main.css    (18 kB)
2 uploaded, 2 skipped in 0.9s
```

## Limitations

Deletes do not propagate. Removing a file locally leaves the remote object in place, and `status` will not mention it. Cleaning up stale objects is a manual job, so treat the bucket as append-mostly rather than as a mirror.

Files larger than 5 GB fail to upload, because `tug` does not implement multipart upload and 5 GB is the single-`PUT` ceiling in the S3 API. The error names the file and the size; there is no partial-upload state to clean up afterwards.

`verify` is slow on large buckets. It issues a request per object to read the ETag, so runtime scales with object count rather than with bytes changed, and a bucket with a few hundred thousand objects takes minutes. Raising `--concurrency` helps somewhat. Verifying a subtree by passing a narrower prefix helps more.