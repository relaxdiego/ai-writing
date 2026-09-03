# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: files move from local to remote and never the other direction, so a push can add or overwrite objects but will never touch anything on your disk. Files whose size and modification time already match the corresponding remote object are skipped, which makes repeated pushes over a large tree cheap.

## Installation

With a Go toolchain installed:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo install tug /usr/local/bin/tug
```

## Getting started

Credentials come from `~/.tug/credentials`, an INI-style file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.eu-central-1.amazonaws.com
region = eu-central-1
```

If you would rather not keep a file, set `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION` in the environment instead. Environment variables take precedence over the credentials file, so you can override a single value for one invocation without editing anything.

A first push looks like this:

```
tug push ./site s3://my-bucket/site
```

Before doing that for real, it is worth running the same command with `--dry-run`, which prints exactly what would be uploaded and skipped without sending a byte.

## Commands

`tug push <local-dir> <s3-uri>` walks the local directory and uploads every file whose size or mtime differs from the remote object, or which does not exist remotely at all. Add `--dry-run` to see the plan without executing it.

`tug status <local-dir> <s3-uri>` performs the same comparison and prints the resulting summary, but never uploads. It is the read-only sibling of `push --dry-run` and is safe to wire into a prompt or a cron report.

`tug verify <local-dir> <s3-uri>` compares checksums rather than sizes and modification times. Use it when you suspect a previous push was interrupted, or when mtimes are unreliable because files were restored from a backup or checked out fresh. Verification is much stronger than the normal comparison and much slower; see the limitations below.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root-level `.tugignore` is consulted; nested ignore files in subdirectories are not read.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding object in the bucket, and nothing in `tug` will ever clean it up. If you need the remote to be an exact mirror, you will have to delete stale objects yourself with another tool.

Files larger than 5 GB cannot be uploaded, because `tug` does not implement multipart upload. Such files are reported as errors and the rest of the push continues.

`verify` fetches the ETag of every object in the target prefix, which costs one request per object and takes a long time on large buckets. On a bucket with hundreds of thousands of objects, expect it to run for minutes rather than seconds, and prefer `status` for routine checks.