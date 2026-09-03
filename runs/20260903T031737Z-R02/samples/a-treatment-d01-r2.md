# tug

`tug` copies a local directory into an S3-compatible bucket. It is one-way by design: your disk is the source of truth, the bucket is a copy, and nothing on the remote side can change a local file. Before uploading anything, `tug` compares each local file's size and modification time against the corresponding remote object and skips the ones that already match, so running a push over a tree that hasn't changed costs a bucket listing and almost nothing else.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/tug-cli/tug/cmd/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, unpack it, and put `tug` somewhere on your `PATH`:

```
curl -sSL https://github.com/tug-cli/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo install tug /usr/local/bin/tug
```

There is nothing to configure at install time; `tug` reads everything it needs from the flags, the environment, and `~/.tug/credentials`.

## Quick start

```
# See what a push would do, without touching the bucket
tug push --bucket my-backups --dry-run ./site

# Do it
tug push --bucket my-backups ./site

# Later: what's out of date?
tug status --bucket my-backups ./site
```

## Commands

### `tug push [flags] <dir>`

Walks `<dir>`, skips anything matched by `.tugignore`, and uploads every file whose size or mtime differs from the remote object. Files that exist remotely but not locally are left alone. Useful flags:

| Flag | Meaning |
| --- | --- |
| `--bucket <name>` | Destination bucket (required) |
| `--prefix <path>` | Key prefix to push under, e.g. `--prefix site/v2` |
| `--endpoint <url>` | S3-compatible endpoint; omit for AWS S3 |
| `--dry-run` | Print the upload and skip decisions, change nothing |
| `--concurrency <n>` | Parallel uploads (default 8) |

`--dry-run` is worth using the first time you point `tug` at a new bucket or prefix, because it prints exactly the same decisions the real run would make and gives you a chance to notice a missing `.tugignore` entry before it becomes ten thousand uploaded objects.

### `tug status [flags] <dir>`

Reports what a push would change, in summary form: how many files would upload, how many would be skipped, and how many bytes are involved. It uses the same size-and-mtime comparison that `push` uses, so it is fast, and it is read-only.

### `tug verify [flags] <dir>`

Compares local files against the remote by checksum instead of by mtime. Where `push` and `status` trust the metadata, `verify` fetches each object's ETag and checks it against a hash of the local file, which catches the cases metadata cannot: a truncated upload, a file rewritten with the same size and a preserved timestamp, or bit rot on either end. Treat it as an occasional audit rather than part of your normal push loop, and see the limitations below for why.

## Credentials

`tug` looks for credentials in two places, environment first:

```
TUG_ACCESS_KEY_ID
TUG_SECRET_ACCESS_KEY
TUG_ENDPOINT        # optional, same as --endpoint
```

If those are unset, it reads `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY

[backblaze]
access_key_id = 0012345678
secret_access_key = K001exampleexample
endpoint = https://s3.us-west-001.backblazeb2.com
```

Select a non-default profile with `--profile backblaze`. The file must not be group- or world-readable; `tug` refuses to start if its mode is looser than `0600`, on the theory that a hard error now beats a leaked key later.

## Ignoring files

If a `.tugignore` file exists at the root of the directory you are pushing, `tug` reads it and applies gitignore syntax to decide what to leave behind. Patterns work the way they do in `.gitignore`: `*.log` for extensions, a trailing slash like `cache/` for directories, a leading `!` to re-include something an earlier pattern excluded, and a leading slash to anchor a pattern to the root rather than matching at any depth.

```
node_modules/
*.tmp
.DS_Store
/private
!/private/public-notes.md
```

Ignore rules apply to every command, so a file excluded from `push` will not be flagged by `status` or checked by `verify`.

## Limitations

These are known and deliberate rather than bugs; if any of them blocks you, say so in an issue rather than working around it silently.

- **No delete propagation.** Removing a file locally does not remove the remote object. A bucket that has been pushed to for a long time accumulates everything you have ever pushed, and pruning it is a manual job.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit for S3 PUT and will fail. `tug` reports them by name and continues with the rest of the tree rather than aborting the run.
- **`verify` is slow on large buckets.** It fetches an ETag for every object, one request each, so cost and wall-clock time scale with object count rather than with the number of files that actually changed. On a bucket with hundreds of thousands of objects this takes a long while, and running it against a subset with `--prefix` is usually the better move.

## License

MIT.