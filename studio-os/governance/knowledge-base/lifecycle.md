---
doc_kind: governance
doc_function: canonical
context: knowledge_provenance
purpose: Правила изменения, синхронизации и promotion знаний.
derived_from:
  - governance.md
status: active
source_material:
  - https://github.com/dapi/memory-bank/blob/main/memory-bank/dna/lifecycle.md
---

# Lifecycle знаний

## Maintenance

1. **Upstream first.** Меняя факт, сначала найти и обновить canonical owner.
2. **Downstream sync.** После изменения upstream проверить прямые `derived_from`-зависимости.
3. **Index sync.** При создании, переносе или архивировании документа обновить parent README.
4. **Конфликт — дефект.** Расхождение authoritative документов фиксируется немедленно.
5. **Report before repair.** Сотрудник сообщает о конфликте и не меняет чужой canonical owner,
   если текущая задача явно не разрешает такое изменение.
6. **Архивация не удаляет provenance.** Archived-документ остаётся доступен для объяснения
   исторических решений, но больше не authoritative.

## Promotion pipeline

```text
raw source → extracted facts → synthesis → canonical proposal
           → human/quality gate → active canon, ADR or contract
           → production run → verified deliverable → retro/evidence
```

- Переход выполняется явным документом или manifest, а не перемещением файла без объяснения.
- У promotion должны быть upstream refs, проверяющий, дата и критерий принятия.
- Новое сообщение в чате не меняет канон автоматически.
- Retro может инициировать изменение upstream, но сначала создаёт finding/proposal.

## Checklist перед фиксацией

- [ ] frontmatter валиден;
- [ ] canonical owner определён и не продублирован;
- [ ] `derived_from` указывает прямые upstream sources без циклов;
- [ ] parent README обновлён;
- [ ] downstream проверен либо явно перечислен как требующий синхронизации;
- [ ] source, canon, run и generated output не смешаны;
- [ ] для решений обновлён ADR, для production — manifest и quality gate.
