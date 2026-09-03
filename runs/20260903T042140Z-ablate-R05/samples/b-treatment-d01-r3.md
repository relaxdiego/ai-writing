# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way and one-way only: local is the source of truth, the bucket is the destination, and nothing ever travels back down. If you want two-way sync, or a backup tool that can restore, this is the wrong program.

On each run `tug` compares every local file against the corresponding remote object and skips the ones whose size and modification time already match, so a repeat push over an unchanged tree costs a listing and nothing else.

## Installation

```
go install github.com/you/tug@latest
```

Prebuilt binaries for Linux, macOS, and Windows are attached to each release; download one, make it executable, and put it somewhere on your `PATH`.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI-style file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The environment variables `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION` override whatever the file supplies, which makes CI runs and one-off pushes against a different endpoint straightforward. Set the endpoint explicitly for MinIO, Backblaze B2, Cloudflare R2, or anything else that speaks the S3 API without being S3.

## Commands

```
tug push [--dry-run] <local-dir> s3://bucket/prefix
tug status <local-dir> s3://bucket/prefix
tug verify <local-dir> s3://bucket/prefix
```

`push` does the work: it walks the local directory, compares each file against the remote object, and uploads the ones that differ. Passing `--dry-run` prints exactly the same plan without transferring anything, which is worth doing the first time you point `tug` at an unfamiliar prefix.

`status` reports what a push would do and exits without uploading. It is the same comparison `push` performs, so `status` and `push --dry-run` agree; `status` simply reads better when you want a summary rather than a transfer log.

`verify` answers a different question. Size and mtime are cheap proxies for "unchanged", and they are wrong whenever a file's contents change without its size moving, or whenever mtimes have been rewritten by a restore or a checkout. `verify` ignores both and compares content checksums against the remote ETags, so a mismatch means the bytes genuinely differ. Run it when you need certainty rather than speed.

## Ignoring files

Place a `.tugignore` at the root of the directory you are pushing. It uses gitignore syntax, including negation with `!` and directory patterns:

```
*.log
build/
!build/manifest.json
.DS_Store
```

Ignored files are skipped entirely. They are not uploaded, and they are not reported by `status` or `verify`.

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket, and `tug` will never notice or mention it. Over a long-lived prefix the remote accumulates everything that has ever been pushed, so periodic manual pruning is on you.

Files larger than 5 GB fail, because `tug` does not implement multipart upload and 5 GB is the single-request ceiling the S3 API imposes. The error is reported per file and does not abort the rest of the push.

`verify` is slow on large buckets. It fetches the ETag of every object under the prefix, one request each, so runtime grows linearly with object count regardless of how much data actually changed. On a bucket with hundreds of thousands of objects this takes long enough that it belongs in a nightly job rather than an interactive check.