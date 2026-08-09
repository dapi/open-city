# Архив проекта ChatGPT «OpenCity. Сатирический мульт-сериал»

Проект: https://chatgpt.com/g/g-p-69077ed3b480819187025a0a7e47c0b5/project
Выкачано: 2026-08-09 (см. `index.json`).
Повторно сверено с сервером: 2026-08-09 07:53 UTC (см. `verification.json`).

Актуальный серверный endpoint проекта вернул ровно 3 чата и `cursor: null`, то есть
следующей страницы нет. Полные ответы `backend-api/conversation/<id>` семантически
совпадают с локальными raw-дампами. Единственное нестабильное различие — порядок
элементов в служебном множестве `safe_urls`; состав множества совпадает.

## Состав (3 чата — все чаты проекта)

| Чат | Сообщений | Текст | Артефакты |
|---|---|---|---|
| Главная (`69077bb5`) | 583 | 444 384 зн. | 25 ok / 2 мертвы на сервере |
| Эпатажный продюсер-консультант (`69078091`) | 113 | 85 047 зн. | 23 ok / 1 мёртв |
| Роли сотрудников OpenCity (`69086e59`) | 27 | 28 475 зн. | 1 ok |

Итого: 723 сообщения в текущих ветках, 891 узел сообщений с учётом всех сохранённых
ветвлений, 49 файлов (115 141 670 байт). Мёртвые файлы (3 шт.) повторно проверены:
один возвращает `file_not_found`, у двух metadata-endpoint работает, но сами blob-ссылки
возвращают HTTP 404 `BlobNotFound`. Восстановить их с сервера OpenAI сейчас нельзя.

## Структура

- `index.json` — сводный индекс по чатам
- `verification.json` — результат сверки текущего серверного списка, raw-дампов,
  нормализованных сообщений и локальных файлов
- `chats/<id>.json` — сообщения (role, text, attachments, thoughts, citations) + реестр артефактов
- `chats/<id>.raw.json` — полный ответ `backend-api/conversation/<id>` (mapping со всеми ветками)
- `artifacts/<id>/` — файлы с настоящими именами (картинки, PDF, видео, скриншоты)

Примечание: файлы вида `chats/<id>.json` со схемой `{id, source, fetchedAt, data}`,
`artifacts/a-*`, `textdocs/`, `*.zip`, `project_archive_manifest.json` — от другого
параллельного процесса выкачки (00:20–00:22). Он ошибочно собрал 25 ссылок из общей
боковой панели ChatGPT вместе с 3 чатами проекта. Эти 25 дампов не имеют project
`gizmo_id` и не входят в актуальный архив проекта; авторитетные списки — `index.json`
и `verification.json`.

## Метод (скрипт `../scripts/chatgpt-export/extract-project-chat.js`)

Самый чистый способ для залогиненных чатов — backend-api, без скролла и DOM:

1. Bearer token: `GET https://chatgpt.com/api/auth/session` → `accessToken`
2. Переписка: `GET /backend-api/conversation/<id>` (заголовок `Authorization: Bearer`) →
   полный `mapping`; линеаризация — от `current_node` вверх по `parent`
3. Файлы: `GET /backend-api/files/<file_id>/download` → подписанный `download_url`
   (estuary с `sig`/`ts`/`p`) → байты
4. Важно: `download_url` требует кук — скачивать в контексте страницы, в Node передавать
   base64-чанками по ~500 КБ. Прямой `estuary/content?id=...` без подписи даёт HTTP 422.

Запуск (через playwriter, Chrome с залогиненным ChatGPT):

```bash
playwriter -s <session> -e 'state.chatId = "<conversationId>"' --timeout 15000
scripts/chatgpt-export/pw-long.sh <session> scripts/chatgpt-export/extract-project-chat.js
```

`pw-long.sh` снимает 5-минутный лимит CLI→relay запроса (см. патч
`../scripts/chatgpt-export/playwriter-long-fetch.cjs`) и ставит `--timeout 1 ч`
(можно больше аргументом).

Экспортёр декодирует каждый base64-чанк отдельно и проверяет итоговый размер файла.
Это обязательная защита от тихого обрезания вложений на первом чанке в 500 000 байт.
