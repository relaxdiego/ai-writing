# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way and non-destructive: files move from local to remote, and nothing on the remote is ever deleted. On each run it compares every local file against the corresponding remote object and uploads only what differs, so repeated pushes over a mostly unchanged tree cost little more than the listing.

## Install

With a Go toolchain:

```
go install github.com/you/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`:

```
curl -L https://github.com/you/tug/releases/latest/download/tug-linux-amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Quick start

```
tug push ./site s3://my-bucket/assets
```

The first argument is a local directory, the second a bucket and optional key prefix. Add `--dry-run` to print the same upload plan without transferring anything, which is the sensible way to check a new prefix or a fresh `.tugignore` before committing to it.

## Commands

| Command | Compares | Uploads |
|---|---|---|
| `tug push` | size and mtime | yes |
| `tug status` | size and mtime | no |
| `tug verify` | checksums | no |

`push` walks the local tree and uploads any file whose size or modification time differs from the remote object, along with anything that has no remote counterpart. A file matching on both size and mtime is assumed current and skipped.

`status` runs that same comparison and prints the result without touching the bucket, so it answers "what would a push do right now" and nothing else. It is what `push --dry-run` reports, available as its own verb.

`verify` ignores mtimes and compares content instead, fetching each remote object's ETag and checking it against a locally computed checksum. Use it when you suspect a file was uploaded truncated, or when mtimes have been rewritten by a checkout or a restore and you no longer trust them as a staleness signal. Bear in mind the cost described under Limitations below.

## Credentials

`tug` reads `~/.tug/credentials` if it exists:

```ini
[default]
access_key_id     = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint          = https://s3.us-west-002.backblazeb2.com
region            = us-west-002
```

Environment variables override the file, which makes them the right choice in CI and in containers where writing a dotfile is awkward:

```
export TUG_ACCESS_KEY_ID=...
export TUG_SECRET_ACCESS_KEY=...
export TUG_ENDPOINT=https://...
export TUG_REGION=...
```

Any S3-compatible endpoint works. Point `endpoint` at AWS, MinIO, Backblaze B2, R2, or a local test server; `tug` has no AWS-specific behaviour beyond the protocol.

## Ignoring files

A `.tugignore` file in the root of the local directory excludes paths from every command. The syntax is gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are not uploaded, not reported by `status`, and not checked by `verify`.

## Limitations

These are known and unfixed, and worth reading before you rely on `tug` for anything you cannot re-push by hand:

- **No delete propagation.** Deleting a local file leaves the remote object in place. A bucket that has taken pushes for a while accumulates objects that no longer exist locally, and pruning them is your job.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit and `push` reports an error for them. Split such files or upload them with another client.
- **`verify` is slow on large buckets.** It fetches the ETag of every object it checks, one request apiece, so runtime grows linearly with object count and the wall-clock cost on a bucket of any size is measured in minutes. Treat it as an occasional audit rather than part of a deploy.

Two smaller consequences of the mtime heuristic are worth knowing. A file edited without its size or mtime changing will not be re-uploaded by `push`, and only `verify` will catch it. Conversely, a tool that rewrites mtimes across a tree, such as a fresh clone, will make `push` re-upload files whose contents never changed.

---

I filled in the spellings you didn't specify: the environment variable names, the credentials file format, and the `local dir` / `s3://bucket/prefix` argument order. Reconcile those against the implementation before publishing.