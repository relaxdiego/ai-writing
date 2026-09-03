# tug

`tug` pushes a local directory to an S3-compatible bucket. It is one-way: local is the source of truth, remote is the copy. Files whose size and modification time already match the remote object are skipped, so repeat pushes only move what changed.

## Install

With Go 1.21 or later:

```
go install github.com/example/tug/cmd/tug@latest
```

Or download a prebuilt binary from the releases page and put it on your `PATH`:

```
curl -L https://github.com/example/tug/releases/latest/download/tug_linux_amd64.tar.gz | tar xz
sudo mv tug /usr/local/bin/
```

## Quick start

```
tug status ./site s3://my-bucket/site      # what would change
tug push ./site s3://my-bucket/site        # send it
tug verify ./site s3://my-bucket/site      # confirm by checksum
```

Every command takes a local directory and a remote prefix, in that order. Add `--dry-run` to `push` to print the upload plan without transferring anything; it is the same listing `status` produces, and it is the safe way to check a new `.tugignore` before trusting it.

## Commands

`tug push` uploads every local file that is missing from the remote or whose size or mtime differs from the remote object's. It never deletes.

`tug status` reports the same comparison without uploading: what is new, what is modified, what is already in sync. It exits non-zero when there is work to do, which makes it usable as a check in a script or a CI step.

`tug verify` compares content rather than metadata. It hashes each local file and compares the digest against the remote object's ETag, catching the case where a file was rewritten with the same size and its mtime was restored, and the case where an upload was silently truncated. Use it when correctness matters more than speed; see the limitations below for what it costs.

## Credentials

`tug` reads credentials from `~/.tug/credentials`, an INI file with one section per profile:

```
[default]
access_key_id = AKIAEXAMPLE
secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
endpoint = https://s3.us-west-002.backblazeb2.com
region = us-west-002
```

Select a non-default section with `--profile <name>`. The file must not be readable by other users; `tug` refuses to start if its mode is looser than `0600`.

The environment variables `TUG_ACCESS_KEY_ID`, `TUG_SECRET_ACCESS_KEY`, `TUG_ENDPOINT` and `TUG_REGION` override the file, one field at a time, which is what you want in CI: keep the endpoint in the file and inject only the secret.

## Ignoring files

If a `.tugignore` file sits at the root of the local directory, its patterns are applied to every path below it. The syntax is gitignore's, including `!` negations, trailing-slash directory matches, and `**`:

```
node_modules/
*.log
.DS_Store
!important.log
```

Ignored files are not uploaded and are not reported by `status` or `verify`. Because `tug` never deletes, adding a pattern after a file has already been pushed leaves the remote copy in place; remove it yourself.

## Limitations

There is no delete propagation. Removing a file locally leaves the remote object where it is, and no flag changes that. If the remote must mirror local exactly, prune it by hand or with your provider's own tooling.

Files larger than 5 GB fail. `tug` uploads each object in a single request, and 5 GB is the S3 limit for that; multipart upload is not implemented.

`verify` is slow on large buckets. It fetches the ETag for every object under the prefix rather than sampling or listing in bulk, so its cost grows with the size of the bucket and not with the size of your change. On a bucket of any real size, run it deliberately rather than on every push.

One further caveat about `verify`: an ETag is only an MD5 digest for objects uploaded in one piece. Objects that were put there by another tool using multipart upload will carry a composite ETag that no local hash can reproduce, and `tug verify` reports those as mismatches rather than guessing at the part size.