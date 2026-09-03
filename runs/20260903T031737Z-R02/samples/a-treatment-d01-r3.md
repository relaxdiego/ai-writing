# tug

`tug` pushes the contents of a local directory to an S3-compatible bucket. It is one-way by design: local is the source of truth, the remote is a destination, and nothing ever flows back down. On each run it compares every local file against the corresponding remote object and uploads only those whose size or modification time differ, so repeated pushes over a mostly-unchanged tree cost little more than the listing itself.

## Install

With a Go toolchain (1.21 or newer):

```
go install github.com/example/tug/cmd/tug@latest
```

Or download a prebuilt binary for your platform from the releases page and drop it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Quick start

Point `tug` at a directory and a bucket, and check what it would do before letting it do anything:

```
tug push ./site s3://my-bucket/assets --dry-run
```

The dry run prints the same upload plan the real run would execute, marking each file as `upload`, `skip`, or `ignore`, and finishes with a summary of how many bytes would cross the wire. Drop `--dry-run` and the plan is carried out.

## Commands

`tug push <dir> s3://<bucket>[/<prefix>]` walks the local directory, compares each file against the remote object at the matching key, and uploads the ones that differ. Comparison uses size and modification time only; a file whose contents changed without changing either will be skipped, which is the cost of keeping the common case cheap.

`tug status <dir> s3://<bucket>[/<prefix>]` performs the same comparison and prints the result without uploading anything. It is the read-only sibling of `push --dry-run`, useful in scripts and CI checks where you want a non-zero exit code when local and remote have drifted.

`tug verify <dir> s3://<bucket>[/<prefix>]` checks the two sides properly. Instead of trusting mtimes it fetches each object's ETag and compares it against the checksum of the local file, catching the silent-corruption and same-timestamp cases that `push` deliberately ignores. Run it after a large migration, or on a schedule if the data matters; see the limitations below before running it against a very large bucket.

All three accept `--dry-run` (a no-op for `status` and `verify`, which never write), `--verbose` for per-file logging, and `--concurrency N` to bound parallel transfers.

## Credentials

`tug` looks for credentials in `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a non-default section with `--profile <name>`. Environment variables take precedence over the file, so `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION` are the right way to supply credentials in CI, in containers, or anywhere writing a file to disk would be awkward. Setting the endpoint is what makes `tug` work against MinIO, Backblaze B2, Cloudflare R2, and other S3-compatible services rather than only AWS.

## Ignoring files

If a `.tugignore` file exists at the root of the directory being pushed, `tug` reads it and excludes matching paths. The syntax is gitignore syntax — glob patterns, `!` for negation, a trailing slash to match directories only, and a leading slash to anchor a pattern to the root:

```
node_modules/
*.log
.DS_Store
/build
!/build/index.html
```

Ignored paths are neither uploaded nor considered when comparing against the remote, so a file that was pushed before being added to `.tugignore` will stay on the remote untouched rather than being removed.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding remote object in place, and `tug` will not report it as drift, so a bucket that has been pushed to for a long time accumulates objects with no local counterpart. Pruning those is currently a manual job with your provider's own tooling.

Files larger than 5 GB will fail to upload. `tug` sends each file as a single `PUT`, and 5 GB is the ceiling S3 imposes on that operation; multipart upload is not implemented yet. Splitting or compressing oversized files is the only workaround today.

`verify` is slow on large buckets. Because it fetches an ETag for every object rather than relying on a bulk listing, its runtime scales with object count and it will make one request per file. On a bucket with hundreds of thousands of objects, expect it to take a long time and to generate a correspondingly large number of billable requests — reach for it deliberately rather than wiring it into a frequent job, and scope it to a prefix where you can.

---

A note on what I filled in: you specified the behaviour but not the concrete spellings, so I invented the credential file's INI layout and key names, the `TUG_*` environment variable names, the positional `<dir> s3://<bucket>/<prefix>` argument form, the install URL, and the `--verbose`/`--concurrency`/`--profile` flags. Tell me the real ones and I'll swap them in.