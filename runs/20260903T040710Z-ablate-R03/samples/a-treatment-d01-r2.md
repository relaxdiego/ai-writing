# tug

`tug` pushes the contents of a local directory to an S3-compatible bucket. It is one-way only: local files are copied up, and nothing on disk is ever modified or removed. Before uploading, `tug` compares each local file's size and modification time against the corresponding remote object and skips the pair when both match, so running a push over an unchanged tree transfers nothing and costs a single listing.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract the `tug` binary, and place it anywhere on your `PATH`.

## Credentials

`tug` looks first at the environment and falls back to a config file. The variables it reads are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`; any value set in the environment overrides the same key in the file. The file lives at `~/.tug/credentials` and holds one profile per section:

```
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Because the file contains a secret, `tug` refuses to read it if its permissions are wider than `0600`.

## Commands

`tug push <local-dir> <bucket>[/prefix]` walks the local directory, compares each file with the remote object at the matching key, and uploads whatever differs or is missing. Adding `--dry-run` prints exactly what would be uploaded and what would be skipped without touching the bucket, which is the right way to check a new prefix or a freshly written `.tugignore` before committing to the transfer.

`tug status <local-dir> <bucket>[/prefix]` performs the same comparison and prints the resulting summary, but never uploads. It is `push --dry-run` without the intent to push, and it exits non-zero when the local tree and the bucket differ, so it can be used as a check in a script.

`tug verify <local-dir> <bucket>[/prefix]` answers a stricter question than the other two. Instead of trusting size and mtime, it computes a checksum for each local file and compares it against the remote object's ETag, which catches corruption and partial writes that the metadata comparison cannot see. Use it after a large migration or when you suspect a transfer went wrong, not as part of a routine push.

## Ignoring files

If a `.tugignore` file is present at the root of the local directory, `tug` reads it and excludes matching paths from every command. The syntax is gitignore's: one pattern per line, `#` for comments, `/` to anchor a pattern to the root, `**` to match across directory boundaries, and a leading `!` to re-include something an earlier pattern excluded.

```
# build artefacts
/dist/
*.tmp
!keep-this.tmp
```

Ignored files are simply invisible to `tug`. They are not uploaded, and because there is no delete propagation, adding a pattern for something already in the bucket will not remove the object that is there.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding object in the bucket, and the only way to clear it is with another tool. This is deliberate for now, since a sync that deletes remotely on the strength of a local absence is a good way to lose data to a mistyped path.

Files larger than 5 GB will fail to upload. `tug` issues a single `PutObject` per file and does not yet implement multipart upload, so it runs into the hard per-request limit that S3 and its compatible implementations impose.

`verify` is slow on large buckets. It fetches every object's ETag individually rather than relying on the listing, so its runtime grows with object count and it will take a long time against a bucket holding hundreds of thousands of keys. Reach for it when you have a specific reason to distrust the metadata, and let `status` cover the ordinary case.

The repository path, environment variable names and endpoint defaults above are placeholders where your project's real values belong.