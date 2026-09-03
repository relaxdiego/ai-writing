# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: local is the source of truth, the remote is a copy, and nothing that happens in the bucket ever changes what is on your disk. If you want a tool that reconciles two sides and resolves conflicts, this is not it.

## Installing

With a Go toolchain in place, `go install github.com/you/tug@latest` puts the binary in `$GOBIN`. Otherwise download a prebuilt binary for your platform from the releases page, make it executable, and drop it somewhere on your `PATH`; it is a single static file with no runtime dependencies.

## Getting started

Point `tug` at a directory and a bucket and it will upload everything that is missing or out of date:

```
tug push ./site --bucket my-bucket --endpoint https://s3.example.com
```

Before uploading anything you will usually want to see what a push would do, which is what `--dry-run` is for. It walks the same comparison the real push does and prints the list of files it would transfer, without opening a single upload:

```
tug push ./site --bucket my-bucket --dry-run
```

`tug status` gives you the same information in summary form: how many local files are already in sync, how many would be uploaded, and how many bytes that comes to. It is the command to reach for when you want to know whether a push is worth running at all.

## How tug decides what to skip

For each local file, `tug` compares its size and modification time against the corresponding remote object and skips the upload when both match. This makes repeat pushes cheap, because an unchanged tree costs one listing of the bucket and no transfers, but it is a heuristic rather than a proof. A file that was rewritten with identical size and had its mtime restored will look unchanged, and a file whose mtime was bumped without any edit will be re-uploaded needlessly.

`tug verify` exists for the cases where you need certainty. It compares checksums instead of timestamps, fetching each object's ETag and checking it against the local content, and reports any file whose bytes differ from what the bucket holds. Run it after a migration, after a push that was interrupted, or on a schedule if the data matters enough.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, a plain key-value file:

```
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.example.com
region = us-east-1
```

Anything set in the environment takes precedence over the file, so `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` and `TUG_ENDPOINT` are the right way to supply secrets in CI, where writing them to disk is awkward. The file should be mode `0600`; `tug` refuses to read it if the permissions are wider than that.

## Ignoring files

A `.tugignore` file at the root of the directory being pushed excludes paths from every command, using gitignore syntax: one pattern per line, `#` for comments, `!` to negate an earlier pattern, a trailing slash to match directories only. Ignored files are invisible to `push`, `status` and `verify` alike, so a file you exclude after uploading it will stay in the bucket untouched rather than being reported as drift.

```
node_modules/
*.log
.DS_Store
!important.log
```

## Limitations

There is no delete propagation. Removing a file locally leaves the object in the bucket, and `tug` will not mention it, so a bucket that has been pushed to for a long time will accumulate objects with no local counterpart. Cleaning those up is a manual job for now.

Multipart upload is not implemented, which caps a single file at the 5GB limit for a one-shot S3 PUT. Files above that size fail with an error rather than uploading partially, so a tree containing one oversized file will still push everything else.

`verify` is slow on large buckets. It fetches the ETag for every object rather than relying on the listing, so its cost grows with the number of objects and it is best run against a subtree or on a schedule rather than in the middle of a deploy.