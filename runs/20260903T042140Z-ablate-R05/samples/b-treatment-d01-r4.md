# tug

`tug` pushes a local directory into an S3-compatible bucket. It is deliberately one-way: files move from your machine to the remote and never back, which makes it suitable for publishing build output, backing up a working directory, or keeping a static site in sync without the risk that a remote change overwrites something local.

To decide what needs uploading, `tug` compares each local file's size and modification time against the corresponding remote object and skips anything that matches. This keeps repeat pushes cheap, since an unchanged tree costs one listing request rather than a full re-upload.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS, and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo mv tug /usr/local/bin/
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment. The file is INI-style and may hold several profiles:

```ini
[default]
endpoint   = https://s3.us-east-1.amazonaws.com
access_key = AKIAIOSFODNN7EXAMPLE
secret_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

[staging]
endpoint   = https://minio.internal:9000
access_key = minioadmin
secret_key = minioadmin
```

Select a profile with `--profile staging`. If no credentials file exists, `tug` reads `TUG_ENDPOINT`, `TUG_ACCESS_KEY`, and `TUG_SECRET_KEY` from the environment instead, which is usually what you want in CI. Because the file holds secrets in plain text, `tug` refuses to read it if its permissions are broader than `0600`.

## Usage

The three commands share the same argument shape: a local directory and a bucket, optionally with a key prefix.

```
tug push   ./public s3://my-bucket/site
tug status ./public s3://my-bucket/site
tug verify ./public s3://my-bucket/site
```

`push` uploads everything that differs and reports what it sent. `status` performs the same comparison but writes no data, so you can see the pending set before committing to it. `verify` is the stricter check: instead of trusting size and mtime, it fetches each remote object's ETag and compares it against a checksum of the local file, which catches the case where a file was modified in place without its timestamp changing, or where an earlier upload was truncated.

Adding `--dry-run` to `push` prints the same plan `status` would produce and exits without touching the bucket. Other flags worth knowing: `--profile` selects a credentials profile, `--concurrency` sets the number of parallel uploads (default 8), and `--verbose` logs every file considered rather than only those acted on.

## Ignoring files

If a `.tugignore` file sits at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore's, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root-level `.tugignore` is consulted; nested ignore files in subdirectories are not read.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, so a bucket that has been pushed to for a long time will accumulate objects that no longer exist on disk. Cleaning those up is a manual job for now.

Files larger than 5 GB will fail to upload, because `tug` does not implement multipart upload and that is the single-request ceiling the S3 API imposes.

`verify` is slow against large buckets. It issues a request per object to retrieve the ETag, so a bucket with a hundred thousand objects takes a correspondingly long time and a correspondingly large number of API calls. Treat it as an occasional audit rather than something to run on every push, and prefer `status` for routine checks.

## Licence

MIT.