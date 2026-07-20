# Security Policy

Skrybe Studio is currently an early-stage, private-development desktop application
(v0.1.0). It has no network services and no remote/client-server architecture; it reads
and writes local project files and a local SQLite database.

## Reporting a vulnerability

If you discover a security issue (e.g. path traversal via asset import, unsafe deserialization,
or a way for a malicious plugin manifest to escape its intended sandboxing), please report it
privately rather than opening a public issue:

- Open a [private security advisory](https://github.com/adeptus-craftmatica/skrybe-studio/security/advisories/new)
  on this repository, or
- Contact the repository owner, [`adeptus-craftmatica`](https://github.com/adeptus-craftmatica),
  directly.

Please include:

- A description of the issue and its potential impact.
- Steps to reproduce, or a minimal proof of concept.
- The version/commit you tested against.

## Supported versions

While the project is pre-1.0, only the latest commit on `main` is supported.

## Scope notes for this iteration

- Plugin manifests are loaded from the local filesystem only; there is no remote plugin
  installation mechanism yet.
- Imported assets are copied into the project's managed `assets/` directory using
  UUID-based filenames; the application does not execute imported files.
- Secrets must never be stored via the settings system (`core/settings`) - it is a plain
  JSON store, not a credential vault.
