# tug

One-way sync from a local directory to an S3-compatible bucket. `tug` pushes; it never pulls, and it never deletes.

## Install

```
go install github.com/example/tug@latest
```

Or grab a prebuilt binary from the releases page and put it on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug-linux-amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Quick start

```
tug status ./site s3://my-bucket/prod     # what would change
tug push ./site s3://my-bucket/prod       # upload it
```

A file is uploaded only if its size or modification time differs from the remote object. Everything else is skipped, so re-running a push over an unchanged tree costs a listing and nothing more.

## Commands

**`tug push <dir> <bucket-uri>`** — Uploads every local file that doesn't match its remote counterpart. Add `--dry-run` to print the plan without touching the bucket.

**`tug status <dir> <bucket-uri>`** — Prints the same plan `push` would execute, with no upload step. Useful in CI as a change detector.

**`tug verify <dir> <bucket-uri>`** — Compares checksums instead of size and mtime. Slower and more thorough: use it when you suspect a mtime-based comparison has lied to you, such as after restoring files from a backup that reset timestamps.

## Credentials

`tug` reads `~/.tug/credentials`:

```
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Environment variables override the file:

```
TUG_ACCESS_KEY_ID
TUG_SECRET_ACCESS_KEY
TUG_ENDPOINT
TUG_REGION
```

Any S3-compatible endpoint works — AWS, Backblaze B2, Cloudflare R2, MinIO.

## Ignoring files

Drop a `.tugignore` at the root of the directory you're pushing. It uses gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
*.log
node_modules/
.DS_Store
!important.log
```

## Limitations

- **No delete propagation.** Removing a file locally leaves the remote object in place. Deletions are yours to make by hand.
- **No multipart upload.** Files over 5 GB will fail; that's the single-request ceiling on S3.
- **`verify` is slow on large buckets.** It fetches the ETag for every object, one object at a time. On a bucket with hundreds of thousands of keys, expect it to take a while — run `push` for routine work and reach for `verify` when you have a reason to.