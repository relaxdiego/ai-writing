```markdown
# tug

`tug` pushes a local directory into an S3-compatible bucket and leaves it there. It is
one-way by design: local is the source of truth, the bucket is a destination, and nothing
the bucket says can change a file on your disk. If you want two-way sync, conflict
resolution, or a remote that can delete things locally, `tug` is the wrong tool and will
stay the wrong tool.

## Installing

With a Go toolchain:

```
go install github.com/example/tug/cmd/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, put it on your
`PATH`, and make it executable. `tug` is a single static binary with no runtime
dependencies.

## Getting started

```
cd ~/photos
tug push --bucket my-bucket --dry-run
tug push --bucket my-bucket
```

The first command tells you what would be uploaded without touching the network beyond
listing the bucket. Once it looks right, drop `--dry-run` and run it again.

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, then falls back to the
environment. The file is a simple set of key/value pairs:

```
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

The equivalent environment variables are `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`TUG_ENDPOINT` and `AWS_REGION`. Environment variables win over the file when both are
set, which makes it easy to override a personal default inside CI without editing
anything. Keep the credentials file readable only by you; `tug` will refuse to use it if
its mode is wider than `0600`.

## Commands

`tug push` walks the local directory and uploads anything the remote does not already
have. A file is considered already present when its size and modification time both match
the corresponding object, so a re-run over an unchanged tree does almost no work and
transfers no bytes. This is a heuristic rather than a proof: a file edited in place
without its mtime advancing, or restored from a backup that reset timestamps, will be
skipped even though its contents differ. `--dry-run` prints the same plan without
uploading.

`tug status` performs the comparison and stops. It prints the files that would be
uploaded, grouped by reason (new, size changed, newer than remote), and exits non-zero if
anything is out of date. That exit code is the useful part in scripts: you can gate a
deploy or a nightly job on whether the tree is already published.

`tug verify` is the slower, more honest check. Instead of trusting size and mtime it
fetches each object's ETag and compares it against a checksum of the local file, which
catches exactly the silent-corruption and reset-timestamp cases that `push` skips over.
Run it when you care about the answer rather than the speed, and read the section on
limitations below before pointing it at a large bucket.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it
and skips matching paths. The syntax is gitignore syntax, including negation with `!` and
directory-only patterns with a trailing slash:

```
*.tmp
node_modules/
.DS_Store
!keep-this.tmp
```

Ignored paths are invisible to all three commands, so a file excluded here will not be
uploaded by `push`, will not appear in `status`, and will not be checked by `verify`.

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket
untouched, and `tug` will neither report it nor clean it up. Over a long-lived directory
the remote therefore accumulates everything you have ever pushed, and pruning it is a
manual job.

Files larger than 5GB will fail to upload. `tug` issues a single `PutObject` per file and
does not implement multipart upload, so it runs into the S3 single-request ceiling. The
failure is reported per file and does not abort the rest of the push.

`tug verify` is slow on large buckets. It issues a request per object to read the ETag,
so its cost grows linearly with the number of objects rather than with the number of
files that actually changed. On a bucket with hundreds of thousands of objects this takes
long enough that it belongs in a scheduled job rather than an interactive session; use
`tug status` for the quick check.

## Licence

MIT.
```

A few details in there are not fixed by your description and I filled them in the most conventional way available: the key names in `~/.tug/credentials`, the environment variable names (standard AWS ones plus `TUG_ENDPOINT`), the `0600` permission check, the `--bucket` flag, and the non-zero exit from `tug status`. Swap them for whatever the tool actually does.