# tug

`tug` pushes a local directory up to an S3-compatible bucket. It is deliberately one-way: files move from your machine to the remote, never the other direction, which makes it a reasonable fit for publishing build artefacts, backing up a working directory, or keeping a static site in sync without the risk that a remote change quietly overwrites your local copy.

The sync itself is incremental. Before uploading anything, `tug` compares each local file's size and modification time against the corresponding remote object and skips the ones that match, so a second push over an unchanged tree costs little more than the listing request. When mtimes are unreliable — files restored from a backup, checked out fresh from version control, or written by a build system that stamps them — `tug verify` does the same comparison against checksums instead.

## Installation

With a Go toolchain:

```
go install github.com/yourorg/tug@latest
```

Otherwise download a prebuilt binary from the releases page and put it somewhere on your `PATH`:

```
curl -L https://github.com/yourorg/tug/releases/latest/download/tug-linux-amd64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment. The file is INI-style:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION`. Anything set in the environment wins over the file, which is usually what you want in CI.

## Usage

The three commands share the same shape — a local directory and a bucket destination:

```
tug push ./site s3://my-bucket/prefix
tug status ./site s3://my-bucket/prefix
tug verify ./site s3://my-bucket/prefix
```

`push` uploads everything that differs and reports what it sent. `status` performs the same comparison but uploads nothing, so it answers "what would change if I pushed right now" without touching the bucket. `verify` fetches each remote object's ETag and compares it against a locally computed checksum, which catches corruption and interrupted uploads that a size-and-mtime check would pass over.

Add `--dry-run` to `push` when you want the upload plan printed without the uploads happening:

```
tug push --dry-run ./site s3://my-bucket/prefix
```

## Ignoring files

If a `.tugignore` file exists at the root of the directory you are pushing, `tug` reads it using gitignore syntax — the same globs, the same `!` negation, the same directory-suffix rules:

```
node_modules/
*.log
.DS_Store
!important.log
```

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object in place, and you will need to delete it through another tool or the provider's console. This is intentional for now, since one-way sync with automatic deletion is an easy way to lose data to a mistyped path.

Files larger than 5GB will fail to upload, as multipart upload is not yet implemented and 5GB is the single-request ceiling for most S3 implementations.

Finally, `verify` is slow against large buckets. It issues a request per object to read the ETag, so a bucket with a hundred thousand objects takes a correspondingly long time. Use `status` for routine checks and reach for `verify` when you have a specific reason to distrust the mtime comparison.