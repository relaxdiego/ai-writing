A README is a document people scan and return to, so I've used headings and one table. A few details weren't in your description and I had to pick something concrete: the module path, the credentials file format and the environment variable names, and the argument shape of the commands. Those are marked below the README so you can correct them against the real code.

```markdown
# tug

`tug` copies a local directory up to an S3-compatible bucket and keeps it
current. It pushes in one direction only. Your local files are the source of
truth, the bucket is a copy of them, and no tug subcommand will ever write to,
move, or delete anything on your disk.

On each push, tug walks the local directory and compares every file against the
object already in the bucket. If the size and modification time match, the file
is skipped and nothing goes over the network; otherwise it is uploaded, replacing
whatever was there. For a directory that mostly sits still, this makes repeat
pushes cheap: the cost is one listing of the remote prefix plus the bytes of
whatever actually changed.

## Installation

With a Go toolchain:

    go install github.com/yourname/tug@latest

Or download a prebuilt binary for your platform from the releases page, unpack
it, and put `tug` somewhere on your `PATH`:

    tar xzf tug_0.4.0_linux_amd64.tar.gz
    sudo install tug /usr/local/bin/tug

## Credentials

tug reads credentials from `~/.tug/credentials`, an INI file with one section
per profile:

    [default]
    access_key_id     = AKIAEXAMPLE
    secret_access_key = wJalrXUtnFEMI/K7MDENG/EXAMPLEKEY
    endpoint          = https://s3.us-west-002.backblazeb2.com
    region            = us-west-002

Select a non-default section with `--profile`. Because the file holds secrets,
tug refuses to read it if it is group- or world-readable; `chmod 600
~/.tug/credentials` if it complains.

Every setting can also come from the environment, and the environment wins over
the file:

    TUG_ACCESS_KEY_ID
    TUG_SECRET_ACCESS_KEY
    TUG_ENDPOINT
    TUG_REGION

That precedence is what makes tug usable from CI, where you can leave the
credentials file absent entirely and inject the four variables as secrets.

## Commands

All three commands take the same two arguments, a local directory and a
destination, and all three respect `.tugignore`. They differ in what they
compare and whether they are allowed to write:

| Command | Compares | Writes to the bucket |
| --- | --- | --- |
| `tug push` | size and mtime | yes |
| `tug status` | size and mtime | no |
| `tug verify` | checksums | no |

### tug push

    tug push ./site my-bucket/blog

Uploads every local file whose size or mtime differs from the corresponding
object. Add `--dry-run` to print exactly the same plan without opening a single
upload:

    tug push --dry-run ./site my-bucket/blog

### tug status

    tug status ./site my-bucket/blog

Reports what a push would do, grouped into files that are new, files that
changed, and files that are already current. `status` is `push --dry-run`
without the risk of forgetting the flag, so it is the safer thing to put in a
shell alias or a pre-deploy check.

### tug verify

    tug verify ./site my-bucket/blog

Confirms that the bucket really holds what you think it does. Rather than
trusting size and mtime, `verify` fetches each object's ETag and compares it to
a checksum computed from the local file, which catches the cases the mtime
heuristic cannot: a truncated upload, a file edited in place and then restored
to its old timestamp, or an object changed by something other than tug. Run it
after any push you care about, and read the section on limitations first if the
bucket is large.

## .tugignore

If the local directory contains a `.tugignore` file at its root, tug reads it
and excludes matching paths from every command. The syntax is gitignore's,
including negation, directory-only patterns, and `**`:

    # build output
    dist/
    *.tmp

    # keep the checked-in fixtures even though *.tmp excludes them
    !testdata/golden.tmp

Excluded files are not uploaded, and they are also not reported by `status` or
`verify`. An object already in the bucket that later becomes ignored is left
alone; tug will not delete it.

## Limitations

- **No delete propagation.** Removing a file locally does not remove the object
  remotely. The bucket accumulates everything you have ever pushed, and pruning
  it is a manual job with another tool.
- **No multipart upload.** Files larger than 5 GB exceed the single-request
  limit and will fail the push outright. Split them or exclude them.
- **`verify` is slow on large buckets.** It issues a request per object to read
  the ETag, so wall-clock time grows linearly with object count and the run is
  dominated by round trips. On a bucket with hundreds of thousands of objects,
  expect minutes to hours; prefer `status` for routine checks and save `verify`
  for releases or for investigating a specific suspicion.

One consequence of the mtime heuristic deserves stating on its own: a file whose
contents change while its size and modification time stay the same will be
skipped by `push` forever. Restoring timestamps from a backup or an archive is
the usual way this happens. `tug verify` is the only command that will notice.
```

The placeholders to check are the module path `github.com/yourname/tug`, the INI keys and the `TUG_*` variable names, the `--profile` flag, and the `<local-dir> <bucket>/<prefix>` argument order. I also asserted that the credentials file must not be group-readable and that ignored-but-already-uploaded objects are left in place; both follow from what you described, but neither was stated, so drop them if the implementation disagrees.