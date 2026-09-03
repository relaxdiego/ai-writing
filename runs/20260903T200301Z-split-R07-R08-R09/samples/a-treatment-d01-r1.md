# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way by design: local is the source of truth, the remote is a copy, and nothing on the remote ever changes anything on disk. On each run it compares every local file against the corresponding remote object and uploads only those whose size or modification time differ, so a repeat push over an unchanged tree costs a listing and nothing more.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/example/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and put it somewhere on your `PATH`:

```
curl -sSL https://example.com/tug/latest/tug-linux-arm64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in the environment first, then falls back to `~/.tug/credentials`. The environment variables are:

```
TUG_ACCESS_KEY_ID
TUG_SECRET_ACCESS_KEY
TUG_ENDPOINT
TUG_REGION
```

The credentials file uses the same keys in INI form, with one section per profile and `default` used unless `--profile` says otherwise:

```ini
[default]
access_key_id = AKIAIOSFODNN7EXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

The file must not be readable by other users; `tug` refuses to start if its mode is broader than `0600`.

## Commands

`tug push` walks the local directory, skips anything matching `.tugignore`, compares each remaining file against the remote object of the same key, and uploads what differs. The comparison is size and modification time only, which is fast but will miss a file that was edited in place without changing either. Use `verify` when that matters.

```
tug push ./site s3://my-bucket/site
tug push --dry-run ./site s3://my-bucket/site
```

`--dry-run` prints exactly what a real run would upload or skip, and touches nothing. It is worth running the first time you point `tug` at an unfamiliar bucket, since a wrong prefix is otherwise discovered only after the upload.

`tug status` reports the same comparison as `push` without uploading and without the per-file transfer log: a count of files that would be uploaded, files that would be skipped, and files present locally but not remotely. It is the quick answer to whether the two sides have drifted.

```
tug status ./site s3://my-bucket/site
```

`tug verify` compares content rather than metadata. It fetches each remote object's ETag and checks it against a checksum computed from the local file, so it catches in-place edits, partial uploads, and silent corruption that `push` cannot see. It reports mismatches and exits non-zero if it finds any; it does not upload anything.

```
tug verify ./site s3://my-bucket/site
```

## .tugignore

An optional `.tugignore` at the root of the local directory excludes paths from every command, using gitignore syntax: glob patterns, `#` comments, `/` to anchor at the root, `**` to cross directory boundaries, and a leading `!` to re-include something an earlier pattern excluded.

```
# build artefacts
/dist/
*.tmp

# keep the checked-in fixture, drop everything else under testdata
testdata/**
!testdata/fixture.json
```

Excluded files are never uploaded and are also invisible to `status` and `verify`, so an object that already exists remotely will not be reported as drift once its path is ignored.

## Limitations

Three of these are worth knowing before you rely on `tug` for anything:

- **No delete propagation.** Deleting a local file leaves the remote object in place. A bucket that has been pushed to for a long time accumulates every file the directory has ever contained, and neither `status` nor `verify` will tell you about them. Removing them is a manual job.
- **No multipart upload.** Files larger than 5 GB exceed the single-request limit for S3 PUT and will fail. `tug` reports the failure and continues with the rest of the tree rather than aborting the run, so check the exit status.
- **`verify` is slow on large buckets.** It issues a request per object to read the ETag, which means runtime grows linearly with object count and the wall-clock cost is dominated by round trips. On a bucket of any real size, treat it as an occasional audit rather than something to run after every push.