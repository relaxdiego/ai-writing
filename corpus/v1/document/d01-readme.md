---
id: d01
register: document
name: README for a small tool
---
Write a README for a command-line tool called `tug`.

`tug` synchronises a local directory with a remote S3-compatible bucket. It does one-way pushes only (local to remote), skips files whose size and mtime match the remote object, supports `--dry-run`, reads credentials from `~/.tug/credentials` or environment variables, and takes an optional `.tugignore` file using gitignore syntax. It is written in Go and installs via `go install` or a prebuilt binary. It has three commands: `tug push`, `tug status`, and `tug verify` (which compares checksums rather than mtimes).

Known limitations: no delete propagation, no multipart upload for files over 5GB, and `verify` is slow on large buckets because it fetches every object's ETag.
