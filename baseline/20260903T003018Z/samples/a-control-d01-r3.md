Here's the README. I've written it as a drop-in `README.md`; tell me if you'd like it saved into the repo.

---

# tug

`tug` pushes a local directory to an S3-compatible bucket. One direction, one job: local wins, remote follows.

It is deliberately not a general-purpose sync tool. There is no pull, no two-way reconciliation, and no delete propagation. If you want rsync semantics against S3, use something else. If you want to shove a build directory at a bucket on every deploy and have it skip the 9,000 files that haven't changed, `tug` is about right.

## Install

With Go 1.21 or newer:

```
go install github.com/example/tug/cmd/tug@latest
```

Or grab a prebuilt binary from the releases page and put it on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

`tug version` should print something.

## Quick start

```
export TUG_ACCESS_KEY_ID=AKIA...
export TUG_SECRET_ACCESS_KEY=...

tug status  ./public s3://my-bucket/site
tug push    ./public s3://my-bucket/site --dry-run
tug push    ./public s3://my-bucket/site
```

Every command takes the same two arguments: a local directory and a remote destination. The destination may include a key prefix; `s3://my-bucket/site` uploads `./public/index.html` to `site/index.html`.

## Commands

### `tug push`

Uploads local files that differ from the remote object.

A file is considered unchanged — and skipped — when its size and modification time both match what `tug` recorded for the corresponding object. Because S3's own `LastModified` is the time of upload rather than the time of authorship, `tug` writes the local mtime into object metadata (`x-amz-meta-tug-mtime`) on the way up and compares against that. Objects uploaded by anything other than `tug` have no such metadata, so the first push after adopting an existing bucket will re-upload everything once, then settle down.

This comparison is a heuristic. It is fast and it is wrong in exactly one interesting case: a file edited in place without changing its length, with the mtime restored afterwards. That is what `tug verify` is for.

```
tug push ./public s3://my-bucket/site
tug push ./public s3://my-bucket/site --dry-run
tug push ./public s3://my-bucket/site --concurrency 16
```

### `tug status`

Prints what `push` would do, and exits without touching the network beyond a listing. Same skip logic as `push`, no uploads.

```
$ tug status ./public s3://my-bucket/site
    new  assets/logo-v2.svg          (12.4 KiB)
modified  index.html                  (3.1 KiB)
 skipped  1,204 files unchanged
```

`--dry-run` on `push` and a bare `status` give you the same information. `status` exists so you can ask the question without typing a verb that means "write things".

### `tug verify`

Compares content rather than metadata. For each local file, `tug` fetches the remote object's ETag and compares it against the checksum of the local file, reporting any mismatch.

```
tug verify ./public s3://my-bucket/site
```

Use it after a push you don't trust, after a crashed upload, or on a schedule if the bucket matters. Don't use it in a tight loop — see the limitations below.

## Flags

| Flag | Applies to | Meaning |
|---|---|---|
| `--dry-run` | `push` | Report intended uploads, change nothing |
| `--concurrency N` | all | Parallel transfers or requests (default 8) |
| `--endpoint URL` | all | Non-AWS S3 endpoint (MinIO, R2, Backblaze, Ceph) |
| `--region NAME` | all | Bucket region |
| `--profile NAME` | all | Credentials profile to use (default `default`) |
| `--ignore-file PATH` | all | Alternate ignore file (default `.tugignore`) |
| `--no-ignore` | all | Ignore the ignore file |
| `-v`, `--verbose` | all | Per-file logging |

## Credentials

`tug` looks for credentials in this order, and stops at the first source that yields a key pair:

1. Environment variables: `TUG_ACCESS_KEY_ID` and `TUG_SECRET_ACCESS_KEY`, plus optional `TUG_SESSION_TOKEN`, `TUG_ENDPOINT`, and `TUG_REGION`.
2. `~/.tug/credentials`.

The credentials file is INI-formatted, one section per profile:

```ini
[default]
access_key_id = AKIA...
secret_access_key = ...
region = us-east-1

[minio-lab]
access_key_id = minioadmin
secret_access_key = minioadmin
endpoint = http://localhost:9000
region = us-east-1
```

Select a profile with `--profile minio-lab`. `tug` refuses to read the file if it is group- or world-readable; `chmod 600 ~/.tug/credentials`.

Note that these are `TUG_`-prefixed variables, not `AWS_`-prefixed ones. `tug` does not read `AWS_ACCESS_KEY_ID`, `~/.aws/credentials`, or instance metadata. This is intentional — it makes it hard to push to production by accident because a shell happened to have your admin credentials exported.

## `.tugignore`

If a file named `.tugignore` exists at the root of the local directory, `tug` reads it and excludes matching paths from all three commands. The syntax is gitignore's: glob patterns, `#` comments, `**` for recursive matches, `/` to anchor to the root, `!` to negate a previous pattern.

```gitignore
# build noise
node_modules/
*.map
.DS_Store

# keep the one sourcemap we actually serve
!dist/app.min.js.map
```

Only the root-level `.tugignore` is consulted. Unlike git, `tug` does not pick up per-directory ignore files in subtrees.

## Limitations

These are known and currently unaddressed.

**No delete propagation.** Deleting a local file does not delete the remote object. The remote set of objects only ever grows. For a static site this means stale assets linger indefinitely; prune them manually or with a bucket lifecycle rule. There is no `--delete` flag and adding one is not a small change, because getting it wrong destroys data.

**No multipart upload.** Files larger than 5 GB exceed the single-request `PutObject` limit and will fail. `tug` detects this before starting the transfer and reports the offending path rather than uploading 5 GB and then erroring. Files under that ceiling are fine, but large ones are uploaded in a single request with no resume — a dropped connection at 4 GB means starting over.

**`verify` is slow on large buckets.** It issues a `HEAD` per object to read the ETag, so cost and wall time scale linearly with object count, and `--concurrency` only helps until the endpoint starts rate-limiting. On a bucket with hundreds of thousands of objects, expect minutes to hours. It is also worth knowing that ETags are only MD5 checksums for objects uploaded in a single part — which, given the previous limitation, is all of them today, but the comparison will need rethinking if multipart support lands.

## License

MIT.

---

Two things I filled in because a README needs them and your brief didn't specify: the mtime-in-object-metadata mechanism (S3's native `LastModified` can't support the skip rule as described, so something has to store the local mtime), and the `TUG_`-prefixed environment variable names. Both are easy to change if the real tool works differently.