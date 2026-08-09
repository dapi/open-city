---
doc_kind: canon
doc_function: index
context: open_city_canon
purpose: Указать канонический источник публичных профилей героев «Города Нейросеть».
canonical_for: open_city_character_catalog_routing
derived_from:
  - ../project-bible.md
status: active
audience: humans_and_agents
---

# Персонажи мира

Канонический машиночитаемый источник публичных профилей —
[`characters.json`](characters.json). Его структура проверяется контрактом
[`character-catalog.schema.json`](../../../../studio-os/contracts/character-catalog.schema.json).

Страница `/characters/`, карточки, метаданные и другие публикационные представления
собираются из этого файла. Сгенерированный HTML не является источником истины и не
редактируется для изменения фактов о персонажах.

Каталог описывает только героев мира комикса. Одноимённые сотрудники StudioChat
находятся в другом контексте и определяются в `channels/studio-chat/participants/`.
