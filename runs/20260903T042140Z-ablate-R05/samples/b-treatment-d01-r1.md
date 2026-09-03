# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the remote is a copy, and nothing ever travels back down. On each run it compares every local file against the corresponding remote object and uploads only those whose size or modification time differ, so a second push over an unchanged tree costs little more than the listing calls.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/yourorg/tug/cmd/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, then put it somewhere on your `PATH`:

```
curl -sSL https://github.com/yourorg/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

```
tug status ./site s3://my-bucket/site      # what would change
tug push --dry-run ./site s3://my-bucket/site
tug push ./site s3://my-bucket/site
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, and falls back to the environment if the file is absent or the requested profile is not in it. The file is INI-formatted and may hold several profiles, selected with `--profile`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1

[backblaze]
access_key_id = 002abc
secret_access_key = K002xyz
endpoint = https://s3.us-west-004.backblazeb2.com
region = us-west-004
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`; the standard `AWS_`-prefixed names are read too, so an existing AWS environment usually works without any configuration. Keep the credentials file at mode `0600`, since `tug` refuses to read it if it is group- or world-readable.

## Ignoring files

If a `.tugignore` file sits at the root of the directory being pushed, its patterns are applied to every candidate path. The syntax is gitignore's, including negation with `!`, directory-only patterns with a trailing slash, and `**` for arbitrary depth:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are never uploaded and are not reported as differences by `status`. They are also invisible to `verify`, so a file excluded after it has already been pushed will simply be left in place on the remote.

## Commands

`tug push <local-dir> <s3-url>` performs the synchronisation. Each file is compared against the remote object's size and last-modified time, and one that matches on both is skipped. Pass `--dry-run` to print the upload plan and exit without touching the bucket, which is worth doing on any tree you have not pushed before.

`tug status <local-dir> <s3-url>` reports what a push would do without performing it. Unlike `--dry-run` it exits with status 1 when differences exist, which makes it usable as a check in CI or a pre-deploy hook.

`tug verify <local-dir> <s3-url>` compares content rather than metadata. It fetches each object's ETag and checks it against the local file's MD5, catching corruption and partial uploads that the size-and-mtime heuristic cannot see. Run it periodically rather than on every push, for reasons covered under limitations below.

Flags common to all three commands:

| Flag | Meaning |
| --- | --- |
| `--profile <name>` | Credentials profile to use (default `default`) |
| `--endpoint <url>` | Override the endpoint from the profile |
| `--concurrency <n>` | Parallel transfers or checks (default 8) |
| `--verbose` | Log every file considered, not just those acted on |
| `--quiet` | Suppress everything except errors |

## Limitations

There is no delete propagation. A file removed locally stays in the bucket forever, so `tug` is well suited to append-mostly trees such as build artefacts, backups and static sites with stable paths, and poorly suited to mirroring a directory you prune. If you need the remote cleaned up, do it out of band.

Uploads are single-part, which caps individual files at the S3 limit of 5 GB. A larger file is reported as an error and skipped, and the rest of the push continues.

`verify` is slow on large buckets because it issues a request per object to read the ETag, with no way to batch them. On a bucket of a few thousand objects this is unremarkable; on hundreds of thousands it will take a long time and generate a corresponding number of billable requests. Raising `--concurrency` helps up to the point where your provider starts rate-limiting.

One further caveat on `verify`: ETags are only MD5 sums for objects that were uploaded in a single part. Anything written to the bucket by another tool using multipart upload will have a composite ETag that cannot be compared, and `tug` reports those as unverifiable rather than as mismatches.