A README needs names for things the description leaves open, so I've supplied the credentials-file keys, the environment variable names, and the argument shape for `push`; adjust those to match what the tool actually does.

---

# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way only: files travel from local to remote, and nothing on the remote is ever copied back or removed. Before uploading anything it compares each local file against the corresponding remote object and skips the ones whose size and modification time already match, so running a push twice over an unchanged tree transfers no data.

## Installation

With a Go toolchain installed:

```
go install github.com/you/tug@latest
```

Otherwise download the prebuilt binary for your platform from the releases page, make it executable, and put it somewhere on your `PATH`.

## Credentials

`tug` looks for `~/.tug/credentials`, a plain key-value file:

```
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.example.com
region = us-east-1
```

The same four values can be supplied as `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. Environment variables take precedence over the file, one key at a time, so you can keep long-lived credentials on disk and override just the endpoint for a staging run. If a value is missing from both sources `tug` exits before contacting the network and names the value it could not find.

## Commands

```
tug push [--dry-run] <directory> <bucket>[/prefix]
tug status <directory> <bucket>[/prefix]
tug verify <directory> <bucket>[/prefix]
```

`push` walks the directory, uploads every file that is new or whose size or mtime differs from the remote object, and leaves everything else alone. Passing `--dry-run` performs the whole comparison and prints the uploads it would make without opening a single write, which is the safe way to check a prefix before committing to it.

`status` runs the same comparison and reports a summary of how far the local tree has drifted from the bucket. It differs from `--dry-run` in what it prints rather than in what it does: `status` gives you counts and total bytes, and a dry-run push gives you the per-file list.

`verify` exists because size and mtime can agree while contents do not, which happens after an interrupted upload or a file that was restored from backup with its timestamp preserved. Instead of trusting metadata it fetches each object's ETag and compares it against a checksum of the local file, then reports any pair that disagrees. It does not upload anything; use `push` afterwards to repair what it finds.

## Ignoring files

If a file called `.tugignore` is present at the root of the directory being pushed, `tug` reads it as a gitignore-syntax pattern list and excludes matching paths from every command. Ignored files are not uploaded, not counted by `status`, and not checked by `verify`.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, and there is no flag to change that, so a bucket that has been pushed to for a long time accumulates objects for paths that no longer exist.

Files larger than 5GB cannot be uploaded, because `tug` issues a single PUT per object and has no multipart support. Such a file is reported as an error and skipped; the rest of the push continues.

`verify` is slow on large buckets. It fetches the ETag of every object under the prefix, so its cost scales with the size of the bucket rather than with the number of files that changed, and on a bucket of any real size it is a deliberate periodic check rather than something to run before each push.