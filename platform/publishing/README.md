---
doc_kind: platform
doc_function: index
context: publishing_platform
status: active
---

# Автоматизация публикации и ревью

- `build_site.py` — собирает статический сайт из производственных пакетов.
- `review_bot.py` — отправляет сценарный пакет и визуальный мастер в приватный
  Telegram-чат, принимает решение Showrunner через long polling и отправляет итог
  ретро для сведения.

Токен бота, идентификаторы чата и разрешённых пользователей берутся только из
переменных окружения. Публикация не запускается при нажатии кнопки одобрения.

После создания чата и бота отправьте в чат `/review_setup`, запишите токен в `.env`
и выполните `make review-discover`: команда покажет ID чата и вашего пользователя,
которые нужно перенести в остальные поля `.env`.

Команды контура: `make review-submit-script ISSUE=issue-NNN` для сценарного пакета,
`make review-submit ISSUE=issue-NNN` для визуального мастера и
`make review-submit-retro ISSUE=issue-NNN` для готового ретро.
