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

Каталог описывает воплощения героев в мире комикса. Одноимённые сотрудники
StudioChat — те же творческие идентичности в другом контексте; связь задаётся через
`identity_id` и `studio_chat_persona_id`. Их производственные роли и правила речи
определяются в `channels/studio-chat/participants/`.

`archive_visual_references` хранит происхождение старых портретов ChatGPT. Все такие
ссылки имеют статус `source_only`: это материал для сравнения и разработки, а не
утверждённый мастер персонажа.
