---
doc_kind: adr
doc_function: decision_log
context: studio_os
purpose: Choose a repository structure that is usable by humans and agents.
decision_status: accepted
status: active
derived_from:
  - ../../../docs/architecture/repository-structure-options.md
---

# ADR 0001: Hybrid Studio OS structure

## Decision

Use five explicit zones: `studio-os`, `projects`, `productions`, `platform` and
`knowledge`. Keep one episode's production run together while separating reusable
code, project canon, governance and raw provenance.

## Rationale

This gives agents local context and clear ownership without the navigation cost of
fully isolated bounded-context repositories. Contracts and manifests make handoffs
explicit.

## Consequences

- Canonical files and generated files have different locations.
- Episode runs must contain manifests.
- Runtime media is local/external; Git stores source, metadata and checksums.
