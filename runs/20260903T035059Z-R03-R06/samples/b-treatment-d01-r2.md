# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: files move from local to remote and never the other direction, so a stale local copy can never overwrite something newer on the far end and a `tug` run can never touch your working tree. Files whose size and modification time match the corresponding remote object are skipped, which makes repeat runs over a large tree cheap.

## Installing

With a Go toolchain (1.21 or later):

```
go install github.com/example/tug/cmd/tug@latest
```

Otherwise download a prebuilt binary for your platform from the releases page and put it somewhere on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo install tug /usr/local/bin/tug
```

## Getting started

Point `tug` at a directory and a bucket. The first push uploads everything; later pushes upload only what changed.

```
tug push ./site --bucket my-assets
tug push ./site --bucket my-assets --prefix v2/ --dry-run
```

`--dry-run` performs the full comparison against the remote listing and prints exactly what a real run would upload, without writing anything. It is the recommended way to check a new `--prefix` or a freshly edited `.tugignore` before committing to the transfer.

## Commands

`tug push` walks the local directory, compares each file against the remote listing, and uploads what differs. Comparison is by size and mtime; a file whose contents changed without changing either will be skipped, which is the tradeoff that keeps ordinary pushes fast.

`tug status` runs the same comparison and reports it, then exits without uploading. It differs from `push --dry-run` only in intent and exit code: `status` exits 1 when the local directory and the bucket differ, so it is usable as a check in a script or CI job.

`tug verify` compares checksums instead of mtimes. It fetches the ETag of every object under the prefix and checks it against a locally computed digest, catching the case `push` is designed to miss: content that changed while size and timestamp stayed put. Run it after a restore, after a migration between providers, or on whatever schedule your paranoia suggests, rather than on every push.

## Credentials

`tug` looks first at the environment and falls back to a credentials file. The recognised variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. If the key variables are unset, `tug` reads `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1

[backblaze]
access_key_id = 0021234567890abcdef
secret_access_key = K002examplesecretvalue
endpoint = https://s3.us-west-004.backblazeb2.com
region = us-west-004
```

Select a section with `--profile backblaze`; without it, `tug` uses `[default]`. The file must not be group- or world-readable, and `tug` refuses to start if its mode is looser than `0600`.

## Ignoring files

If a `.tugignore` file sits at the root of the directory being pushed, `tug` reads it and skips anything it matches. The syntax is gitignore syntax, including negation with `!`, directory-only patterns ending in `/`, and `**` for arbitrary depth:

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root `.tugignore` is consulted; nested ones in subdirectories are ignored, unlike git's behaviour. Patterns are matched against paths relative to the push root, so a rule written as `/build` anchors to that root rather than to the filesystem.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding object in the bucket untouched, and nothing in `tug` will ever issue a delete. Pruning a bucket is a job for the provider's console, lifecycle rules, or another tool.

Files larger than 5GB will fail to upload. Multipart upload is not implemented, so `tug` is bounded by the single-request object size limit that S3 and its clones impose. The failure is reported per file and does not abort the rest of the run.

`tug verify` is slow on large buckets. It issues a request per object to read the ETag, so its cost scales linearly with object count rather than with the number of changed files, and a bucket with hundreds of thousands of objects will take a long time. Narrowing the work with `--prefix` is the usual remedy.

---

Flag names (`--bucket`, `--prefix`, `--profile`), the module path, and the credentials file format are placeholders where your specification did not fix them; swap them for the real ones before publishing.