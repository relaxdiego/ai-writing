# tug

One-way directory sync to S3-compatible object storage.

`tug` pushes the contents of a local directory to a remote bucket. It skips files whose size and modification time already match the remote object, so repeated runs only transfer what changed.

It does not pull, does not merge, and does not delete. Local is the source of truth; the bucket is a copy.

## Install

With Go:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary from the [releases page](https://github.com/example/tug/releases) and put it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64 -o tug
chmod +x tug
sudo mv tug /usr/local/bin/
```

## Quick start

```
$ tug push ./site s3://my-bucket/site
uploaded  index.html          4.2 KiB
uploaded  css/main.css        11.8 KiB
skipped   img/logo.png        (unchanged)
3 files, 1 skipped, 16.0 KiB uploaded
```

Check first if you'd rather not find out afterwards:

```
$ tug push ./site s3://my-bucket/site --dry-run
would upload  index.html
would upload  css/main.css
```

## Commands

### `tug push <local-dir> <s3-url>`

Walks the local directory and uploads every file whose size or mtime differs from the corresponding remote object. Files that match on both are skipped without being read.

| Flag | Description |
| --- | --- |
| `--dry-run` | Print what would be uploaded, change nothing. |
| `--concurrency N` | Parallel uploads (default 8). |
| `--verbose` | Log skipped files as well as uploaded ones. |

### `tug status <local-dir> <s3-url>`

Reports what a push would do, without doing it and without the per-file upload log. Useful in scripts:

```
$ tug status ./site s3://my-bucket/site
2 files to upload (16.0 KiB)
1 file unchanged
```

Exits `0` if everything is in sync, `1` if a push would transfer anything.

### `tug verify <local-dir> <s3-url>`

Compares local file checksums against remote ETags instead of trusting size and mtime. Slower, but catches corrupted or truncated uploads that a metadata comparison misses.

```
$ tug verify ./site s3://my-bucket/site
ok        index.html
MISMATCH  css/main.css   local 9f86d081… remote 2c624232…
1 mismatch of 3 objects
```

Exits nonzero if any object mismatches or is missing.

## Credentials

`tug` looks for credentials in this order:

1. `~/.tug/credentials`
2. Environment variables

The credentials file is INI-style, with an optional `[default]` profile:

```ini
[default]
access_key_id     = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint          = https://s3.us-east-1.amazonaws.com
region            = us-east-1
```

Select another profile with `--profile <name>` or `TUG_PROFILE`.

The equivalent environment variables:

```
TUG_ACCESS_KEY_ID
TUG_SECRET_ACCESS_KEY
TUG_ENDPOINT
TUG_REGION
```

Any S3-compatible endpoint works — AWS S3, MinIO, Backblaze B2, Cloudflare R2, Ceph.

## Ignoring files

If a `.tugignore` file exists at the root of the local directory, `tug` reads it and skips matching paths. The syntax is gitignore syntax — the same patterns, the same precedence, the same `!` negation.

```
# build artefacts
dist/
*.log

# but keep this one
!dist/manifest.json

.DS_Store
```

Only the root `.tugignore` is read; nested ones are ignored. `.tugignore` itself is never uploaded.

## Limitations

These are real and current, not oversights waiting on a redesign:

- **No delete propagation.** Removing a file locally does not remove it from the bucket. The remote accumulates everything you have ever pushed, and you will need to prune it by hand or with another tool.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit and will fail. Split them or use a different tool for those objects.
- **`verify` is slow on large buckets.** It fetches every object's ETag individually, so runtime grows linearly with object count and is dominated by round-trips. On a bucket with tens of thousands of objects, expect minutes. Prefer `tug status` for routine checks and save `verify` for when you actually suspect corruption.
- **mtime-based skipping can be fooled.** A file edited in place with its mtime preserved will not be re-uploaded by `push`. `verify` will catch it.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success; for `status`, everything in sync |
| `1` | Work pending (`status`) or mismatch found (`verify`) |
| `2` | Configuration or credential error |
| `3` | Transfer error |

## License

MIT.