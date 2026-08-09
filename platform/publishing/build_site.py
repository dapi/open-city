#!/usr/bin/env python3
"""Собирает статический сайт OpenCity из производственных пакетов выпусков."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ISSUES_DIR = ROOT / "productions/issues"
SITE_SOURCE = ROOT / "projects/open-city/site"
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


def shell(config: dict, body: str, *, review: bool, title: str, description: str) -> str:
    robots = '<meta name="robots" content="noindex,nofollow">' if review else ""
    banner = '<div class="review-banner">Закрытый предпросмотр — не опубликовано</div>' if review else ""
    github_url = config.get("github_url")
    github_link = (
        f'<a href="{html.escape(github_url)}">Исходный код на GitHub ↗</a>' if github_url else ""
    )
    return f"""<!doctype html>
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
</head>
<body>
  {banner}
  <a class="skip-link" href="#main">К содержанию</a>
  <header class="site-header">
    <div class="shell nav">
      <a class="brand" href="/"><span>Город</span> Нейросеть</a>
      <nav class="nav-links" aria-label="Основная навигация">
        <a href="/#issues">Выпуски</a>
        <a href="{html.escape(config['telegram_url'])}">Telegram</a>
        <a href="{html.escape(config['studio_chat_url'])}">Синхронизация</a>
      </nav>
    </div>
  </header>
  <main id="main">{body}</main>
  <footer class="site-footer"><div class="shell footer-row"><span>{html.escape(config['publisher'])}</span><span>Город, где оптимизация стала смыслом жизни.</span>{github_link}</div></footer>
</body>
</html>
"""


def build_index(config: dict, issues: list[dict], review: bool) -> str:
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
    body = f"""
    <section class="hero shell">
      <div class="eyebrow">Серийный цифровой комикс</div>
      <h1>Всё уже <em>оптимизировано.</em> Кроме смысла.</h1>
      <p class="lede">{html.escape(config['description'])}</p>
      <div class="hero-actions">
        <a class="button primary" href="#issues">Читать выпуски</a>
        <a class="button" href="{html.escape(config['studio_chat_url'])}">Читать «Синхронизацию»</a>
      </div>
    </section>
    <section class="shell" id="issues">
      <div class="section-heading"><h2>Выпуски</h2><div class="count">{len(issues):02d}</div></div>
      <div class="issue-grid">{grid}</div>
    </section>"""
    return shell(config, body, review=review, title=config["title"], description=config["description"])


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
    if output.exists():
        shutil.rmtree(output)
    (output / "assets/comics").mkdir(parents=True)
    shutil.copy2(SITE_SOURCE / "styles.css", output / "assets/styles.css")
    for issue in issues:
        source_image = issue["directory"] / issue["canonical_files"]["art_master"]
        shutil.copy2(source_image, output / f"assets/comics/{issue['id']}.png")
    (output / "index.html").write_text(build_index(config, issues, include_drafts), encoding="utf-8")
    for index, issue in enumerate(issues):
        issue_output = output / issue["address"].strip("/")
        issue_output.mkdir(parents=True, exist_ok=True)
        previous = issues[index - 1] if index > 0 else None
        following = issues[index + 1] if index + 1 < len(issues) else None
        page = build_issue(config, issue, previous, following, include_drafts)
        (issue_output / "index.html").write_text(page, encoding="utf-8")
    print(f"SITE BUILD OK: {len(issues)} issues -> {output}")
    return len(issues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--include-drafts", action="store_true")
    args = parser.parse_args()
    write_site(args.output.resolve(), args.include_drafts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
