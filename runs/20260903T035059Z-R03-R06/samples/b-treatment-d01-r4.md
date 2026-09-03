# tug

`tug` synchronises a local directory with a remote S3-compatible bucket. It pushes in one direction only: your local tree is the source of truth and the bucket receives a copy of it. Files whose size and modification time already match the corresponding remote object are skipped, so a second run over an unchanged tree costs one listing and no uploads.

## Installation

With a Go toolchain installed:

```
go install github.com/yourorg/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release on the GitHub releases page. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo install tug /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials`, which uses an INI format with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Select a non-default section with `--profile`. Every field can also be supplied through the environment as `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`; environment variables take precedence over the file, which makes them convenient in CI where writing a credentials file is awkward. If neither source provides a key pair, `tug` exits before contacting the network rather than attempting an anonymous request.

## Usage

All three commands take the local directory and the destination bucket, optionally with a key prefix:

```
tug push ./site s3://my-bucket/assets
tug status ./site s3://my-bucket/assets
tug verify ./site s3://my-bucket/assets
```

`push` uploads every local file that is missing remotely or whose size or mtime differs from the remote object. `status` performs the same comparison and prints what would change without uploading anything, which is also what `push --dry-run` does; the difference is that `status` is read-only by construction and safe to wire into a script that runs unattended. `verify` ignores mtimes entirely and compares checksums against the ETag of each remote object, catching the case where a file was modified in place by something that preserved its timestamp and length.

Useful flags:

```
--dry-run          show planned uploads without performing them
--profile NAME     credentials section to use (default: "default")
--concurrency N    parallel uploads (default: 8)
--verbose          log every file considered, not just those uploaded
```

## Ignoring files

If a `.tugignore` file is present at the root of the local directory, its patterns are applied using gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored paths are excluded from `push`, `status` and `verify` alike, so a file you exclude will not be reported as missing from the bucket.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding object in the bucket, and `tug` will never report it, so a bucket that has been pushed to over a long period accumulates objects for paths that no longer exist. Prune those with your provider's console or lifecycle rules.

Files larger than 5 GB fail to upload, because `tug` issues a single `PutObject` request per file and does not yet implement multipart upload. The failure is reported per file and does not abort the rest of the run.

`verify` is slow on large buckets. It issues a request per object to read the ETag, so a bucket with a hundred thousand objects takes minutes even at high concurrency. Reserve it for periodic auditing and rely on `push` and `status` for routine work.