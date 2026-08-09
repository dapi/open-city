# Экспорт проекта ChatGPT

Утилиты в этом каталоге воспроизводимо выгружают полное дерево разговоров проекта
ChatGPT через авторизованную вкладку Chrome и Playwriter.

- `extract-project-chat.js` сохраняет raw `mapping`, текущую ветку сообщений и вложения.
- `convert-to-markdown.py` строит полнотекстовые Markdown-проекции всех текущих и
  сохранённых веток, не меняя архив.
- `pw-long.sh` запускает длительную выгрузку без стандартного пятиминутного лимита.
- `playwriter-long-fetch.cjs` снимает сетевой таймаут CLI для длительного запуска.

Пример:

```bash
playwriter -s <session> -e 'state.chatId = "<conversationId>"'
scripts/chatgpt-export/pw-long.sh \
  <session> scripts/chatgpt-export/extract-project-chat.js
```

Результат записывается в `knowledge/sources/chatgpt/open-city/archive/` относительно
корня репозитория. Это provenance/source, а не канон проекта.

Поисковые Markdown-копии пересобираются отдельно:

```bash
make chat-archive-markdown
make chat-archive-markdown-check
```

Они записываются в `knowledge/research/open-city-chat-archive/transcripts/` и являются
производным представлением raw JSON, а не новым источником канонических фактов.
