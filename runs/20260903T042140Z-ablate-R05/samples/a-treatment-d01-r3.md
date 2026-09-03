# tug

`tug` pushes the contents of a local directory into an S3-compatible bucket. It is deliberately one-directional: files move from your machine to the remote and never the other way, which makes it safe to run against a directory you are actively editing and predictable enough to put in a deploy script. On each run it compares every local file against the corresponding remote object and uploads only those whose size or modification time differ, so repeated pushes over a mostly-unchanged tree cost little more than the listing.

## Installation

With a Go toolchain (1.21 or later):

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo install tug /usr/local/bin/tug
```

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a non-default section with `--profile`. Any value in the file can be overridden by the environment, which is usually what you want in CI:

```
export TUG_ACCESS_KEY_ID=...
export TUG_SECRET_ACCESS_KEY=...
export TUG_ENDPOINT=https://nyc3.digitaloceanspaces.com
export TUG_REGION=nyc3
```

Environment variables take precedence over the credentials file. If neither source supplies a key, `tug` exits without contacting the network rather than falling back to anonymous access.

## Commands

`tug push <dir> <bucket>[/prefix]` walks the local directory and uploads everything that differs from the remote. Passing `--dry-run` prints the same report of what would be uploaded, skipped and totalled, but performs no writes; it is worth running the first time you point `tug` at an unfamiliar bucket.

```
tug push ./public assets.example.com/site
tug push ./public assets.example.com/site --dry-run
```

`tug status <dir> <bucket>[/prefix]` compares the two sides and reports the difference without uploading anything. It is the read-only sibling of `push --dry-run` and is the right command for a health check or a pre-commit hook, since it never opens a file for reading beyond its metadata.

`tug verify <dir> <bucket>[/prefix]` performs the stronger check. Rather than trusting size and mtime, it computes a checksum for each local file and compares it against the remote object's ETag, which will catch a truncated upload or a file that was modified in place without its timestamp changing. Because the timestamp heuristic that makes `push` fast is exactly what `verify` refuses to rely on, this command is much slower; run it after an interrupted push or on a schedule, not on every deploy.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore's, including negation with `!`, directory-only patterns with a trailing slash, and `**` for arbitrary depth:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are never uploaded and are not treated as remote-only leftovers, so adding a pattern after a push leaves the already-uploaded objects in place.

## Limitations

There is no delete propagation. Removing a file locally does not remove the corresponding object from the bucket, and `tug` will not report it as a difference. If you need the remote to be an exact mirror, you will have to prune it yourself.

Files larger than 5 GB cannot be uploaded, because `tug` does not yet implement multipart upload and 5 GB is the ceiling for a single `PutObject` request. Such files are reported as errors and skipped; the rest of the push continues.

`verify` scales poorly. It issues a request per object to fetch each ETag, so on a bucket with hundreds of thousands of keys the command can take hours and will generate a corresponding number of billable API calls. Scope it to a prefix when you can.

---

I invented the module path, release URL, credentials-file field names and the `TUG_*` variable spellings, since you didn't specify them; swap in the real ones before publishing.