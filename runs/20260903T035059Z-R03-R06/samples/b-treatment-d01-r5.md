# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way: the local tree is the source of truth, and remote objects are created or overwritten to match it. Nothing on the remote is ever copied back down, and no local file is ever modified.

On each run tug walks the local directory, compares every file against the corresponding remote object, and uploads only what differs. The comparison is by size and modification time: tug records each file's mtime in the object's metadata when it uploads, and a later run skips the file when both the size and that recorded mtime still match. This makes repeat pushes cheap, since an unchanged tree costs one listing and no transfers, at the price of trusting timestamps. When you want the stronger guarantee, `tug verify` compares checksums instead.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/example/tug/cmd/tug@latest
```

Otherwise download a prebuilt binary for your platform from the releases page, make it executable, and put it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64 -o tug
chmod +x tug && sudo mv tug /usr/local/bin/
```

## Commands

`tug push <dir> s3://bucket/prefix` uploads everything under `<dir>` that is new or changed. Pass `--dry-run` to print the same plan without transferring anything, which is worth doing the first time you point tug at a bucket that already has contents in it.

```
tug push ./site s3://assets/site
tug push ./site s3://assets/site --dry-run
```

`tug status <dir> s3://bucket/prefix` reports what a push would do and exits without uploading. It is the read-only sibling of `--dry-run` and prints the count of files to upload, files to skip, and remote objects with no local counterpart. Those orphaned objects are reported but never removed; see the limitations below.

`tug verify <dir> s3://bucket/prefix` fetches every object under the prefix and compares its ETag against a checksum of the local file, ignoring sizes and timestamps entirely. Use it after a push you have reason to distrust, or on a schedule if the tree is written to by something other than tug.

## Credentials

tug reads credentials from `~/.tug/credentials`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Select a non-default section with `--profile <name>`. The environment variables `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION` override whatever the file supplies, field by field, so you can keep an endpoint in the file and inject the secret from a password manager or CI secret store. If neither source provides a key pair, tug exits with a configuration error rather than attempting an anonymous request.

## Ignoring files

A `.tugignore` file at the root of the pushed directory excludes paths using gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
*.log
node_modules/
.DS_Store
!important.log
```

Patterns are matched against paths relative to the directory being pushed. Nested `.tugignore` files in subdirectories are not read; one file at the root governs the whole tree. The `.tugignore` file itself is never uploaded.

## Limitations

There is no delete propagation. Removing a file locally leaves its object in the bucket, and `tug status` will list it as orphaned so you can clean it up yourself. This is deliberate for now, since a bug in the walk logic would otherwise be able to delete data.

Files larger than 5 GB fail, because tug issues a single `PutObject` per file and has no multipart upload path. The upload aborts with an error naming the file, and the rest of the push continues.

`verify` is slow on large buckets. It issues a request per object to read the ETag, so runtime grows linearly with object count rather than with the number of changed files, and a bucket with hundreds of thousands of objects will take minutes. Scope it to a narrower prefix when you only need to check part of the tree.