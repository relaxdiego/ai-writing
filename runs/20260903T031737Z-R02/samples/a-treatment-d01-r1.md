# tug

`tug` pushes a local directory into an S3-compatible bucket and keeps it in sync there. The sync is one-way by design: local is the source of truth and the bucket is a copy, so `tug` never writes to, renames, or deletes anything on your disk. It is a single static Go binary with no runtime dependencies, which makes it easy to drop into a CI image or a cron job.

## Install

With a Go toolchain (1.21 or newer):

```
go install github.com/tugsync/tug/cmd/tug@latest
```

Prebuilt binaries for Linux, macOS, and Windows on both amd64 and arm64 are attached to every release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
curl -sSL https://github.com/tugsync/tug/releases/latest/download/tug_linux_arm64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

Write your credentials to `~/.tug/credentials`, then run a dry run from the directory you want to push. `--dry-run` prints exactly what a real push would do without transferring a byte, so it is the right way to check a new configuration:

```
$ tug push --bucket site-assets --dry-run
+ img/hero@2x.png        1.4 MB
+ css/main.css           18 kB
~ index.html             4 kB   (size differs)
  js/vendor.js                  (unchanged, skipped)

dry run: 3 objects to upload (1.5 MB), 1 skipped
```

Drop `--dry-run` and the same plan executes. Uploads run concurrently, defaulting to eight at a time:

```
$ tug push --bucket site-assets
uploaded 3 objects (1.5 MB) in 2.1s, 1 skipped
```

## Commands

### `tug push`

`push` walks the local directory, compares each file against the corresponding remote object, and uploads whatever differs. A file is skipped when its size and modification time both match the remote copy; since S3's own `Last-Modified` records upload time rather than authorship time, `tug` stores the local mtime as object metadata on upload and compares against that. The comparison is cheap — one `ListObjectsV2` pass over the prefix — which is what makes repeat pushes of a large tree fast.

### `tug status`

`status` performs the same comparison as `push` and prints the resulting plan, but never uploads. It differs from `push --dry-run` only in intent and exit code: `status` exits `0` when local and remote agree and `1` when they have drifted, so it works as a check step in a pipeline.

### `tug verify`

`verify` ignores mtimes entirely and compares content checksums instead. For each local file it computes the MD5 digest and compares it to the remote object's ETag, which catches the cases metadata cannot — a truncated upload, a file whose mtime was rewritten by a build step, or an object modified by something other than `tug`. Because ETags are not returned by a bulk listing, `verify` issues a `HeadObject` request per object; see the limitations below before pointing it at a large bucket.

## Configuration

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile. Restrict its permissions to `0600`; `tug` refuses to read it otherwise:

```ini
[default]
endpoint          = https://s3.us-west-002.backblazeb2.com
region            = us-west-002
access_key_id     = 002abc...
secret_access_key = K002xyz...
bucket            = site-assets

[staging]
endpoint          = http://localhost:9000
region            = us-east-1
access_key_id     = minioadmin
secret_access_key = minioadmin
bucket            = staging-assets
```

Select a profile with `--profile staging`, or set `TUG_PROFILE`. Every field also has an environment variable equivalent — `TUG_ENDPOINT`, `TUG_REGION`, `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_BUCKET` — and the environment wins over the file, which in turn loses to an explicit command-line flag. The standard `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are honoured as a fallback when their `TUG_` counterparts are unset, so an existing CI setup usually works without changes.

## Ignoring files

A `.tugignore` file in the root of the directory being pushed excludes paths from every command, using gitignore syntax: glob patterns, `**` for nested directories, a leading `/` to anchor to the root, and a leading `!` to re-include something an earlier pattern excluded. Patterns apply to `push`, `status`, and `verify` alike, so an ignored file is neither uploaded nor reported as drift.

```
node_modules/
*.log
.DS_Store
/build/**
!/build/manifest.json
```

`.tugignore` files in subdirectories are not read; a single root file governs the whole tree.

## Flags

| Flag | Description |
| --- | --- |
| `--bucket <name>` | Target bucket, overriding the profile and environment. |
| `--prefix <path>` | Key prefix to push under. Defaults to the bucket root. |
| `--profile <name>` | Credentials profile to use. Defaults to `default`. |
| `--dry-run` | Print the plan without uploading. `push` only. |
| `--concurrency <n>` | Parallel uploads or checksum requests. Defaults to `8`. |
| `--verbose`, `-v` | Log every file considered, including skips. |

## Limitations

**No delete propagation.** Deleting a local file leaves the corresponding remote object in place, and `status` will not report it as drift. Pruning the bucket is a manual job for now, whether through your provider's console or a lifecycle rule; treat the remote as an append-only mirror until that changes.

**No multipart upload.** Files larger than 5 GB exceed the single-request `PutObject` limit and will fail with an error from the provider rather than being split into parts. `tug` detects the size beforehand and skips such files with a warning instead of attempting a doomed upload, so one oversized file will not abort the rest of the push.

**`verify` is slow on large buckets.** Fetching an ETag requires a request per object, so verification time scales linearly with object count rather than with the number of changed files — a bucket with 100,000 objects takes minutes even when nothing has changed. Raising `--concurrency` helps up to the point your provider starts rate-limiting, and narrowing the scope with `--prefix` helps more. Use `status` for routine checks and reserve `verify` for occasions when you have real reason to distrust the metadata.

## License

MIT.

---

A few details weren't in your brief, so I picked plausible ones you may want to correct: the repository path, the credentials file format and its `TUG_*` variable names, the default concurrency of 8, the `status` exit-code convention, and the choice to store local mtime as object metadata (without it, mtime-based skipping can't work against S3's `Last-Modified`). I also assumed `verify` compares MD5 against ETag, which is only valid for single-part uploads — convenient here, since `tug` doesn't do multipart anyway.