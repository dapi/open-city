---
doc_kind: governance
doc_function: canonical
context: knowledge_provenance
purpose: Правила authority, canonical ownership и dependency graph документов.
derived_from:
  - principles.md
status: active
source_material:
  - https://github.com/dapi/memory-bank/blob/main/memory-bank/dna/governance.md
---

# Governance базы знаний

## Authority

1. Authoritative только документы со `status: active` и `doc_function: canonical`.
2. `draft` может предлагать изменение, но не переопределяет active canonical owner.
3. Если документы конфликтуют, сначала применяется явный `canonical_for`, затем
   dependency graph: authority течёт от upstream к downstream.
4. Raw sources никогда не выигрывают конфликт автоматически. Они используются как
   evidence для обновления canonical owner.
5. Публикационный `status` документа отделён от состояния эпизода, исследования или ADR.

## Canonical owners студии

| Тип факта | Владелец |
|---|---|
| миссия, operating rules, роли агентов | Studio OS governance |
| мир, персонажи, tone, визуальные правила | Project canon |
| scope и состояние конкретного эпизода | Episode spec/manifest |
| принятое архитектурное решение | ADR |
| интерфейс между агентами/этапами | Contract/schema |
| поведение automation | Код и тесты |
| происхождение утверждения | Knowledge source + provenance record |
| результат конкретного запуска | Run/release manifest |

## Dependency graph

- `derived_from` перечисляет только прямые semantic upstream-документы.
- Корень локального governance graph — `principles.md`; у него нет `derived_from`.
- У каждого active non-root governance-документа `derived_from` обязателен.
- Циклы запрещены. Ссылка для навигации не обязана быть semantic dependency.
- Изменение upstream требует проверки всех downstream-документов.

## Типы документов

Рекомендуемые `doc_kind`: `governance`, `studio`, `project`, `canon`, `episode`,
`research`, `source`, `engineering`, `ops`, `adr`, `prompt`, `process`.

Рекомендуемые `doc_function`: `canonical`, `index`, `template`, `derived`, `reference`,
`contract`, `manifest`, `roadmap`, `decision_log`, `risk_register`.

`context` должен указывать один основной semantic context документа:
`studio_os`, `open_city_canon`, `episode_production`, `automation_platform`,
`distribution_learning` или `knowledge_provenance`.
