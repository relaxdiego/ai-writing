# tug

`tug` pushes a local directory into an S3-compatible bucket. It is one-way only: the local tree is the source of truth, the bucket is a copy, and nothing ever comes back down. On each run `tug` compares every local file against the object stored under the same key and uploads only those whose size or modification time differs from the remote, so pushing an unchanged tree a second time transfers nothing and costs one listing request.

## Installing

With a Go toolchain (1.21 or newer):

```
go install github.com/tug-cli/tug@latest
```

Prebuilt binaries for Linux, macOS and Windows are attached to each release. Download the archive for your platform, extract it, and put `tug` somewhere on your `PATH`:

```
curl -sSL https://github.com/tug-cli/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Commands

### `tug push`

Uploads everything in the local directory that the bucket does not already have in the same form.

```
tug push ./site s3://my-bucket/site
```

Files are matched to objects by their path relative to the local directory, appended to the destination prefix, so `./site/img/logo.png` becomes `s3://my-bucket/site/img/logo.png`. A file is skipped when its size matches the remote object's `Content-Length` and its modification time matches the mtime `tug` recorded on upload. Anything else is uploaded, including files whose contents changed without the size changing, since the mtime moves as well.

Pass `--dry-run` to see the exact set of uploads without performing any of them:

```
tug push --dry-run ./site s3://my-bucket/site
```

### `tug status`

Compares the local directory against the bucket and prints a summary of the difference: how many files would be uploaded, how many are already current, and how many objects exist remotely with no local counterpart. It uploads nothing. Use it for a quick sense of how far the two have drifted; use `push --dry-run` when you want the individual filenames.

```
tug status ./site s3://my-bucket/site
```

### `tug verify`

Checks that what is in the bucket is genuinely what is on disk, by comparing checksums instead of size and mtime. This catches the cases the mtime heuristic cannot: a truncated upload, an object edited by another tool, a file restored from backup with its timestamp preserved but its contents altered.

```
tug verify ./site s3://my-bucket/site
```

`verify` exits non-zero if any object's checksum disagrees with the local file, which makes it usable as a post-deploy gate in CI. Read the note on its cost under [Limitations](#limitations) before running it against a large bucket on every build.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```ini
[default]
access_key_id = AKIAIOSFODNN7EXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1
endpoint = https://s3.us-east-1.amazonaws.com

[backblaze]
access_key_id = 0026f1b...
secret_access_key = K002...
region = us-west-004
endpoint = https://s3.us-west-004.backblazeb2.com
```

Select a section other than `[default]` with `--profile backblaze`. The file must not be readable by other users; `tug` refuses to start if its mode is broader than `0600`.

Environment variables take precedence over the file, which is usually what you want in CI, where no credentials file exists at all:

| Variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | Access key |
| `AWS_SECRET_ACCESS_KEY` | Secret key |
| `AWS_REGION` | Region, where the provider requires one |
| `AWS_ENDPOINT_URL` | Endpoint, for non-AWS providers |

## Ignoring files

If a file named `.tugignore` sits at the root of the local directory, `tug` reads it before every command and excludes matching paths from uploads, from `status` counts, and from `verify`. The syntax is gitignore's, including `#` comments, `!` negation, trailing-slash directory matches, and `**` for spanning directories:

```
# build artefacts
node_modules/
dist/
*.log

# but keep the one log we publish
!dist/build.log
```

Ignored files are never deleted or otherwise touched remotely. A file that was pushed before you added it to `.tugignore` stays in the bucket, and you will need to remove it by hand.

## Limitations

These are known and worth reading before you rely on `tug` for anything important.

- **No delete propagation.** Removing a file locally does not remove the object from the bucket. Objects accumulate, and a bucket that has been pushed to for a long time will hold keys that no longer correspond to anything on disk. Run `tug status` to see the count of remote-only objects, then delete them with your provider's own tooling.
- **No multipart upload.** Files larger than 5 GB exceed the single-`PutObject` limit and will fail, as will smaller files on providers with a lower per-request ceiling. Split such files or upload them separately.
- **`verify` is slow on large buckets.** It fetches the ETag of every object individually rather than relying on the listing, so its runtime and request count both grow linearly with object count. On a bucket of a few hundred thousand keys this takes minutes and shows up on your bill. Reserve it for scheduled checks rather than running it after each push.

A last caution on the mtime heuristic behind `push` and `status`: it assumes local modification times move forward when contents change. Tools that restore timestamps, and filesystems mounted with coarse timestamp granularity, can defeat it and leave a changed file unsent. `verify` is the check that catches this.

---

The tool's specifics you did not pin down are filled in above with the conventional choices: the module path, the `local-dir → s3://bucket/prefix` argument form, the INI shape of the credentials file, the `AWS_*` variable names, the `--profile` flag, and `verify`'s non-zero exit on mismatch. Adjust them to match the implementation.