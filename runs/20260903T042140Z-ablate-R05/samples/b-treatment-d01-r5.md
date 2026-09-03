# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way by design: the local tree is the source of truth, and the remote is a mirror of it. Files whose size and modification time already match the remote object are skipped, so a repeated push over a mostly-unchanged directory costs little more than the listing.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo mv tug /usr/local/bin/
```

## Getting started

Point `tug` at a directory and a bucket, and it uploads everything that differs:

```
tug push ./site s3://my-bucket/site
```

Before doing that for real, it is worth seeing what would happen. Passing `--dry-run` runs the full comparison and prints the transfer plan without writing anything to the remote, which makes it the safe way to check a new `.tugignore` or a path you are unsure about:

```
tug push --dry-run ./site s3://my-bucket/site
```

## Commands

`tug push` performs the sync. Each local file is compared against the corresponding remote object by size and mtime; if either differs, or the object is absent, the file is uploaded.

`tug status` reports what a push would do without uploading anything. It is the same comparison `push` performs, so it is a useful standalone check in scripts and CI, and it exits non-zero when the local tree and the remote have diverged.

`tug verify` confirms that what is in the bucket matches what is on disk. Rather than trusting size and mtime, it computes a checksum for each local file and compares it against the remote object's ETag, which catches truncated uploads and objects modified by something other than `tug`. Use it after a large push or on a schedule, not on every deploy; see the note on its cost below.

## Credentials

`tug` looks for credentials in `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a profile with `--profile`, or leave it unset to use `default`. The environment variables `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION` override the file when set, which is the easier route inside CI runners and containers where writing a dotfile is awkward.

## Ignoring files

A `.tugignore` file at the root of the local directory excludes paths from every command. It uses gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are never uploaded and are not considered when `status` or `verify` decide whether the two sides agree.

## Limitations

Deletes are not propagated. Removing a file locally leaves the remote object in place, and you will need to delete it yourself with another tool. This is deliberate for now, since one-way sync with automatic deletion is an easy way to lose data to a mistyped path, but it does mean a bucket managed by `tug` accumulates orphans over time.

Files larger than 5 GB cannot be uploaded, because `tug` issues a single `PutObject` per file and has no multipart support. Such files are reported as errors and skipped; the rest of the push continues.

`verify` fetches the ETag of every object in the target prefix, which means one request per object and no way to shortcut the scan. On a bucket with hundreds of thousands of objects it can run for a long time and generate a substantial number of API calls, so treat it as an occasional audit rather than part of a normal deploy.