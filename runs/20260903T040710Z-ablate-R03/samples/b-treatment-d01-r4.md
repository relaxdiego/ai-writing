```markdown
# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: the local
tree is the source of truth, and the remote is a copy of it. Files whose size and modification time
already match the remote object are skipped, so a repeated push over an unchanged tree costs a
listing and nothing more.

## Installation

With a Go toolchain (1.21 or newer):

```
go install github.com/example/tug/cmd/tug@latest
```

Otherwise download a prebuilt binary for your platform from the releases page, extract it, and put
it somewhere on your `PATH`:

```
curl -sSL https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, then falls back to the environment. The
file is INI-style and may hold several profiles; the one named `default` is used unless you pass
`--profile`:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`,
`TUG_ENDPOINT` and `TUG_REGION`. Because the endpoint is configurable, `tug` works against MinIO,
Backblaze B2, Cloudflare R2, Wasabi and anything else that speaks the S3 API; if you leave the
endpoint unset it talks to AWS S3 directly. Keep the credentials file at mode `0600`, since `tug`
refuses to read it if it is group- or world-readable.

## Usage

Each command takes a local directory and a remote target of the form `s3://bucket/optional/prefix`.

```
tug push ./site s3://my-bucket/site
tug status ./site s3://my-bucket/site
tug verify ./site s3://my-bucket/site
```

`push` uploads every local file that is missing from the remote or whose size or mtime differs from
the remote object, and reports a count of uploaded, skipped and failed files when it finishes.
Passing `--dry-run` performs the same comparison and prints exactly what would be uploaded without
writing anything, which is the safest way to sanity-check a new prefix or a freshly written
`.tugignore`.

`status` is a read-only summary of the same comparison. It tells you how many files would be
uploaded and how many are already current, without listing each one, so it is cheap enough to run
from a prompt or a cron job.

`verify` is the stricter check. Instead of trusting size and mtime it fetches each remote object's
ETag and compares it against a checksum computed from the local file, which catches truncated
uploads, silent corruption, and files that were edited in place without their mtime changing. Use
it after a large migration or when you suspect a previous push was interrupted.

## Ignoring files

If a `.tugignore` file exists at the root of the local directory, `tug` reads it and skips matching
paths. The syntax is gitignore syntax, including negation with `!`, directory-only patterns ending
in `/`, and `**` for recursive matches:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are never uploaded and are also excluded from `status` and `verify` counts, so a file
you ignore will not show up as remote drift later.

## How the skip check works

For each local file `tug` compares two things against the remote listing: the object size, and the
mtime it stored as object metadata on the last push. A file is uploaded when either differs or when
no remote object exists. This makes an incremental push fast, but it inherits the usual caveat of
mtime-based synchronisation: a file whose contents change while its size and mtime stay the same
will be treated as current. `verify` exists precisely to find those cases.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding object in the
bucket, and `tug` will not report it as drift. Pruning the remote is currently a manual job.

Files larger than 5 GB cannot be uploaded, because `tug` does not yet implement multipart upload
and 5 GB is the single-request limit imposed by the S3 API. Such files are reported as failures at
the end of a push rather than skipped silently.

`verify` is slow on large buckets. It issues a request per object to read the ETag, so runtime
grows linearly with object count and it is not something to run on every deploy. Reserve it for the
occasions where the mtime heuristic is not good enough.
```

A few details above are conventions I chose rather than facts you gave me: the `s3://bucket/prefix` argument shape, the `--profile` flag, the exact environment variable names, the INI key names in the credentials file, and the permission check on that file. Adjust them to match what the tool actually does.