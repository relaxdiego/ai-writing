# tug

One-way directory sync to S3-compatible object storage.

`tug` pushes the contents of a local directory to a remote bucket. It compares file size and modification time against the remote object and skips anything that already matches, so repeat runs only transfer what changed.

It is deliberately one-directional: `tug` never writes to your local disk and never pulls from the remote.

## Install

With Go 1.21 or later:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the [releases page](https://github.com/example/tug/releases) and put it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

```
$ tug status ./site s3://my-bucket/site
  3 new, 1 changed, 128 unchanged

$ tug push ./site s3://my-bucket/site --dry-run
  would upload  index.html         (4.1 KiB)
  would upload  css/main.css       (912 B)
  would upload  img/hero.jpg       (1.2 MiB)
  would upload  about.html         (2.8 KiB, changed)

$ tug push ./site s3://my-bucket/site
  uploaded 4 files (1.2 MiB) in 2.4s
```

## Commands

### `tug push <local-dir> <s3-url>`

Uploads every file under `<local-dir>` whose size or mtime differs from the corresponding remote object. Files that match on both are skipped without being read.

```
tug push ./site s3://my-bucket/site
tug push ./site s3://my-bucket/site --dry-run
```

Flags:

| Flag | Description |
|---|---|
| `--dry-run` | Print what would be uploaded and exit without transferring anything. |
| `--concurrency <n>` | Number of parallel uploads (default 8). |
| `--endpoint <url>` | Override the S3 endpoint, for MinIO, R2, Backblaze B2, etc. |
| `--region <name>` | Bucket region (default `us-east-1`). |
| `--profile <name>` | Credentials profile to use from `~/.tug/credentials`. |

### `tug status <local-dir> <s3-url>`

Reports what a push would do, without uploading. Same comparison as `push` (size and mtime), just summarised. Useful in scripts — exits `0` if everything is in sync, `1` if there is work to do.

### `tug verify <local-dir> <s3-url>`

Compares local files against remote objects by **checksum** rather than size and mtime. Slower, but catches truncated uploads, silent corruption, and files whose mtime was touched without the contents changing.

```
tug verify ./site s3://my-bucket/site
```

Exits `0` if every local file matches its remote checksum, `1` otherwise. Run this after a large migration or when you suspect an interrupted push left something half-written.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[staging]
access_key_id = AKIASTAGING
secret_access_key = ...
endpoint = https://s3.eu-central-1.wasabisys.com
```

Select a non-default section with `--profile staging`.

Environment variables take precedence over the file:

- `TUG_ACCESS_KEY_ID`
- `TUG_SECRET_ACCESS_KEY`
- `TUG_ENDPOINT`
- `TUG_REGION`

Make sure the credentials file is not world-readable:

```
chmod 600 ~/.tug/credentials
```

## Ignoring files

If a `.tugignore` file exists in the root of the local directory, `tug` reads it and excludes matching paths from all three commands. It uses gitignore syntax — glob patterns, `!` negation, `/` anchoring, and `#` comments all behave as you would expect:

```
# build artefacts
node_modules/
dist/
*.log

# but keep the changelog
!CHANGELOG.log

# only at the root
/tmp
```

Ignored files are not uploaded and are not counted by `status` or `verify`.

## Limitations

These are known and intentional-for-now. Read them before trusting `tug` with something important.

- **No delete propagation.** Deleting a local file does not delete the remote object. The remote is append-and-overwrite only; stale objects accumulate until you remove them by hand.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit for S3 PUT and will fail. Split them or use another tool for those objects.
- **`verify` is slow on large buckets.** It fetches every object's ETag individually, which means one request per object. On a bucket with hundreds of thousands of objects this takes a long time and generates a correspondingly large number of API calls. Prefer `status` for routine checks and save `verify` for when you actually need checksum-level confidence.

A further caveat on mtime-based comparison: if a file's contents change but its size and mtime do not, `push` will skip it. This is rare in practice but possible with tools that preserve timestamps. `tug verify` will catch it.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success; for `status` and `verify`, everything is in sync. |
| `1` | Differences found (`status`, `verify`) or a transfer failed (`push`). |
| `2` | Configuration error — bad credentials, unreachable endpoint, malformed arguments. |

## License

MIT.