# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way: local is the source of truth, the bucket is a copy. Files whose size and modification time already match the remote object are skipped, so a repeat push over an unchanged tree costs a listing and nothing else.

## Install

With a Go toolchain:

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page, make it executable, and put it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Quick start

```
tug push ./site s3://my-bucket/site
```

Add `--dry-run` to see what would be uploaded without uploading anything. This is worth doing the first time you point `tug` at a new bucket, since there is no delete propagation to undo a mistake with.

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, then falls back to the environment. The file is INI-style and may hold several profiles:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a profile other than `default` with `--profile`. The environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`; set `endpoint` for MinIO, Backblaze B2, Cloudflare R2 or anything else speaking the S3 API. Keep the credentials file at mode `0600`; `tug` refuses to read it if it is group- or world-readable.

## Ignoring files

If a `.tugignore` file sits at the root of the directory being pushed, its patterns are applied to every path below. The syntax is gitignore's, including negation with `!` and directory-only patterns ending in `/`:

```
node_modules/
*.log
.DS_Store
!important.log
```

## Commands

`tug push <local-dir> <s3-uri>` uploads everything that differs. A file is considered unchanged when its size and mtime match the remote object's metadata, which makes push fast but means a file edited without changing either will be missed. `tug verify` exists for that case.

`tug status <local-dir> <s3-uri>` reports what a push would do without writing anything: new files, changed files, and files present remotely but not locally. It is the same comparison `push` performs, so it inherits the same mtime caveat.

`tug verify <local-dir> <s3-uri>` compares content instead of metadata. It computes each local file's checksum and compares it against the remote object's ETag, catching corruption, interrupted uploads and edits that preserved size and mtime. Anything it flags can be corrected with `tug push --force`.

Global flags: `--dry-run`, `--profile <name>`, `--concurrency <n>` (default 8), `--verbose`.

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket, and nothing in `tug` will clean it up for you; if the bucket must mirror the directory exactly, prune it by hand or with your provider's lifecycle rules.

Multipart upload is not implemented, so any single file over 5 GB will fail to upload. Split such files or move them with another tool.

`verify` fetches the ETag for every object in the target prefix, which means one request per object and no way to shortcut it. On a bucket with hundreds of thousands of objects this takes a long time and costs a corresponding number of API calls. Run it against a narrower prefix when you can, and treat it as an occasional audit rather than part of a routine push.

One further wrinkle in `verify`: an ETag is only an MD5 sum for objects uploaded in a single part. Objects that were put in the bucket by another tool using multipart upload carry a composite ETag that `tug` cannot reproduce, and those are reported as `unverifiable` rather than as mismatches.