# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way by design: local is the source of truth, the remote is a copy, and nothing on the remote ever changes what is on disk. Files whose size and modification time already match the corresponding remote object are skipped, so a repeat push over an unchanged tree costs one listing and no uploads.

## Installing

With a Go toolchain:

```
go install github.com/you/tug@latest
```

Otherwise download a prebuilt binary from the releases page, unpack it, and put `tug` somewhere on your `PATH`:

```
tar xzf tug_0.4.0_linux_amd64.tar.gz
sudo install tug /usr/local/bin/tug
```

## Getting started

```
cd ~/site
tug push --bucket my-bucket --dry-run
tug push --bucket my-bucket
```

The dry run prints exactly the operations the real push would perform and touches nothing remote, which is the sane way to try `tug` against a bucket you care about.

## Commands

`tug push` walks the working directory, compares each file against the remote object of the same key, and uploads anything whose size or mtime differs. Objects that exist remotely but not locally are left alone.

`tug status` performs the same comparison and reports what a push would do, without uploading. It differs from `tug push --dry-run` only in tone: `status` is meant for reading, and exits non-zero when the tree is out of sync so you can use it in a check.

`tug verify` compares content instead of metadata. It computes a checksum for each local file and fetches the ETag of each remote object, which catches the cases mtime comparison cannot: a file restored from backup with a fresh timestamp but identical bytes, or a truncated upload that happened to land on the same size.

## Credentials

`tug` reads `~/.tug/credentials`, an INI file keyed by profile:

```
[default]
access_key_id = AKIA...
secret_access_key = ...
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Select a profile with `--profile`, or override any field from the environment using `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. Environment variables win over the file, which makes CI configuration a matter of setting three secrets and shipping no config at all. If no endpoint is given, `tug` talks to AWS S3.

## Ignoring files

A `.tugignore` at the root of the directory being pushed excludes paths using gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are invisible to all three commands, so a file excluded after it has already been pushed stays on the remote rather than being cleaned up.

## Limitations

There is no delete propagation. Removing a file locally does not remove the object remotely, and `tug` will not tell you the remote has objects your tree no longer contains. Pruning is a manual job with your provider's tooling.

Files larger than 5 GB fail, because `tug` does not yet implement multipart upload and 5 GB is the single-PUT ceiling in the S3 API. The error is reported per file and the rest of the push continues.

`verify` is slow on large buckets. It issues a request per object to read the ETag, so runtime scales with object count rather than with the number of changed files, and a bucket with hundreds of thousands of keys will take minutes. Run it on a schedule or against a prefix (`tug verify --prefix assets/`) rather than as part of every deploy.