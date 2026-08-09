# Экспорт проекта ChatGPT

Утилиты в этом каталоге воспроизводимо выгружают полное дерево разговоров проекта
ChatGPT через авторизованную вкладку Chrome и Playwriter.

- `extract-project-chat.js` сохраняет raw `mapping`, текущую ветку сообщений и вложения.
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
