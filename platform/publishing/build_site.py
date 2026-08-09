#!/usr/bin/env python3
"""Собирает статический сайт OpenCity из производственных пакетов выпусков."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ISSUES_DIR = ROOT / "productions/issues"
SITE_SOURCE = ROOT / "projects/open-city/site"
CHARACTERS_SOURCE = ROOT / "projects/open-city/canon/characters/characters.json"
CHARACTERS_ASSET_DIR = ROOT / "projects/open-city/assets/characters"
ARCHIVE_ARTIFACTS_DIR = ROOT / "knowledge/sources/chatgpt/open-city/archive/artifacts"
ARCHIVE_CHATS_DIR = ROOT / "knowledge/sources/chatgpt/open-city/archive/chats"
VISUAL_DEVELOPMENT_DIR = ROOT / "projects/open-city/assets/visual-development"
# Explicit operator exclusions. IDs remain reserved so existing archive references
# do not silently point at a different image after deletion.
ARCHIVE_REMOVED_SOURCES = {
    "knowledge/sources/chatgpt/open-city/archive/artifacts/69077bb5-15c0-8327-a692-409c0d5bf1ea/Screenshot_2025-11-02_at_21.35.49.png",
    "knowledge/sources/chatgpt/open-city/archive/artifacts/69077bb5-15c0-8327-a692-409c0d5bf1ea/f2f54056-f7a4-438c-a818-1393f4162cb7.png",
    "knowledge/sources/chatgpt/open-city/archive/artifacts/69086e59-db2c-8325-b5c2-da4d3bf58181/ca76c594-8f40-4be1-9400-9321f45f01a3.png",
}
NEWS_SOURCE = ROOT / "projects/open-city/news/news.json"
DEFAULT_OUTPUT = ROOT / "var/output/site"
PUBLIC_STATUSES = {"published"}


def markdown_field(text: str, label: str) -> str:
    pattern = rf"\*\*{re.escape(label)}:\*\*\s*(.*?)(?=\n\n|\n\*\*|\Z)"
    match = re.search(pattern, text, flags=re.DOTALL)
    if not match:
        return ""
    value = re.sub(r"\s+", " ", match.group(1)).strip().strip("`")
    return value


def load_issues(include_drafts: bool) -> list[dict]:
    issues = []
    for issue_path in sorted(ISSUES_DIR.glob("issue-*/issue.json")):
        issue = json.loads(issue_path.read_text(encoding="utf-8"))
        if not include_drafts and issue["status"] not in PUBLIC_STATUSES:
            continue
        issue_dir = issue_path.parent
        release_text = (issue_dir / "publish/website.md").read_text(encoding="utf-8")
        issue["directory"] = issue_dir
        issue["number"] = issue["id"].split("-")[1]
        issue["address"] = markdown_field(release_text, "Адрес") or f"/comics/{issue['id']}"
        issue["intro"] = markdown_field(release_text, "Подводка") or issue["premise"]
        issue["alt"] = markdown_field(release_text, "Alt-текст") or issue["premise"]
        issues.append(issue)
    return issues


def load_characters() -> list[dict]:
    catalog = json.loads(CHARACTERS_SOURCE.read_text(encoding="utf-8"))
    return catalog["characters"]


def load_news(include_drafts: bool) -> list[dict]:
    collection = json.loads(NEWS_SOURCE.read_text(encoding="utf-8"))
    articles = [
        article
        for article in collection["articles"]
        if include_drafts or article["status"] in PUBLIC_STATUSES
    ]
    return sorted(articles, key=lambda article: article["date"], reverse=True)


def news_asset_url(article: dict, asset: dict) -> str:
    return f"/assets/news/{article['slug']}/{Path(asset['asset_path']).name}"


def format_publication_date(value: str) -> str:
    year, month, day = value.split("-")
    months = {
        "01": "января",
        "02": "февраля",
        "03": "марта",
        "04": "апреля",
        "05": "мая",
        "06": "июня",
        "07": "июля",
        "08": "августа",
        "09": "сентября",
        "10": "октября",
        "11": "ноября",
        "12": "декабря",
    }
    return f"{int(day)} {months[month]} {year}"


def archive_asset_name(character_id: str, index: int, artifact_path: str) -> str:
    suffix = Path(artifact_path).suffix.lower() or ".png"
    return f"{character_id}-{index + 1:02d}{suffix}"


def archive_catalog(characters: list[dict]) -> list[dict]:
    """Return public archive assets in newest-first display order."""
    appearance_dates: dict[tuple[str, str], str] = {}
    for chat_path in sorted(ARCHIVE_CHATS_DIR.glob("*.json")):
        if chat_path.name.endswith(".raw.json"):
            continue
        chat = json.loads(chat_path.read_text(encoding="utf-8"))
        conversation_id = chat.get("conversationId", chat_path.stem)
        file_by_id = {
            artifact.get("file_id"): artifact.get("file")
            for artifact in chat.get("artifacts", [])
            if artifact.get("file_id") and artifact.get("file")
        }
        for message in chat.get("messages", []):
            timestamp = message.get("create_time")
            if timestamp is None:
                continue
            date = datetime.fromtimestamp(float(timestamp), timezone.utc).strftime("%Y-%m-%d")
            for attachment in message.get("attachments", []):
                filename = file_by_id.get(attachment.get("file_id"))
                if filename:
                    appearance_dates.setdefault((conversation_id, filename), date)

    usage: dict[str, list[str]] = {}
    excluded: set[str] = set()
    for character in characters:
        for reference in character.get("archive_visual_references", []):
            artifact_path = reference["artifact_path"]
            if not reference.get("publish", True):
                excluded.add(artifact_path)
                continue
            usage.setdefault(artifact_path, []).append(character["name"])

    assets = []
    for source in sorted(ARCHIVE_ARTIFACTS_DIR.rglob("*")):
        if not source.is_file() or source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        relative_source = source.relative_to(ROOT).as_posix()
        if relative_source in excluded:
            continue
        number = len(assets) + 1
        archive_id = f"ARCH-{number:03d}"
        if relative_source in ARCHIVE_REMOVED_SOURCES:
            # Consume the old slot but do not publish the removed asset.
            assets.append({"_removed": True})
            continue
        assets.append(
            {
                "id": archive_id,
                "number": number,
                "source": source,
                "source_path": relative_source,
                "original_filename": source.name,
                "public_filename": f"{archive_id.lower()}{source.suffix.lower()}",
                "used_by": sorted(set(usage.get(relative_source, []))),
                "appearance_date": appearance_dates.get((source.parent.name, source.name)),
            }
        )

    for manifest_path in sorted(VISUAL_DEVELOPMENT_DIR.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        package_date = manifest.get("approved_at")
        for manifest_asset in manifest.get("assets", []):
            archive_metadata = manifest_asset.get("archive", {})
            if not archive_metadata.get("publish", False):
                continue
            source = manifest_path.parent / manifest_asset["file"]
            if not source.is_file():
                raise FileNotFoundError(f"archive asset missing: {source}")
            number = len(assets) + 1
            archive_id = f"ARCH-{number:03d}"
            assets.append(
                {
                    "id": archive_id,
                    "number": number,
                    "source": source,
                    "source_path": source.relative_to(ROOT).as_posix(),
                    "original_filename": source.name,
                    "public_filename": f"{archive_id.lower()}{source.suffix.lower()}",
                    "used_by": [],
                    "usage_label": archive_metadata["caption"],
                    "alt": archive_metadata["alt"],
                    "appearance_date": package_date,
                }
            )

    public_assets = [asset for asset in assets if not asset.get("_removed")]
    return sorted(
        public_assets,
        key=lambda asset: asset["appearance_date"] or "",
        reverse=True,
    )


def clean_html(page: str) -> str:
    """Normalize generated pages without changing their rendered content."""
    return "\n".join(line.rstrip() for line in page.splitlines()) + "\n"


def shell(
    config: dict,
    body: str,
    *,
    review: bool,
    title: str,
    description: str,
    scripts: str = "",
) -> str:
    robots = '<meta name="robots" content="noindex,nofollow">' if review else ""
    banner = '<div class="review-banner">Закрытый предпросмотр — не опубликовано</div>' if review else ""
    github_url = config.get("github_url")
    github_link = (
        f'<a href="{html.escape(github_url)}">Исходный код на GitHub ↗</a>' if github_url else ""
    )
    return f"""<!doctype html>
