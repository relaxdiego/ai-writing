# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way and additive: files that changed locally go up, everything else is left alone, and nothing on the remote is ever deleted.

The tool exists for the case where you have a directory that is the source of truth and a bucket that should mirror it — a built static site, a nightly export, a directory of artefacts. If you need two-way sync, deletion, or conflict resolution, `tug` is the wrong tool and will quietly leave you with a stale bucket rather than telling you so.

## Install

With a Go toolchain (1.21 or later):

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and put it on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug-linux-amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Usage

All three commands take a local directory and a remote destination:

```
tug push   ./public s3://my-bucket/site
tug status ./public s3://my-bucket/site
tug verify ./public s3://my-bucket/site
```

`tug push` uploads every local file whose size or modification time differs from the corresponding remote object. Add `--dry-run` to print the same plan without transferring anything; this is worth doing the first time you point `tug` at a bucket, since a mismatched prefix is easy to type and expensive to undo.

`tug status` reports what a push would do without performing it. It is the read-only twin of `push --dry-run` and takes the same flags.

`tug verify` compares the checksum of each local file against the remote object's ETag instead of trusting size and mtime. Use it when you suspect a partial upload, a clock problem, or a bucket that something else has written to. It is much slower than `status`, for the reason given under Limitations below.

## How files are skipped

A local file is uploaded when its size differs from the remote object's, or when its modification time is newer than the remote object's last-modified time. If both match, `tug` skips the file without reading it.

This is fast and it is approximate. A file edited in place without changing its length, on a filesystem whose timestamps have coarse resolution, can be missed. Restoring an old copy of a file over a newer one produces the same blind spot from the other direction, since the restored mtime may be older than what is already in the bucket. `tug verify` is the answer to both cases, and `tug push --force` will re-upload everything without consulting the remote at all.

## Credentials

`tug` reads credentials from the environment first, then from `~/.tug/credentials`. The environment variables are:

- `TUG_ACCESS_KEY_ID`
- `TUG_SECRET_ACCESS_KEY`
- `TUG_ENDPOINT` — the S3-compatible endpoint URL, defaulting to AWS S3
- `TUG_REGION` — defaulting to `us-east-1`

The credentials file is INI-formatted and may hold several named profiles, selected with `--profile`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002

[staging]
access_key_id = AKIAOTHEREXAMPLE
secret_access_key = ...
```

`tug` refuses to read the file if its permissions are broader than `0600`.

## Ignoring files

If a `.tugignore` file exists at the root of the local directory, `tug` reads it as a gitignore-syntax pattern list and excludes matching paths from every command, including `status` and `verify`. Nested `.tugignore` files in subdirectories are not read; one file at the root governs the whole tree.

```
node_modules/
*.log
.DS_Store
!important.log
```

Because ignored files are excluded from `verify` as well as `push`, adding a pattern after you have already uploaded matching files leaves those objects in the bucket with nothing reporting on them.

## Limitations

These are known and current, not edge cases you are unlikely to reach:

- **No delete propagation.** Removing a file locally does not remove the remote object, and no command will tell you the object is orphaned. A directory that has churned over months will accumulate objects with no local counterpart, and you must clean them up by hand or with the vendor's own tooling.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit of the S3 API and will fail the push with an error from the provider. `tug` does not split them, and there is no flag that makes it.
- **`verify` is slow on large buckets.** It issues a request per object to fetch the ETag, so its cost grows linearly with the number of remote objects and is dominated by round-trip latency. On a bucket with hundreds of thousands of objects, expect it to take a long time and to cost real money in request charges. Run it deliberately rather than on a schedule.

## Exit codes

`0` on success. `1` on a transfer or credential error. `2` when `status` or `verify` finds differences, so that either can be used as a check in a CI pipeline.

---

Two details were not in your specification and I filled them in to make the document usable: the environment variable names and the INI shape of the credentials file, and the exit-code convention. Adjust either to match the real implementation.