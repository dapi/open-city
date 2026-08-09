---
doc_kind: governance
doc_function: canonical
context: knowledge_provenance
purpose: Правила навигации между знаниями, кодом и production artifacts.
derived_from:
  - principles.md
status: active
source_material:
  - https://github.com/dapi/memory-bank/blob/main/memory-bank/dna/cross-references.md
---

# Cross-references

Цель — пройти цепочку в обе стороны: source → решение → реализация → run → evidence.

## Docs → docs

- Canonical документ перечисляет прямые upstream через `derived_from`.
- Индекс использует аннотированные ссылки и задаёт reading order.
- Downstream не копирует upstream-факт без ссылки и fit-ограничения.

## Code → docs

Модуль, реализующий contract или архитектурное решение, содержит относительную ссылку
от корня репозитория и поясняет, какой аспект документа реализован.

## Docs → code/tests

Design, ADR или contract может ссылаться на реализацию и тесты. Ссылка объясняет,
что именно подтверждает файл; номер строки добавляется только когда достаточно стабилен.

## Production artifacts → manifests

- Episode/release manifest перечисляет входы, версии инструментов, outputs и checksums.
- Бинарный файл без manifest считается неуправляемым артефактом.
- Raw source содержит provenance к внешней системе и времени получения.

## Запрещённые замены

- Навигационная ссылка не заменяет `derived_from`.
- Имя папки не доказывает authority.
- Совпадающее имя файла не доказывает, что это одна версия сущности.