<!-- GENERATED FILE. Source of truth: open-city repository. Do not edit published facts here. -->
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#070b12">
  <meta name="color-scheme" content="dark">
  {robots}
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description)}">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23070b12'/%3E%3Ccircle cx='16' cy='16' r='7' fill='%2308b8d1'/%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800;900&display=swap">
  <link rel="stylesheet" href="/assets/styles.css">
  <link rel="stylesheet" href="/assets/site-header.css">
</head>
<body>
  {banner}
  <a class="skip-link" href="#main">К содержанию</a>
  <header class="site-header">
    <a class="studio-mark" href="/" aria-label="OpenCity Studio — главная">
      <span class="studio-mark__signal" aria-hidden="true"></span>
      OpenCity Studio
    </a>
    <nav class="site-nav" aria-label="Основная навигация">
      <a href="/characters/">Картотека</a>
      <a href="/news/">Новости</a>
      <a class="secondary-nav-link" href="/archive/">Архив</a>
      <a href="/studio/">Студия</a>
      <a class="secondary-nav-link" href="/studio/process/">Как мы работаем</a>
      <a class="header-link" href="{html.escape(config['telegram_url'])}" aria-label="Telegram">Telegram ↗</a>
    </nav>
  </header>
  <main id="main">{body}</main>
  <footer class="site-footer"><div class="shell footer-row"><span>{html.escape(config['publisher'])}</span><span>Город, где оптимизация стала смыслом жизни.</span>{github_link}</div></footer>
  {scripts}
