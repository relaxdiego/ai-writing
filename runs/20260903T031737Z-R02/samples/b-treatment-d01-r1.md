# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-directional: files move from your machine to the remote and never the other way, so a mistake on the remote side can never overwrite work in your working copy. Files whose size and modification time already match the corresponding remote object are skipped, which makes repeat runs over a mostly-unchanged tree cheap.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/yourorg/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and put it somewhere on your `PATH`:

```
curl -LO https://github.com/yourorg/tug/releases/latest/download/tug_linux_amd64
chmod +x tug_linux_amd64
sudo mv tug_linux_amd64 /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment if that file is absent or does not define the value it needs. The file is INI-style:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. Because the endpoint is configurable, `tug` works against MinIO, Backblaze B2, Cloudflare R2 and anything else that speaks the S3 API, not just AWS itself. Keep the credentials file at mode `0600`; `tug` will refuse to read it if the permissions are wider than that.

## Commands

### `tug push`

Walks the local directory, compares each file against the remote object of the same key, and uploads anything that is new or whose size or mtime differs.

```
tug push ./site s3://my-bucket/site
tug push --dry-run ./site s3://my-bucket/site
```

`--dry-run` performs the full comparison and prints exactly what would be uploaded without transferring any bytes, which is the right way to check a new ignore rule or a new prefix before committing to it.

### `tug status`

Reports what a push would do without uploading, in a summary form rather than a per-file transcript. Use it to answer "is my remote up to date?" at a glance; use `push --dry-run` when you want the file list.

```
tug status ./site s3://my-bucket/site
```

### `tug verify`

Compares local checksums against remote ETags instead of trusting size and mtime. Since `push` uses a heuristic, a file that was modified in place without changing its length and had its timestamp restored will be silently skipped; `verify` is how you catch that case, along with any corruption that occurred in transit or at rest.

```
tug verify ./site s3://my-bucket/site
```

## Ignoring files

If a `.tugignore` file exists at the root of the local directory, its patterns are applied to the walk. The syntax is gitignore syntax — the same globs, the same directory semantics, the same `!` negation:

```
node_modules/
*.log
.DS_Store
!important.log
```

## Limitations

Deletions are not propagated. Removing a file locally leaves the corresponding object in the bucket, so a long-lived sync target accumulates orphans that you will have to clean up by other means.

Multipart upload is not implemented, which caps individual files at the 5 GB single-`PUT` limit. Anything larger fails with an explicit error rather than a partial upload, but it does fail, so large archives and disk images need a different tool.

`verify` issues a request per object to fetch its ETag and does not parallelise aggressively. On a bucket with tens of thousands of objects this takes minutes and costs a corresponding number of API calls, so it is best run deliberately rather than on every deploy — `push` and `status` only need a single `LIST` and stay fast regardless of bucket size.