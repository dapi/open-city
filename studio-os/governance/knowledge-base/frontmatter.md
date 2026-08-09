---
doc_kind: governance
doc_function: canonical
context: knowledge_provenance
purpose: Минимальная frontmatter schema для governed-документов студии.
derived_from:
  - governance.md
status: active
source_material:
  - https://github.com/dapi/memory-bank/blob/main/memory-bank/dna/frontmatter.md
---

# Frontmatter schema

## Обязательные поля

| Поле | Значения | Назначение |
|---|---|---|
| `doc_kind` | enum из governance | Тип знания |
| `doc_function` | enum из governance | Роль документа |
| `context` | один bounded context | Где действуют термины и правила |
| `purpose` | короткая строка | Зачем существует документ |
| `status` | `draft`, `active`, `archived` | Публикационная authority |

## Условно обязательные поля

| Поле | Когда требуется |
|---|---|
| `derived_from` | Есть semantic upstream; обязательно для active non-root governance docs |
| `canonical_for` | Документ владеет явно ограниченным классом фактов |
| `decision_status` | ADR: `proposed`, `accepted`, `superseded`, `rejected` |
| `delivery_status` | Lifecycle owner production item: `planned`, `in_progress`, `done`, `cancelled` |
| `research_status` | Lifecycle owner исследования |
| `source_url`, `captured_at` | Внешний или динамический source snapshot |
| `verified_at`, `verification_method` | Source заявлен как проверенный |

`derived_from` содержит путь либо объект `{path, fit}`, где `fit` ограничивает область
заимствования. Обычная навигационная ссылка не создаёт dependency.

Допустимое поле `audience`: `humans` или `humans_and_agents`. Документ для автоматического
использования агентами не должен семантически зависеть от human-only инструкции, если
машинно-проверяемый contract отсутствует.

## Минимальный пример

```yaml
---
doc_kind: episode
doc_function: canonical
context: episode_production
purpose: Scope и acceptance criteria пилотного эпизода.
canonical_for: pilot-v1.2
derived_from:
  - ../../../projects/open-city/canon/project-bible.md
status: active
delivery_status: in_progress
audience: humans_and_agents
---
```
