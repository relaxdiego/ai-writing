# tug

`tug` pushes a local directory to an S3-compatible bucket. It is a one-way tool: the local tree is the source of truth, and nothing on the remote side ever comes back down. If you want a two-way sync or a mirror that deletes, this is the wrong tool.

## Install

With a Go toolchain:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, unpack it, and put `tug` somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo install tug /usr/local/bin/tug
```

## Quick start

```
$ cd ~/photos
$ tug status s3://my-bucket/photos
  3 new, 1 changed, 214 unchanged

$ tug push s3://my-bucket/photos --dry-run
  + 2026/summer/IMG_4417.jpg   (2.1 MB)
  + 2026/summer/IMG_4418.jpg   (1.9 MB)
  + 2026/summer/IMG_4419.jpg   (2.4 MB)
  ~ index.html                 (4.1 KB)
  would upload 4 files, 8.5 MB

$ tug push s3://my-bucket/photos
  uploaded 4 files, 8.5 MB in 3.2s
```

## Commands

**`tug push <bucket-url>`** walks the local directory, compares each file against the corresponding remote object, and uploads anything that is new or that differs. A file is considered unchanged, and is skipped, when its size and modification time both match the remote object's metadata. Pass `--dry-run` to print the upload plan and exit without writing anything.

**`tug status <bucket-url>`** does the same comparison and prints a summary without uploading. It is the read-only half of `push`, useful when you want to know how far the local tree has drifted before committing to the transfer.

**`tug verify <bucket-url>`** compares checksums instead of modification times. Because mtimes are cheap to compare but easy to falsify, `push` can be fooled by a file that was restored from a backup or rewritten with a preserved timestamp; `verify` catches that by hashing local content and checking it against each object's ETag. Run it when you need to be certain the remote copy is byte-for-byte correct, not merely plausible. It is much slower than `status`, for the reason given under limitations below.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Select a non-default section with `--profile <name>`. Any of these environment variables, when set, override the corresponding value from the file:

- `TUG_ACCESS_KEY_ID`
- `TUG_SECRET_ACCESS_KEY`
- `TUG_ENDPOINT`
- `TUG_REGION`

The credentials file should not be world-readable. `tug` refuses to start if its mode is looser than `0600`.

## Ignoring files

If a `.tugignore` file is present at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
*.tmp
node_modules/
.DS_Store
!keep-this.tmp
```

Ignored files are invisible to all three commands. `status` will not count them as new, and `verify` will not report them as missing from the remote.

## Limitations

- **No delete propagation.** Removing a file locally leaves the remote object in place. Deleting remote objects is a destructive operation that a sync tool should not perform on inference, so `tug` does not do it at all. Prune the bucket with your provider's own tooling.
- **No multipart upload.** Files larger than 5 GB exceed the single-`PUT` limit of every S3-compatible API and will fail. `tug` reports the offending path and continues with the rest of the tree rather than aborting the run.
- **`verify` is slow on large buckets.** It issues a request per object to fetch the ETag, so its cost grows linearly with the number of objects and is dominated by round-trip latency. On a bucket of a hundred thousand objects, expect to wait. Scope it to a prefix when you can.

---

A note on what I filled in: you gave me the behaviour but not the surface details, so I invented the credentials-file format, the environment variable names, the `--profile` flag, the URL form `s3://bucket/prefix`, the module path, and the output text in the examples. Check those against the real implementation before publishing.