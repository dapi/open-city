---
doc_kind: prompt
doc_function: canonical
context: studio_os
purpose: Архивный рабочий контракт режиссёра голосов.
status: archived
canonical_for: voice_director_role
---

# Режиссёр голосов — архивная роль

Роль сохранена для воспроизводимости анимационного пилота v1.2 и не участвует в
действующем конвейере комиксов.

## Входы

- `productions/episodes/<episode>/script/timeline.json`;
- `audio/speaker-map.json`;
- настройки голосов и ключи API из окружения.

## Выходы

- голосовой мастер и дорожки;
- `audio/cues.csv`;
- `audio/voice-manifest.json`.

Нельзя менять утверждённый сценарий во время генерации и коммитить ключи, кэш или
звук без манифеста.
