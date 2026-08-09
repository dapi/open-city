---
doc_kind: governance
doc_function: canonical
context: studio_os
purpose: Minimum quality gates for production handoffs.
derived_from:
  - knowledge-base/principles.md
status: active
canonical_for: studio_quality_gates
---

# Quality gates

An agent may mark a handoff ready only when the input and output files are listed
in the relevant manifest.

1. **Script** — approved text, speaker names and timeline are internally consistent.
2. **Voice** — all speakers resolve, audio is readable, cues and subtitles exist,
   and no secret or local cache is included.
3. **Animation** — shot list references approved audio and render settings are explicit.
4. **Release** — final media, subtitles, metadata and checksums are recorded.
5. **Retro** — deviations and next actions are captured after release.
