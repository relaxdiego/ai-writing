# tug

One-way directory sync to S3-compatible object storage.

`tug` pushes the contents of a local directory to a remote bucket. It compares each local file against the corresponding remote object and uploads only what has changed. It never modifies your local files, and it never deletes anything remotely.

## Installation

With Go 1.21 or later:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the [releases page](https://github.com/example/tug/releases) and put it somewhere on your `PATH`:

```
curl -LO https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz
tar xzf tug_linux_amd64.tar.gz
sudo mv tug /usr/local/bin/
```

## Quick start

```
$ cd ~/site
$ tug status
  4 files to upload (2.1 MB)
  118 files unchanged

$ tug push --dry-run
  would upload  index.html          4.2 KB
  would upload  css/main.css        18 KB
  would upload  img/header.png      1.9 MB
  would upload  img/footer.png      184 KB

$ tug push
  uploaded  index.html          4.2 KB
  uploaded  css/main.css        18 KB
  uploaded  img/header.png      1.9 MB
  uploaded  img/footer.png      184 KB
  done: 4 uploaded, 118 skipped
```

## Commands

### `tug push`

Uploads local files that differ from their remote counterparts. A file is **skipped** when its size and modification time both match the remote object; otherwise it is uploaded.

```
tug push [flags]

  --dry-run     print what would be uploaded, but upload nothing
```

`--dry-run` is worth using the first time you point `tug` at a new bucket — the mtime comparison can flag more files than you expect if the files were checked out fresh from version control.

### `tug status`

Reports what `tug push` would do, as a summary rather than a per-file list. Makes no changes.

```
tug status
```

### `tug verify`

Compares local and remote files by **checksum** instead of size and mtime, and reports any mismatches. Use this when you suspect an upload was truncated or when mtimes are unreliable — for instance after restoring from a backup that reset them.

```
tug verify
```

`verify` does not upload anything. If it reports mismatches, run `tug push` to correct them; if the mtimes happen to match, touch the offending files first so `push` picks them up.

## Configuration

### Credentials

`tug` looks for credentials in two places, in order:

1. `~/.tug/credentials`
2. Environment variables

The credentials file is INI-style:

```ini
[default]
endpoint   = https://s3.us-east-1.amazonaws.com
region     = us-east-1
bucket     = my-bucket
access_key = AKIAIOSFODNN7EXAMPLE
secret_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

Give it restrictive permissions:

```
chmod 600 ~/.tug/credentials
```

The equivalent environment variables:

| Variable | Meaning |
| --- | --- |
| `TUG_ENDPOINT` | S3 endpoint URL |
| `TUG_REGION` | Bucket region |
| `TUG_BUCKET` | Target bucket name |
| `TUG_ACCESS_KEY` | Access key ID |
| `TUG_SECRET_KEY` | Secret access key |

Any S3-compatible endpoint should work — AWS S3, MinIO, Backblaze B2, Cloudflare R2, Wasabi.

### `.tugignore`

If a `.tugignore` file exists in the directory being pushed, `tug` reads it and excludes matching paths. The syntax is the same as `.gitignore`:

```
# build artifacts
node_modules/
dist/
*.log

# but keep this one
!dist/release-notes.txt
```

Ignored files are not uploaded, and are not considered by `status` or `verify`.

## Limitations

These are real and current. Read them before relying on `tug` for anything important.

- **No delete propagation.** Deleting a local file does not delete the remote object. The remote bucket only ever accumulates. If you need to remove objects, do it with another tool.
- **No multipart upload.** Files larger than 5 GB will fail to upload. There is no workaround inside `tug` today; split the file or use the AWS CLI for those objects.
- **`verify` is slow on large buckets.** It fetches every object's ETag individually, so runtime scales linearly with object count and is dominated by round trips. On a bucket with tens of thousands of objects, expect it to take minutes. `status` and `push` are unaffected.

Two smaller things worth knowing: mtime comparison means a file that was rewritten with identical contents will still be re-uploaded, and because pushes are one-way, changes made directly in the bucket will be silently overwritten the next time that path is pushed.

## License

MIT.

---

Want me to write this to a `README.md` in a particular directory, or adjust the tone (shorter, more formal, more example-heavy)?