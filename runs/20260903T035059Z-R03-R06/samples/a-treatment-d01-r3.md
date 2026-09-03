# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way only: the local tree is the source of truth, nothing on the remote is ever copied back down, and no local file is ever modified. Before uploading, `tug` compares each file's size and modification time against the corresponding remote object and skips the ones that match, so a second run over an unchanged tree costs little beyond the listing request.

## Install

With a Go toolchain:

```
go install github.com/example/tug@latest
```

Otherwise download the binary for your platform from the releases page and put it anywhere on your `PATH`. There is nothing else to install; `tug` is a single static binary with no runtime dependencies.

## Commands

`tug push [directory]` walks the directory, compares it against the bucket, and uploads everything that is new or changed. Passing `--dry-run` prints the same upload plan without transferring anything, which is worth doing the first time you point `tug` at an unfamiliar bucket.

```
tug push ./site
tug push ./site --dry-run
```

`tug status` reports the difference between the local directory and the bucket using the same size-and-mtime comparison, without uploading. Use it when you want to know whether a push is needed at all.

`tug verify` compares checksums rather than modification times. A file that was touched but not edited looks changed to `push` and `status`; a file that was edited and then had its mtime restored looks unchanged to them. `verify` answers the question those two cannot, at the cost of reading every local file and fetching every remote ETag.

## Configuration

`tug` reads credentials from `~/.tug/credentials`, which is a plain INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
bucket = my-bucket
```

Select a profile with `--profile`, or leave it out to use `default`. The same values can come from the environment as `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, `TUG_REGION` and `TUG_BUCKET`, which is the easier route inside CI. Environment variables take precedence over the credentials file, and command-line flags take precedence over both. The credentials file must not be group- or world-readable; `tug` refuses to start if it is.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it as gitignore syntax: one pattern per line, `#` for comments, a leading `!` to re-include something an earlier pattern excluded, and a trailing `/` to match directories only. Ignored files are not uploaded and are not counted by `status` or `verify`.

```
node_modules/
*.log
!important.log
.DS_Store
```

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket, so a bucket that has been pushed to for a while accumulates objects that no longer correspond to anything on disk; clearing those out is a manual job for now.

Files larger than 5 GB fail, because `tug` uploads with a single `PutObject` call and does not implement multipart upload. The failure is reported per file and does not abort the rest of the push.

`verify` is slow on large buckets. It fetches the ETag of every object individually rather than relying on the listing, which means one request per object and a run time that grows linearly with the size of the bucket rather than with the size of your change. On a bucket of any real size, prefer `status` for routine checks and save `verify` for when you have a specific reason to distrust the mtimes.