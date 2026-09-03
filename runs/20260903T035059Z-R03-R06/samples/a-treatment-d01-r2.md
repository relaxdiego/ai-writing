# tug

`tug` pushes a local directory to an S3-compatible bucket. Synchronisation is one-way: files travel from your machine to the bucket and never the other direction, so a push can create or overwrite remote objects but will never modify, delete, or restore anything on disk. Before uploading, `tug` compares each local file's size and modification time against the matching remote object and skips the ones that agree, so repeated pushes over a large tree cost little beyond the listing.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS, and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo install tug /usr/local/bin/tug
```

## Commands

### `tug push`

`push` walks the local directory, decides which files differ from the bucket, and uploads them. The comparison is size and mtime only, which is fast but assumes that a file whose size and timestamp are unchanged has unchanged contents; if you rewrite a file in place without altering either, `push` will not notice, and `verify` is the command that will.

```
tug push ./site s3://my-bucket/site
tug push ./site s3://my-bucket/site --dry-run
```

With `--dry-run`, `tug` performs the same comparison and prints exactly what it would upload without sending any data, which is the safest way to check a new prefix or a freshly written `.tugignore` before committing to it.

### `tug status`

`status` reports the same comparison `push` makes and then stops. It lists local files that are missing from the bucket and local files whose size or mtime differs from the object, along with a count of how many files were skipped as unchanged and how many were excluded by `.tugignore`. Nothing is uploaded, so it is safe to run against a production bucket at any time.

```
tug status ./site s3://my-bucket/site
```

### `tug verify`

`verify` answers the question `push` cannot: whether the bytes actually match. Instead of trusting size and mtime, it computes the checksum of each local file and compares it against the ETag of the corresponding object, so it catches truncated uploads, in-place edits that preserved the timestamp, and objects that were altered outside `tug`. Read the note under [Limitations](#limitations) before running it against a large bucket.

```
tug verify ./site s3://my-bucket/site
```

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/EXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a profile other than `default` with `--profile`. The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION`; when set, they take precedence over the file, which makes them the usual choice in CI where writing a credentials file is inconvenient. The credentials file should be mode `0600`, and `tug` will refuse to read one that is group- or world-readable.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it as a list of exclusion patterns in gitignore syntax: one pattern per line, `#` for comments, `/` to anchor a pattern to the root, `**` to match across directory boundaries, and a leading `!` to re-include something an earlier pattern excluded.

```
node_modules/
*.log
.DS_Store
/build
!/build/index.html
```

Ignored files are never uploaded and never counted as differences by `status` or `verify`. Adding a pattern for a file that has already been pushed excludes it from future comparisons but leaves the existing object in the bucket.

## Limitations

There is no delete propagation. Removing a file locally has no effect on the bucket: the object remains, and neither `status` nor `verify` will report it, because both walk the local tree and look up the corresponding objects rather than the reverse. Pruning a bucket after a local deletion has to be done with another tool or through the provider's console.

Files larger than 5 GB cannot be uploaded. `tug` issues a single `PutObject` per file and does not implement multipart upload, so a file above the 5 GB single-request limit fails with an error from the server; `push` reports it and continues with the remaining files rather than aborting the run.

`verify` is slow on large buckets. It fetches the ETag of every object it checks, one request per file, so a bucket with hundreds of thousands of objects takes a long time and consumes a request for each one. On buckets of that size, prefer `verify` on a narrow prefix rather than the whole tree, and use `status` for routine checks.