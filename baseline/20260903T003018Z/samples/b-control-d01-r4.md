# tug

`tug` pushes a local directory to an S3-compatible bucket. One direction, no surprises: local is the source of truth, remote gets what local has.

It is deliberately not a general-purpose sync tool. There is no pull, no two-way reconciliation, and no delete propagation. If you want those, use `rclone` or `aws s3 sync`.

## Install

With Go 1.21 or newer:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary from the [releases page](https://github.com/example/tug/releases) and drop it somewhere on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

```
$ tug status ./site s3://my-bucket/site
12 files to upload (4.1 MB), 340 unchanged

$ tug push --dry-run ./site s3://my-bucket/site
would upload  index.html          (2.1 KB)
would upload  assets/app.css      (18 KB)
...

$ tug push ./site s3://my-bucket/site
uploaded 12 files (4.1 MB) in 3.2s
```

## Commands

### `tug push <local-dir> <s3-url>`

Uploads everything in `<local-dir>` that differs from the remote. A file is considered unchanged — and therefore skipped — when its size and modification time both match the corresponding remote object. Everything else is uploaded.

```
tug push ./site s3://my-bucket/site
tug push --dry-run ./site s3://my-bucket/site
```

`--dry-run` prints exactly what would be uploaded and exits without touching the bucket. Use it. The output is stable enough to diff between runs.

### `tug status <local-dir> <s3-url>`

Shows what `push` would do, in summary form: how many files are new or changed, how many bytes that adds up to, and how many are being skipped. Read-only.

### `tug verify <local-dir> <s3-url>`

The paranoid version of `status`. Instead of trusting size and mtime, `verify` fetches each remote object's ETag and compares it against a checksum of the local file. This catches the cases mtime-based comparison cannot: truncated uploads, files edited without a timestamp change, bit rot on either end.

It is much slower than `status`. See [Limitations](#limitations).

## Credentials

`tug` looks for credentials in this order:

1. **`~/.tug/credentials`** — an INI file:

   ```ini
   [default]
   access_key_id = AKIAEXAMPLE
   secret_access_key = wJalrEXAMPLEKEY
   endpoint = https://s3.us-west-002.backblazeb2.com
   region = us-west-002
   ```

   Select a non-default profile with `--profile <name>`.

2. **Environment variables** — used when no credentials file is present:

   ```
   AWS_ACCESS_KEY_ID
   AWS_SECRET_ACCESS_KEY
   TUG_ENDPOINT
   TUG_REGION
   ```

The `endpoint` setting is what makes this work with non-AWS providers — Backblaze B2, Cloudflare R2, MinIO, Wasabi, and anything else speaking the S3 API. Omit it for AWS S3 proper.

Keep `~/.tug/credentials` at mode `0600`. `tug` will warn if it is more permissive.

## Ignoring files

Drop a `.tugignore` file in the root of the directory you are pushing. It uses gitignore syntax, including negation and directory patterns:

```
# build artifacts
node_modules/
dist/
*.log

# but keep this one
!dist/manifest.json

.DS_Store
```

Ignored files are never uploaded and never reported as changes. There is no `--force` flag to override the ignore file; edit the file instead.

## Limitations

These are known and intentional, in the sense that they are documented rather than fixed.

**No delete propagation.** Deleting a file locally does not delete it remotely. Over time the bucket accumulates objects with no local counterpart. `tug` will not tell you about them — `status` only reports files that exist locally. If you need the bucket to exactly mirror the directory, you will have to prune it yourself.

**No multipart upload.** Files larger than 5 GB cannot be uploaded, because S3 requires multipart for anything above that threshold and `tug` does not implement it. Such files fail with a clear error and the rest of the push continues.

**`verify` is slow on large buckets.** It issues a request per object to read the ETag, so runtime scales linearly with object count and is dominated by round-trip latency. On a bucket with tens of thousands of objects, expect minutes. Run it on a schedule, not in a tight loop.

**mtime is a heuristic.** The default comparison assumes that a file whose size and mtime match the remote is identical to it. That assumption breaks if a file is modified without its mtime advancing, or if timestamps are rewritten by a build step or a restore from backup. `verify` exists for exactly this reason.

## Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Success; for `status`/`verify`, no differences found |
| `1`  | Differences found (`status`, `verify`) |
| `2`  | Configuration or credentials error |
| `3`  | Transfer error — one or more files failed to upload |

This makes `tug verify` usable as a CI check: a non-zero exit means the bucket does not match the tree.

## License

MIT.