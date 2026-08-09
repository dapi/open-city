---
doc_kind: process
doc_function: canonical
context: automation_platform
purpose: Reproducible voice generation workflow.
status: active
---

# Voice production

1. Validate timeline and speaker map.
2. Run `make generate` with the required API key.
3. Inspect cues, duration and clipping.
4. Copy only approved deliverables to the episode's approved audio area.
5. Write the voice manifest with inputs, settings, tool version and checksums.
