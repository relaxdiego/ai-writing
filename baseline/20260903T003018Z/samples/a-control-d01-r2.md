# tug

`tug` pushes a local directory to an S3-compatible bucket. One direction, local → remote, and nothing else: no pull, no sync-back, no surprises about which side wins.

Files whose size and modification time already match the remote object are skipped, so re-running a push over a mostly-unchanged tree costs a listing and little else.

## Install

With Go 1.21 or newer:

```
go install github.com/yourorg/tug@latest
```

Or grab a prebuilt binary from the [releases page](https://github.com/yourorg/tug/releases), and put it somewhere on your `PATH`:

```
curl -L https://github.com/yourorg/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

```
$ tug status ./site s3://my-bucket/site
  4 files to upload    (1.2 MB)
  1 file changed       (18 KB)
138 files unchanged

$ tug push ./site s3://my-bucket/site --dry-run
would upload  css/main.css
would upload  img/header.png
...

$ tug push ./site s3://my-bucket/site
uploaded 5 files (1.2 MB) in 3.1s
```

## Commands

### `tug push <local-dir> <s3-url>`

Uploads everything under `<local-dir>` that isn't already on the remote. A file is considered already uploaded when its size **and** modification time match the corresponding object. Anything else gets sent.

| Flag | Description |
|---|---|
| `--dry-run` | Print what would be uploaded and exit without writing anything. |
| `--concurrency N` | Number of parallel uploads (default 8). |
| `--endpoint URL` | S3-compatible endpoint. Overrides config and environment. |

### `tug status <local-dir> <s3-url>`

Compares the local tree against the remote and prints a summary — new, changed, unchanged — without transferring anything. Uses the same size-and-mtime comparison as `push`, so its output is exactly what a `push` would do.

### `tug verify <local-dir> <s3-url>`

Compares checksums instead of mtimes. Fetches each remote object's ETag and checks it against the local file's MD5, which catches corruption, truncated uploads, and files that were modified without their mtime changing.

This is the honest check, and it is much slower than `status`. See [Limitations](#limitations).

## Credentials

`tug` looks for credentials in this order:

1. Environment variables
2. `~/.tug/credentials`

The environment variables are the usual S3 ones:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_REGION
AWS_ENDPOINT_URL
```

The credentials file is INI-formatted and supports named profiles, selected with `--profile` (or `default` if unset):

```ini
[default]
access_key_id     = AKIAEXAMPLE
secret_access_key = wJalrEXAMPLEKEY
region            = us-east-1
endpoint          = https://s3.example.com
```

Keep it at mode `0600`; `tug` will refuse to read a world-readable credentials file.

## Ignoring files

Drop a `.tugignore` in the root of the directory you're pushing. It uses gitignore syntax — glob patterns, `!` negation, trailing `/` for directories, `#` for comments:

```
# build artifacts
node_modules/
*.log
.DS_Store

# ...but keep this one
!important.log
```

Only the root `.tugignore` is read; nested ones in subdirectories are ignored.

## Limitations

These are known and intentional-for-now, not bugs:

- **No delete propagation.** Deleting a local file does not delete the remote object. The bucket only ever grows. If you need the remote to mirror deletions, you'll have to prune it yourself.
- **No multipart upload.** Files larger than 5 GB will fail, since that's the single-request limit for S3 `PutObject`.
- **`verify` is slow on large buckets.** It fetches every object's ETag, one request per object. On a bucket with tens of thousands of objects this takes minutes, and it makes a lot of API calls. Use `status` for routine checks and save `verify` for when you actually suspect something is wrong.

## License

MIT.

---

A few details were invented to make the README concrete: the module path, release URL, flag names beyond `--dry-run`, the `[default]` profile format, and the license. Swap in your real values.