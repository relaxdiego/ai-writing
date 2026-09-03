# tug

`tug` pushes a local directory to an S3-compatible bucket. It is deliberately one-way: files move from your machine to the remote, and nothing on the remote ever comes back down or gets removed. If you want a general-purpose two-way sync tool, this is not it. If you want to shove a build output, a static site, or a backup directory at a bucket and have it finish quickly the second time, that is what `tug` is for.

Files are skipped when the local size and modification time match the remote object's, which makes repeat pushes cheap without hashing anything. When you need a stronger guarantee than mtime can give, `tug verify` compares checksums instead.

## Installing

With a Go toolchain present:

```
go install github.com/example/tug@latest
```

Prebuilt binaries for Linux, macOS, and Windows are attached to each release. Download the one matching your platform, make it executable, and put it somewhere on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64 -o /usr/local/bin/tug
chmod +x /usr/local/bin/tug
```

## Credentials

`tug` looks for credentials in `~/.tug/credentials` first, falling back to the environment. The file is INI-style and may hold several profiles:

```ini
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/EXAMPLEKEY
endpoint = https://s3.us-east-1.amazonaws.com
region = us-east-1
```

Select a non-default profile with `--profile`. The equivalent environment variables are `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT`, and `TUG_REGION`, and any of them override the corresponding value from the file, so you can keep a profile on disk and swap out just the endpoint for a one-off run against a different provider.

## Commands

`tug push <dir> <bucket>[/prefix]` walks the local directory, compares each file against the remote object, and uploads whatever differs. Add `--dry-run` to print the same report without transferring anything; this is worth doing the first time you point `tug` at an unfamiliar bucket, since a mismatched prefix is easier to spot in a listing than to undo afterwards.

`tug status <dir> <bucket>[/prefix]` performs the comparison and reports what a push would do, then exits. It is the read-only sibling of `--dry-run` and takes no upload flags.

`tug verify <dir> <bucket>[/prefix]` re-checks the remote against your local copy using checksums rather than size and mtime. Use it after a push you have reason to distrust, or on a schedule against archival data where silent corruption matters more than speed.

A typical first run looks like this:

```
$ tug push ./public my-site-bucket/assets --dry-run
+ index.html          4.1 KiB
+ css/main.css       12.8 KiB
~ img/logo.png       48.2 KiB   (size differs)
= js/app.js                     (unchanged)
3 to upload, 1 unchanged, 0 errors
```

## Ignoring files

A `.tugignore` file at the root of the directory being pushed excludes paths using gitignore syntax, including negation with `!` and directory-only patterns with a trailing slash:

```
node_modules/
*.log
.DS_Store
!important.log
```

Only the root-level file is read; nested `.tugignore` files in subdirectories are not consulted.

## Limitations

There is no delete propagation. Removing a file locally leaves the corresponding remote object in place, so a bucket that has been pushed to for a long time will accumulate objects that no longer exist on your machine. Clean those up with your provider's tooling or a lifecycle rule.

Multipart upload is not implemented, which caps a single file at 5 GB. Larger files fail with an error rather than uploading partially, so a push containing one will report the failure and continue with the rest.

`verify` fetches every object's ETag individually and is therefore slow on large buckets, roughly in proportion to object count rather than total bytes. On a bucket with hundreds of thousands of small objects, expect it to take minutes and to burn a comparable number of API requests. Scoping it to a prefix is usually the practical answer.