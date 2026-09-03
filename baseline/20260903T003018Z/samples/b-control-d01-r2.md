# tug

One-way directory sync to S3-compatible object storage.

`tug` pushes the contents of a local directory to a remote bucket. It skips files whose size and modification time already match the remote object, so repeat runs only transfer what changed.

## Install

With Go:

```sh
go install github.com/example/tug@latest
```

Or download a prebuilt binary from the [releases page](https://github.com/example/tug/releases), then:

```sh
chmod +x tug
sudo mv tug /usr/local/bin/
```

Verify the install:

```sh
tug --version
```

## Quick start

```sh
# See what would be uploaded, without uploading anything
tug push ./site s3://my-bucket/prefix --dry-run

# Do it for real
tug push ./site s3://my-bucket/prefix
```

## Commands

### `tug push <local-dir> <bucket-uri>`

Uploads every local file that differs from its remote counterpart. A file is considered unchanged — and therefore skipped — when its size and mtime both match the remote object's metadata.

```sh
tug push ./site s3://my-bucket/prefix
tug push ./site s3://my-bucket/prefix --dry-run
```

`--dry-run` prints the exact set of uploads that would happen and exits without writing to the bucket. Use it freely; it is the fastest way to sanity-check a new prefix or a new `.tugignore`.

### `tug status <local-dir> <bucket-uri>`

Reports what push would do, without doing it. Files are grouped as new, changed, or up to date. Uses the same size-and-mtime comparison as `push`.

```sh
tug status ./site s3://my-bucket/prefix
```

### `tug verify <local-dir> <bucket-uri>`

Compares checksums instead of mtimes. Use this when you suspect a file was uploaded incorrectly, or when mtimes are unreliable — for example after a checkout, a restore from backup, or a build that rewrites timestamps without changing content.

```sh
tug verify ./site s3://my-bucket/prefix
```

`verify` fetches the ETag of every object in the target prefix, so it is considerably slower than `status` and gets slower as the bucket grows. See [Limitations](#limitations).

## Credentials

`tug` reads credentials from `~/.tug/credentials`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Or from the environment, which takes precedence over the file:

```sh
export TUG_ACCESS_KEY_ID=AKIAEXAMPLE
export TUG_SECRET_ACCESS_KEY=wJalrXUtnFEMI/EXAMPLEKEY
export TUG_ENDPOINT=https://s3.us-east-1.amazonaws.com
export TUG_REGION=us-east-1
```

Any S3-compatible endpoint works — AWS S3, MinIO, Backblaze B2, Cloudflare R2, and others.

## Ignoring files

Place a `.tugignore` file in the root of the directory you are pushing. It uses gitignore syntax:

```gitignore
# build artifacts
node_modules/
dist/
*.log

# but keep this one
!dist/index.html
```

Patterns are matched relative to the directory root. If no `.tugignore` exists, every file in the directory is a candidate for upload.

## Limitations

These are known and intentional for the current version. Read them before relying on `tug` for anything important.

- **No delete propagation.** Deleting a local file does not delete the remote object. The remote bucket only ever grows. If you need the remote to exactly mirror local state, you must remove stale objects yourself.
- **No multipart upload.** Files larger than 5 GB will fail to upload. Split them, or use another tool for those objects.
- **`verify` is slow on large buckets.** It fetches the ETag of every object under the prefix, one listing page at a time. On buckets with many objects this can take a long while. Prefer `status` for routine checks and reach for `verify` only when you have a specific reason to distrust mtimes.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success; for `status` and `verify`, local and remote agree |
| `1` | Differences found (`status`, `verify`) |
| `2` | Configuration or credentials error |
| `3` | Transfer error |

This makes `tug` easy to use in CI:

```sh
tug verify ./site s3://my-bucket/prefix || echo "drift detected"
```

## License

MIT.