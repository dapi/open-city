---
doc_kind: engineering
doc_function: reference
context: studio_os
purpose: Три варианта структуры репозитория AI OS студии и критерии выбора.
derived_from:
  - ../../studio-os/governance/knowledge-base/principles.md
status: draft
---

# Варианты структуры репозитория AI OS студии

## Что именно структурируем

Репозиторий одновременно играет несколько ролей, которые нельзя считать одним типом
контента:

1. **Studio governance** — правила, роли агентов, workflow, решения и quality gates.
2. **Project canon** — мир, персонажи, tone of voice, визуальный и сюжетный канон.
3. **Episode production** — конкретный производственный прогон от brief до release и retro.
4. **Automation platform** — переиспользуемый код для голоса, визуалов, монтажа,
   публикации и экспорта данных.
5. **Distribution and learning** — публикации, метрики, эксперименты и обратная связь.
6. **Knowledge and provenance** — первичные источники, исследования и архив разговоров.

В терминах FPF это отдельные bounded contexts: у каждого собственные понятия,
инварианты, ответственные роли и жизненный цикл. Данные между ними должны переходить
через явные контракты: episode spec, approved script, voice manifest, render manifest,
release manifest и retro.

## Критерии выбора

- агент быстро понимает, где его входы, выходы и зона ответственности;
- исходники, утверждённые артефакты и генерируемые результаты не смешиваются;
- один репозиторий масштабируется на несколько проектов и эпизодов;
- производственный прогон воспроизводим по manifest и provenance;
- человеку удобно найти всё, относящееся к одному эпизоду;
- миграция не требует сразу переписать весь pipeline.

## Вариант 1 — по жизненному циклу производства

```text
open-city/
├── studio/                 # роли, правила, prompts, workflow
├── development/            # идеи, исследования, черновики
├── preproduction/          # briefs, сценарии, дизайн, casting
├── production/             # audio, animation, render
├── postproduction/         # монтаж, QA, subtitles
├── distribution/           # публикации, media kit, analytics
├── archive/                # исходные разговоры и завершённые пакеты
└── scripts/
    ├── voice/
    ├── animation/
    ├── publishing/
    └── chatgpt-export/
```

**Сильные стороны:** pipeline виден непосредственно в дереве; низкий порог входа;
легко внедрить поверх текущего production kit.

**Слабые стороны:** материалы одного эпизода разнесены по многим папкам; при нескольких
проектах быстро появляются дубли и сложные имена; границы канона и конкретного run
остаются неявными.

**Когда выбирать:** одна команда, один сериал и ближайшая задача — стабилизировать
производственный конвейер без серьёзной реорганизации.

## Вариант 2 — строгие bounded contexts

```text
open-city/
├── contexts/
│   ├── studio-governance/
│   ├── story-world/
│   ├── episode-production/
│   ├── media-automation/
│   ├── distribution-learning/
│   └── knowledge-provenance/
├── bridges/                # явные контракты между contexts
│   ├── episode-spec.schema.json
│   ├── approved-script.schema.json
│   ├── voice-manifest.schema.json
│   ├── render-manifest.schema.json
│   └── release-retro.schema.json
├── agents/                 # adapters/prompts по ролям
└── var/                    # cache/output, не коммитится
```

Каждый context получает собственный `README.md`, glossary, invariants, owners,
quality gates и локальную структуру данных.

**Сильные стороны:** лучшие семантические границы; агентам проще действовать автономно;
handoff проверяется схемами; хорошо масштабируется на много агентов и интеграций.

**Слабые стороны:** человеку сложнее собрать взгляд «весь эпизод в одной папке»;
потребуются индексы и tooling; самая дорогая миграция.

**Когда выбирать:** студия становится платформой с несколькими командами, проектами и
независимо развиваемыми automation-сервисами.

## Вариант 3 — гибрид Studio OS + проекты + production runs

```text
open-city/
├── studio-os/
│   ├── governance/         # правила, ADR, quality gates
│   ├── agents/             # роли, prompts, capabilities
│   ├── workflows/          # методы и handoff-процессы
│   └── contracts/          # схемы межконтекстных артефактов
├── projects/
│   └── open-city/
│       ├── canon/          # мир, персонажи, tone, narrative rules
│       ├── brand/          # visual guide, media identity
│       └── roadmap/
├── productions/
│   └── episodes/
│       └── pilot-v1.2/
│           ├── episode.yaml
│           ├── script/
│           ├── art/
│           ├── audio/
│           ├── animation/
│           ├── render/
│           ├── release/
│           └── retro/
├── platform/
│   ├── voice/
│   ├── visual/
│   ├── animation/
│   ├── publishing/
│   └── tests/
├── knowledge/
│   ├── sources/
│   │   └── chatgpt/open-city/
│   ├── research/
│   └── decisions/
├── scripts/
│   └── chatgpt-export/     # repo-операции и data ingestion
└── var/                    # cache/output/tmp, не коммитится
```

**Сильные стороны:** канон отделён от конкретных выпусков, код — от результатов, а
первичные знания — от утверждённых документов. При этом весь production run эпизода
лежит рядом. Структура подходит и человеку, и специализированным агентам.

**Слабые стороны:** нужны manifest-файлы и правила продвижения артефакта из knowledge
в canon, а затем в production; некоторые общие assets потребуют явного владельца.

**Когда выбирать:** AI OS уже важнее одного скрипта, но студия ещё хочет сохранять
простую навигацию по проектам и эпизодам.

## Рекомендация

Выбрать **вариант 3**. Он даёт почти всю ценность bounded contexts без организационной
цены варианта 2. Каталоги здесь не означают семантическое наследование контекстов:
связи фиксируются явными contracts/manifests.

### Как разложить текущие файлы

| Сейчас | Целевое место |
|---|---|
| `docs/паспорт_студии_*.md` | `studio-os/governance/studio-passport.md` |
| `docs/паспорт_проекта_*.md` | `projects/open-city/canon/project-bible.md` |
| `Pilot_v1.2_Vertical_ProductionKit/` | `productions/episodes/pilot-v1.2/` |
| `voice_script_v1.2_extended.json` | `productions/episodes/pilot-v1.2/script/timeline.json` |
| `speakers*.json` | project voice profile либо episode override |
| `generate_voice*.py` | `platform/voice/` |
| `prepare_russian_voices*.py` | `platform/voice/tools/` |
| архив ChatGPT | `knowledge/sources/chatgpt/open-city/` |
| экспортёр ChatGPT | `scripts/chatgpt-export/` |

### Безопасная последовательность миграции

1. Сначала создать новые каталоги и contracts, не меняя поведения pipeline.
2. Перенести automation-код и добавить совместимые команды в корневой `Makefile`.
3. Перенести pilot как один production run и проверить генерацию теми же входами.
4. Перенести паспорта в governance/canon и оставить временные redirect-файлы.
5. Последним переместить архив разговоров в knowledge и проверить все относительные ссылки.

Архив и экспортёр изолированы соответственно в
`knowledge/sources/chatgpt/open-city/archive/` и `scripts/chatgpt-export/`; они не
меняют voice/animation pipeline.
