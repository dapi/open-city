---
doc_kind: governance
doc_function: canonical
context: knowledge_provenance
purpose: Фундаментальные принципы базы знаний AI OS студии.
status: active
source_material:
  - https://github.com/dapi/memory-bank/blob/main/memory-bank/dna/principles.md
---

# Принципы базы знаний

1. **Один факт — один canonical owner.** Копии не становятся вторым источником истины.
   Они ссылаются на owner либо явно объявляются snapshot.
2. **Источник не равен истине.** Чат, transcript, research dump и сгенерированный файл —
   evidence/provenance. Каноном они становятся только после проверки и явного promotion.
3. **Границы контекстов явны.** Studio governance, project canon, episode production,
   automation platform, distribution learning и knowledge provenance используют свои
   словари и правила. Переход между ними оформляется contract/manifest.
4. **Один документ — одна тема.** Разросшийся документ делится, а не превращается в
   неразличимый склад фактов.
5. **Progressive disclosure.** Сначала короткий индекс и карта, затем специализированные
   документы и только потом raw sources.
6. **WHY / WHAT / HOW разделены.** Паспорт/brief владеет intent и requirements; ADR —
   причиной выбора; plan и код — способом исполнения; manifest — фактом конкретного run.
7. **Код владеет реализацией.** Документация владеет intent, rationale, contracts и
   operating constraints. Она не переписывает код прозой.
8. **Index-first.** Каждый governed-документ доступен из родительского README.
   Orphan-файл считается дефектом навигации.
9. **Ссылки аннотированы.** Рядом со ссылкой указано, что находится по адресу и зачем
   это читать.
10. **Решение — отдельный ADR.** Обсуждение и список вариантов не считаются принятым
    решением без ADR со статусом `accepted`.
11. **Provenance сохраняется.** Для канонического утверждения можно восстановить его
    upstream sources, автора/агента, время проверки и критерий принятия.
12. **Run-time отделён от design-time.** Cache, temp и промежуточный output не являются
    knowledge base. Утверждённый deliverable попадает в Git только через manifest и gate.