</body>
</html>
"""


def build_index(config: dict, issues: list[dict], news: list[dict], review: bool) -> str:
    cards = []
    for issue in issues:
        cards.append(f"""
        <a class="issue-card" href="{html.escape(issue['address'])}/">
          <img src="/assets/comics/{issue['id']}.png" alt="{html.escape(issue['alt'])}" loading="lazy" width="1024" height="1536">
          <div class="issue-card-copy">
            <div class="issue-number">Выпуск {issue['number']}</div>
            <h3>{html.escape(issue['title'])}</h3>
            <p>{html.escape(issue['intro'])}</p>
          </div>
        </a>""")
    empty = '<p class="lede">Первый выпуск готовится к публикации.</p>'
    grid = "\n".join(cards) if cards else empty
    latest_news = ""
    if news:
        article = news[0]
        latest_news = f"""
        <section class="shell latest-news" aria-labelledby="latest-news-title">
          <div class="section-heading"><h2 id="latest-news-title">Внутри студии</h2><a href="/news/">Все новости →</a></div>
          <a class="latest-news-card" href="/news/{html.escape(article['slug'])}/">
            <span class="news-card-media"><img src="{html.escape(news_asset_url(article, article['cover']))}" alt="{html.escape(article['cover']['alt'])}" loading="lazy" width="1024" height="1536"></span>
            <div>
              <div class="news-meta">{html.escape(format_publication_date(article['date']))} · {html.escape(article['category'])}</div>
              <h3>{html.escape(article['title'])}</h3>
              <p>{html.escape(article['summary'])}</p>
            </div>
          </a>
        </section>"""
    body = f"""
    <section class="hero shell">
      <div class="eyebrow">Серийный цифровой комикс</div>
      <h1>Всё уже <em>оптимизировано.</em> Кроме смысла.</h1>
      <p class="lede">{html.escape(config['description'])}</p>
      <div class="hero-actions">
        <a class="button primary" href="#issues">Читать выпуски</a>
        <a class="button" href="/characters/">Открыть картотеку</a>
        <a class="button" href="{html.escape(config['studio_chat_url'])}">Читать «Синхронизацию»</a>
      </div>
    </section>
    <section class="shell" id="issues">
      <div class="section-heading"><h2>Выпуски</h2><div class="count">{len(issues):02d}</div></div>
      <div class="issue-grid">{grid}</div>
    </section>
    {latest_news}"""
    return shell(config, body, review=review, title=config["title"], description=config["description"])


def build_characters(config: dict, characters: list[dict], issues: list[dict], review: bool) -> str:
    visible_issues = {issue["id"]: issue for issue in issues}
    cards = []
    for character in characters:
        published_appearances = [
            visible_issues[issue_id]
            for issue_id in character["appearances"]
            if issue_id in visible_issues
        ]
        if published_appearances:
            appearance_links = "".join(
                f'<a href="{html.escape(issue["address"])}/">Выпуск {issue["number"]}</a>'
                for issue in published_appearances
            )
        elif character["profile_status"] == "announced":
            appearance_links = "<span>Первое появление ещё не зарегистрировано</span>"
        else:
            appearance_links = "<span>Материалы дела готовятся к публикации</span>"

        quote = ""
        if character.get("quote") and (review or published_appearances):
            quote = f'<blockquote>«{html.escape(character["quote"])}»</blockquote>'

        if character["visual_status"] == "approved":
            visual_label = "Образ утверждён"
            visual_class = "is-approved"
        else:
            visual_label = "Визуальный мастер готовится"
            visual_class = "is-pending"

        portrait = character.get("portrait")
        if portrait:
            portrait_name = Path(portrait["asset_path"]).name
            visual_content = (
                f'<img class="character-portrait" src="/assets/characters/{html.escape(portrait_name)}" '
                f'alt="{html.escape(portrait["alt"])}" width="1024" height="1280">'
            )
            portrait_direction = f"""
            <dl class="portrait-direction">
              <dt>Режиссура образа</dt>
              <dd>{html.escape(portrait['creation_note'])}</dd>
            </dl>"""
            portrait_class = " has-portrait"
        else:
            monogram = character["name"][0].upper()
            visual_content = (
                f'<span class="character-monogram" aria-hidden="true">{html.escape(monogram)}</span>'
            )
            portrait_direction = ""
            portrait_class = ""

        archive_references = [
            (index, reference)
            for index, reference in enumerate(character.get("archive_visual_references", []))
            if reference.get("publish", True)
        ]
        archive_references.sort(key=lambda item: not item[1].get("featured", False))
        if archive_references:
            archive_items = []
            for index, reference in archive_references:
                archive_name = archive_asset_name(
                    character["id"], index, reference["artifact_path"]
                )
                note = html.escape(reference["note"])
                figure_class = ' class="is-featured"' if reference.get("featured") else ""
                archive_items.append(f"""
                <figure{figure_class}>
                  <a href="/assets/characters/archive/{html.escape(archive_name)}" target="_blank" rel="noopener" title="Открыть исходный вариант полностью">
                    <img src="/assets/characters/archive/{html.escape(archive_name)}" alt="{note}" loading="lazy">
                  </a>
                  <figcaption>{note}</figcaption>
                </figure>""")
            archive_gallery = f"""
            <details class="archive-gallery">
              <summary>Архивные варианты · {len(archive_references)}</summary>
              <div class="archive-gallery-grid">{''.join(archive_items)}</div>
            </details>"""
        else:
            archive_gallery = ""
        cards.append(f"""
        <article class="character-card accent-{html.escape(character['accent'])}" id="{html.escape(character['id'])}">
          <div class="character-visual {visual_class}{portrait_class}" aria-label="{html.escape(visual_label)}">
            {visual_content}
            <span class="visual-status">{html.escape(visual_label)}</span>
          </div>
          <div class="character-copy">
            <div class="dossier-row">
              <span>Дело {html.escape(character['dossier_number'])}</span>
              <span>{'Наблюдается' if character['profile_status'] == 'active' else 'Дело открыто'}</span>
            </div>
            <h2>{html.escape(character['name'])}</h2>
            <p class="character-role">{html.escape(character['role'])}</p>
            <p class="character-function">{html.escape(character['dramatic_function'])}</p>
            <dl class="system-note">
              <dt>Системная пометка</dt>
              <dd>{html.escape(character['system_note'])}</dd>
            </dl>
            {portrait_direction}
            {archive_gallery}
            {quote}
            <div class="appearances"><strong>Появления</strong>{appearance_links}</div>
          </div>
        </article>""")

    body = f"""
    <section class="catalog-hero shell">
      <div class="eyebrow">Муниципальный реестр · доступ открыт</div>
      <h1>Картотека<br><em>жителей</em></h1>
      <p class="lede">Герои города, который научился учитывать всё — кроме человеческого смысла.</p>
      <p class="catalog-context">Здесь собраны воплощения героев в мире комикса. Одноимённые сотрудники OpenCity Studio — те же творческие идентичности в другом контексте. <a href="/archive/">Открыть полный архив изображений →</a></p>
    </section>
    <section class="shell character-list" aria-label="Профили героев">
      {''.join(cards)}
    </section>"""
    return shell(
        config,
        body,
        review=review,
        title=f"Картотека жителей — {config['short_title']}",
        description="Профили героев серийного цифрового комикса «Город Нейросеть».",
    )


def build_archive(config: dict, archive_assets: list[dict], review: bool) -> str:
    cards = []
    for asset in archive_assets:
        alt = asset.get("alt", f"{asset['id']}: {asset['original_filename']}")
        if asset.get("usage_label"):
            usage = html.escape(asset["usage_label"])
        elif asset["used_by"]:
            usage = "Профили: " + ", ".join(html.escape(name) for name in asset["used_by"])
        else:
            usage = "Не привязан к профилю"
        cards.append(f"""
        <figure class="archive-card" id="{html.escape(asset['id'].lower())}">
          <a class="archive-image-link" href="/assets/archive/{html.escape(asset['public_filename'])}" target="_blank" rel="noopener" title="Открыть исходный файл полностью">
            <img src="/assets/archive/{html.escape(asset['public_filename'])}" alt="{html.escape(alt)}" loading="lazy">
          </a>
          <figcaption>
            <div class="archive-id">{html.escape(asset['id'])}</div>
            <div class="archive-filename">{html.escape(asset['original_filename'])}</div>
            <div class="archive-date">Появился: {html.escape(asset['appearance_date'] or 'дата не установлена')}</div>
            <div class="archive-usage">{usage}</div>
            <a class="archive-direct-link" href="/assets/archive/{html.escape(asset['public_filename'])}">Прямой файл ↗</a>
          </figcaption>
        </figure>""")
    body = f"""
    <section class="catalog-hero shell archive-hero">
      <div class="eyebrow">Архив источников · {len(archive_assets):02d} файлов</div>
      <h1>Архив<br><em>изображений</em></h1>
      <p class="lede">Визуальная история OpenCity: новые производственные материалы и найденные изображения из старых чатов.</p>
      <p class="catalog-context">Сначала показаны самые новые изображения. Ссылайтесь на любой артефакт по номеру; исходные имена сохранены в карточках, а клик открывает полный файл.</p>
    </section>
    <section class="shell archive-grid" aria-label="Нумерованный архив изображений">
      {''.join(cards)}
    </section>"""
    return shell(
        config,
        body,
        review=review,
        title=f"Архив изображений — {config['short_title']}",
        description="Нумерованный архив визуальных материалов OpenCity Studio, от новых к старым.",
    )


def build_news_index(config: dict, articles: list[dict], review: bool) -> str:
    cards = []
    for article in articles:
        cards.append(f"""
        <a class="news-card" href="/news/{html.escape(article['slug'])}/">
          <span class="news-card-media"><img src="{html.escape(news_asset_url(article, article['cover']))}" alt="{html.escape(article['cover']['alt'])}" loading="lazy" width="1024" height="1536"></span>
          <div class="news-card-copy">
            <div class="news-meta">{html.escape(format_publication_date(article['date']))} · {html.escape(article['category'])}</div>
            <h2>{html.escape(article['title'])}</h2>
            <p>{html.escape(article['summary'])}</p>
            <span>Читать материал →</span>
          </div>
        </a>""")
    empty = '<p class="lede">Первая производственная заметка готовится.</p>'
    body = f"""
    <section class="catalog-hero shell news-index-hero">
      <div class="eyebrow">Открытый производственный журнал</div>
      <h1>Новости<br><em>студии</em></h1>
      <p class="lede">Показываем внутренний процесс OpenCity: решения, эксперименты, ошибки и рабочие материалы до того, как они становятся выпуском.</p>
      <p class="catalog-context">Новые материалы анонсируем в <a href="{html.escape(config['telegram_url'])}">Telegram-канале проекта ↗</a>.</p>
    </section>
    <section class="shell news-grid" aria-label="Новости OpenCity Studio">
      {''.join(cards) if cards else empty}
    </section>"""
    return shell(
        config,
        body,
        review=review,
        title=f"Новости студии — {config['short_title']}",
        description="Открытый производственный журнал OpenCity Studio.",
    )


def build_news_article(config: dict, article: dict, review: bool) -> str:
    cover_caption = article["cover"].get("caption", article["title"])
    gallery_title = article.get("gallery_title", "Первый пакет")
    followup = article.get(
        "followup",
        "Новые сценические пробы и следующие версии пакета будем анонсировать в Telegram студии.",
    )
    sections = []
    for section in article["sections"]:
        paragraphs = "".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in section.get("paragraphs", []))
        bullets = ""
        if section.get("bullets"):
            bullets = "<ul>" + "".join(
                f"<li>{html.escape(item)}</li>" for item in section["bullets"]
            ) + "</ul>"
        sections.append(f"""
        <section class="news-copy-section">
          <h2>{html.escape(section['heading'])}</h2>
          {paragraphs}
          {bullets}
        </section>""")

    gallery = []
    for item in article["gallery"]:
        gallery.append(f"""
        <figure class="news-gallery-item">
          <a href="{html.escape(news_asset_url(article, item))}" data-lightbox data-caption="{html.escape(item['label'])}" target="_blank" rel="noopener" title="Открыть в полноэкранном просмотрщике">
            <img src="{html.escape(news_asset_url(article, item))}" alt="{html.escape(item['alt'])}" loading="lazy" width="1024" height="1536">
          </a>
          <figcaption><strong>{html.escape(item['label'])}</strong>{html.escape(item['caption'])}</figcaption>
        </figure>""")

    body = f"""
    <article class="shell news-article">
      <header class="news-article-header">
        <div class="news-meta">{html.escape(format_publication_date(article['date']))} · {html.escape(article['category'])}</div>
        <h1>{html.escape(article['title'])}</h1>
        <p class="lede">{html.escape(article['lead'])}</p>
      </header>
      <figure class="news-cover">
        <a href="{html.escape(news_asset_url(article, article['cover']))}" data-lightbox data-caption="{html.escape(cover_caption)}" target="_blank" rel="noopener" title="Открыть в полноэкранном просмотрщике">
          <img src="{html.escape(news_asset_url(article, article['cover']))}" alt="{html.escape(article['cover']['alt'])}" width="1024" height="1536">
        </a>
      </figure>
      <div class="news-copy">{''.join(sections)}</div>
      <aside class="telegram-teaser">
        <div class="eyebrow">Следить за процессом</div>
        <p>{html.escape(followup)}</p>
        <a class="button" href="{html.escape(config['telegram_url'])}">Открыть Telegram ↗</a>
      </aside>
      <section class="news-gallery" aria-labelledby="news-gallery-title">
        <div class="section-heading"><h2 id="news-gallery-title">{html.escape(gallery_title)}</h2><div class="count">{len(article['gallery']):02d}</div></div>
        <div class="news-gallery-grid">{''.join(gallery)}</div>
      </section>
      <nav class="news-back" aria-label="Навигация по новостям"><a href="/news/">← Все новости студии</a></nav>
    </article>
    <dialog class="news-lightbox" id="news-lightbox" aria-label="Полноэкранный просмотр изображения">
      <header class="news-lightbox-toolbar">
        <p class="news-lightbox-caption" aria-live="polite"></p>
        <div class="news-lightbox-controls">
          <button type="button" data-lightbox-zoom-out aria-label="Уменьшить изображение">−</button>
          <output class="news-lightbox-scale" aria-live="polite">100%</output>
          <button type="button" data-lightbox-zoom-in aria-label="Увеличить изображение">+</button>
          <button type="button" data-lightbox-reset>Вписать</button>
          <button type="button" data-lightbox-close>Закрыть ×</button>
        </div>
      </header>
      <div class="news-lightbox-stage">
        <div class="news-lightbox-canvas"><img class="news-lightbox-image" alt=""></div>
      </div>
    </dialog>"""
    return shell(
        config,
        body,
        review=review,
        title=f"{article['title']} — {config['short_title']}",
        description=article["summary"],
        scripts='<script src="/assets/news-lightbox.js" defer></script>',
    )


def build_issue(config: dict, issue: dict, previous: dict | None, following: dict | None, review: bool) -> str:
    previous_link = f'<a href="{html.escape(previous["address"])}/">← Выпуск {previous["number"]}</a>' if previous else "<span></span>"
    following_link = f'<a href="{html.escape(following["address"])}/">Выпуск {following["number"]} →</a>' if following else "<span></span>"
    body = f"""
    <article class="shell issue-layout">
      <div class="comic-frame"><img src="/assets/comics/{issue['id']}.png" alt="{html.escape(issue['alt'])}" width="1024" height="1536"></div>
      <div class="issue-copy">
        <div class="eyebrow">Выпуск {issue['number']}</div>
        <h1>{html.escape(issue['title'])}</h1>
        <p class="premise">{html.escape(issue['intro'])}</p>
        <div class="meta">
          <div><strong>Формат:</strong> {issue['format']['panels']} панелей, {html.escape(issue['format']['master_aspect_ratio'])}</div>
          <div><strong>Статус:</strong> {html.escape(issue['status'])}</div>
          <div><strong>Производство:</strong> {html.escape(config['publisher'])}</div>
        </div>
        <div class="pager">{previous_link}{following_link}</div>
      </div>
    </article>"""
    return shell(
        config,
        body,
        review=review,
        title=f"Выпуск {issue['number']}. {issue['title']} — {config['short_title']}",
        description=issue["intro"],
    )


def write_site(output: Path, include_drafts: bool) -> int:
    config = json.loads((SITE_SOURCE / "site.json").read_text(encoding="utf-8"))
    issues = load_issues(include_drafts)
    characters = load_characters()
    news = load_news(include_drafts)
    archive_assets = archive_catalog(characters)
    if output.exists():
        shutil.rmtree(output)
    (output / "assets/comics").mkdir(parents=True)
    (output / "assets/archive").mkdir(parents=True)
    shutil.copy2(SITE_SOURCE / "styles.css", output / "assets/styles.css")
    shutil.copy2(SITE_SOURCE / "site-header.css", output / "assets/site-header.css")
    shutil.copy2(SITE_SOURCE / "news-lightbox.js", output / "assets/news-lightbox.js")
    for character in characters:
        portrait = character.get("portrait")
        if portrait:
            source = ROOT / portrait["asset_path"]
            portrait_output = output / "assets/characters" / source.name
            portrait_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, portrait_output)
        for index, reference in enumerate(character.get("archive_visual_references", [])):
            if not reference.get("publish", True):
                continue
            source = ROOT / reference["artifact_path"]
            archive_output = output / "assets/characters/archive" / archive_asset_name(
                character["id"], index, reference["artifact_path"]
            )
            archive_output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, archive_output)
    for asset in archive_assets:
        shutil.copy2(asset["source"], output / "assets/archive" / asset["public_filename"])
    for article in news:
        article_assets = [article["cover"], *article["gallery"]]
        copied_sources: set[str] = set()
        for asset in article_assets:
            if asset["asset_path"] in copied_sources:
                continue
            copied_sources.add(asset["asset_path"])
            source = ROOT / asset["asset_path"]
            destination = output / news_asset_url(article, asset).lstrip("/")
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    for issue in issues:
        source_image = issue["directory"] / issue["canonical_files"]["art_master"]
        shutil.copy2(source_image, output / f"assets/comics/{issue['id']}.png")
    (output / "index.html").write_text(
        clean_html(build_index(config, issues, news, include_drafts)), encoding="utf-8"
    )
    characters_output = output / "characters"
    characters_output.mkdir(parents=True, exist_ok=True)
    (characters_output / "index.html").write_text(
        clean_html(build_characters(config, characters, issues, include_drafts)), encoding="utf-8"
    )
    archive_output = output / "archive"
    archive_output.mkdir(parents=True, exist_ok=True)
    (archive_output / "index.html").write_text(
        clean_html(build_archive(config, archive_assets, include_drafts)), encoding="utf-8"
    )
    (archive_output / "manifest.json").write_text(
        json.dumps(
            [
                {
                    "id": asset["id"],
                    "original_filename": asset["original_filename"],
                    "appearance_date": asset["appearance_date"],
                    "public_path": f"/assets/archive/{asset['public_filename']}",
                    "used_by": asset["used_by"],
                }
                for asset in archive_assets
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    news_output = output / "news"
    news_output.mkdir(parents=True, exist_ok=True)
    (news_output / "index.html").write_text(
        clean_html(build_news_index(config, news, include_drafts)), encoding="utf-8"
    )
    for article in news:
        article_output = news_output / article["slug"]
        article_output.mkdir(parents=True, exist_ok=True)
        (article_output / "index.html").write_text(
            clean_html(build_news_article(config, article, include_drafts)), encoding="utf-8"
        )
    for index, issue in enumerate(issues):
        issue_output = output / issue["address"].strip("/")
        issue_output.mkdir(parents=True, exist_ok=True)
        previous = issues[index - 1] if index > 0 else None
        following = issues[index + 1] if index + 1 < len(issues) else None
        page = build_issue(config, issue, previous, following, include_drafts)
        (issue_output / "index.html").write_text(clean_html(page), encoding="utf-8")
    print(
        f"SITE BUILD OK: {len(issues)} issues, {len(characters)} characters, "
        f"{len(news)} news articles -> {output}"
    )
    return len(issues)


def sync_character_catalog(build_output: Path, public_root: Path) -> None:
    public_root = public_root.resolve()
    if public_root in {Path("/"), Path.home()} or not (public_root / ".git").is_dir():
        raise SystemExit(f"Refusing to sync to non-repository path: {public_root}")
    managed_files = [
        Path("characters/index.html"),
        Path("archive/index.html"),
        Path("archive/manifest.json"),
        Path("assets/styles.css"),
        Path("assets/site-header.css"),
        Path("assets/news-lightbox.js"),
    ]
    portrait_dir = build_output / "assets/characters"
    if portrait_dir.is_dir():
        managed_files.extend(
            path.relative_to(build_output) for path in sorted(portrait_dir.rglob("*.png"))
        )
    archive_dir = build_output / "assets/archive"
    if archive_dir.is_dir():
        managed_files.extend(
            path.relative_to(build_output) for path in sorted(archive_dir.rglob("*")) if path.is_file()
        )
    news_dir = build_output / "news"
    if news_dir.is_dir():
        managed_files.extend(
            path.relative_to(build_output) for path in sorted(news_dir.rglob("*")) if path.is_file()
        )
    news_asset_dir = build_output / "assets/news"
    if news_asset_dir.is_dir():
        managed_files.extend(
            path.relative_to(build_output)
            for path in sorted(news_asset_dir.rglob("*"))
            if path.is_file()
        )
    managed_set = set(managed_files)
    for managed_dir, prefix in [
        (public_root / "assets/characters/archive", ""),
        (public_root / "assets/archive", "arch-"),
    ]:
        if not managed_dir.is_dir():
            continue
        for existing in managed_dir.iterdir():
            relative = existing.relative_to(public_root)
            if existing.is_file() and (not prefix or existing.name.startswith(prefix)) and relative not in managed_set:
                existing.unlink()
    for relative in managed_files:
        source = build_output / relative
        destination = public_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    print(f"SITE CONTENT SYNC OK: {len(managed_files)} generated files -> {public_root}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-drafts", action="store_true")
    parser.add_argument(
        "--sync-characters-to",
        type=Path,
        help="Copy managed character, archive, and news sections to a checked-out site repository.",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    write_site(output, args.include_drafts)
    if args.sync_characters_to:
        if args.include_drafts:
            raise SystemExit("Refusing to sync a draft preview to the public site repository.")
        sync_character_catalog(output, args.sync_characters_to)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
