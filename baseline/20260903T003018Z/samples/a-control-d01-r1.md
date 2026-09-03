Here's the README:

---

# tug

One-way directory sync to S3-compatible object storage.

`tug` pushes the contents of a local directory to a remote bucket. It compares each local file against the corresponding remote object and uploads only what has changed. It never modifies your local files, and it never deletes anything.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, then:

```
chmod +x tug
mv tug /usr/local/bin/
```

## Quick start

```
export TUG_ACCESS_KEY_ID=AKIA...
export TUG_SECRET_ACCESS_KEY=...

tug status  ./site s3://my-bucket/site
tug push    ./site s3://my-bucket/site
```

`tug status` is always safe — it only reads. Run it first to see what a push would do.

## Commands

### `tug push <local-dir> <bucket-url>`

Uploads every local file whose size or modification time differs from the remote object. Files that match on both are skipped without being read.

```
tug push ./site s3://my-bucket/site
tug push ./site s3://my-bucket/site --dry-run
```

`--dry-run` prints the exact set of uploads that would happen and exits without transferring anything.

### `tug status <local-dir> <bucket-url>`

Reports what `push` would do, using the same size-and-mtime comparison. Equivalent to `push --dry-run`, but reads as a query rather than a withheld action.

### `tug verify <local-dir> <bucket-url>`

Compares local files to remote objects by checksum instead of by size and mtime. Use this when you want certainty that the remote contents match the local ones — after a network interruption, for example, or when mtimes have been rewritten by a build step or a fresh checkout.

`verify` is read-only. It reports mismatches; it does not fix them. Follow up with `tug push` for anything it flags.

## Credentials

`tug` looks for credentials in this order:

1. The environment variables `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, and optionally `TUG_ENDPOINT` and `TUG_REGION`.
2. The file `~/.tug/credentials`.

The credentials file is INI-style:

```ini
[default]
access_key_id     = AKIA...
secret_access_key = ...
endpoint          = https://s3.us-east-1.amazonaws.com
region            = us-east-1
```

Set `endpoint` to point at any S3-compatible service — MinIO, Backblaze B2, Cloudflare R2, and similar. Give the file mode `0600`; `tug` will warn if it is readable by other users.

## Ignoring files

If a `.tugignore` file is present in the local directory, `tug` reads it and skips matching paths. The syntax is gitignore syntax: one pattern per line, `#` for comments, `!` to re-include, trailing `/` to match directories only.

```
# build artifacts
node_modules/
*.log
.DS_Store

# ...but keep this one
!important.log
```

The same ignore rules apply to `push`, `status`, and `verify`, so all three agree on which files are in scope.

## Limitations

These are known and intentional for the current version. Read them before trusting `tug` with anything important.

**No delete propagation.** If you delete a local file, its remote object stays. Over time the bucket accumulates objects with no local counterpart. `tug` will not tell you which ones — you will need to reconcile that yourself. If you need the remote to be an exact mirror, `tug` is the wrong tool.

**No multipart upload.** Files larger than 5 GB will fail to upload, since single-request PUT is capped there. `tug push` reports the failure and continues with the remaining files rather than aborting the run.

**`verify` is slow on large buckets.** It fetches the ETag for every object individually, so runtime grows linearly with object count and it makes one request per object. On a bucket with hundreds of thousands of objects this can take a long time and generate a correspondingly large number of API calls, which may cost money on metered services. `verify` is meant for occasional confirmation, not for routine use — `status` is the everyday command.

**mtime is a heuristic.** Normal `push` trusts size and modification time. A file edited in place without changing either will be treated as unchanged and skipped. This is uncommon but possible; `verify` is the check that catches it.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success; for `status` and `verify`, no differences found |
| 1 | Differences found (`status`, `verify`) |
| 2 | Usage error — bad arguments or unreadable local directory |
| 3 | Credentials missing or rejected |
| 4 | One or more transfers failed |

## License

MIT.