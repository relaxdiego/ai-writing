# tug

`tug` pushes a local directory into an S3-compatible bucket. It is deliberately one-way: files move from your machine to the remote, and nothing on the remote comes back. That constraint keeps the mental model small. If a file exists locally, `tug` makes sure the bucket has a copy of it; if it does not exist locally, `tug` leaves the bucket alone.

Most invocations do very little work, because `tug` compares each local file's size and modification time against the metadata of the corresponding remote object and skips anything that matches. A second push over an unchanged tree costs one listing request and no transfers.

## Installation

With a Go toolchain (1.21 or later):

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo mv tug /usr/local/bin/
```

## Getting started

```
cd ~/photos
tug push --bucket my-archive --dry-run
tug push --bucket my-archive
```

The first command reports exactly what the second one would upload without touching the network beyond the listing it needs for comparison. Running with `--dry-run` first is worth the habit on an unfamiliar tree, since `tug` walks the whole directory and an unexpected `node_modules` or build cache shows up in the plan before it shows up in your bandwidth bill.

## Commands

`tug push` walks the local directory, compares each file against the remote object of the same key, and uploads whatever differs. Add `--dry-run` to print the plan and exit.

`tug status` performs the same comparison and prints the result without uploading anything. It differs from `tug push --dry-run` only in intent: `status` is the command to reach for when you want to know whether a directory is in sync, and it exits non-zero when there is pending work, which makes it usable in a scripted check.

`tug verify` ignores size and mtime entirely and compares checksums instead. Use it when you suspect a file was modified in a way that preserved its timestamp, or after a transfer that ended badly. Because it must fetch every object's ETag, it is much slower than the other two commands and issues one request per object.

## Credentials

`tug` reads credentials from `~/.tug/credentials`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/EXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
```

Select a non-default section with `--profile`. Environment variables take precedence over the file, which is the arrangement you want in CI: set `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY` and `TUG_ENDPOINT`, and no credentials file needs to exist at all. The endpoint may be omitted for Amazon S3 itself, in which case the region determines it.

## Ignoring files

If a `.tugignore` file is present at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore's, including negation with `!` and directory-only patterns ending in `/`:

```
*.log
build/
!build/manifest.json
```

Only the root file is consulted. Nested `.tugignore` files in subdirectories are not read, which is a departure from git's behaviour and a common source of surprise.

## Limitations

There is no delete propagation. Removing a file locally does not remove the object remotely, and there is no flag to make it do so. Treat the bucket as append-mostly and prune it by hand when you need to.

Files larger than 5GB will fail to upload, because `tug` does not yet implement multipart upload and that is the single-request ceiling S3 imposes. The failure is reported per file and does not abort the rest of the push.

`tug verify` is slow on large buckets. Every object costs a round trip to retrieve its ETag, so a bucket with a hundred thousand objects will take minutes rather than seconds. Scope it with a path prefix when you can, and prefer `tug status` for routine checks.

---

I filled in a few details the description left open: the module path, the environment variable names, the `--profile` and `--bucket` flags, and the non-zero exit from `status`. Swap in whatever the actual implementation uses.