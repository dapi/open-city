---
doc_kind: source
doc_function: index
context: knowledge_provenance
purpose: Индекс полнотекстовых Markdown-представлений скачанных чатов ChatGPT OpenCity.
status: active
derived_from:
  - ../../../sources/chatgpt/open-city/archive/index.json
audience: humans_and_agents
---

# Поисковые транскрипты архива ChatGPT OpenCity

Это воспроизводимая Markdown-проекция неизменённого JSON-архива. Она удобна для
полнотекстового поиска, но не является каноном проекта или заменой raw-источника.
Каждый уникальный узел сообщения представлен один раз: сначала текущая ветка,
затем сохранённые ответвления с указанием родителя.

| Чат | Текущая ветка | Сохранённые ветки | Всего |
|---|---:|---:|---:|
| [Главная](main.md) | 583 | 55 (5 корн.) | 638 |
| [Эпотажный продюсер-консультант](producer-consultant.md) | 113 | 113 (2 корн.) | 226 |
| [Роли сотрудников OpenCity](studio-roles.md) | 27 | 0 (0 корн.) | 27 |
| **Итого** | **723** | **168** | **891** |

## Как искать

```bash
rg -n -i 'личка|ошибка человека|минус-контент' knowledge/research/open-city-chat-archive/transcripts
rg -n '7d6799d9-d599-4388-9391-d1ac76a5fe9a' knowledge/research/open-city-chat-archive/transcripts
```

Служебные внутренние рассуждения модели намеренно не копируются; их узлы и
метаданные остаются видимыми, а первичное содержимое хранится только в raw JSON.
