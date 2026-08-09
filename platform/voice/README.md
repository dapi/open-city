---
doc_kind: engineering
doc_function: index
context: automation_platform
purpose: Voice synthesis tooling and tests.
status: active
---

# Voice platform

`generate.py` is the stable entry point; its current implementation is kept in
`generate_v2.py`. `legacy/generate_v1.py` is the older explicit-ID implementation.
New pipeline changes must preserve the episode manifest contract.

Install dependencies with `make deps`. The CLI supports `--help` without installed
runtime dependencies and reports the missing package when a render is attempted.
