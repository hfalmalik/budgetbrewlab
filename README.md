# BudgetBrewLab

A mostly-hands-off affiliate content site about **budget home coffee gear** — reviews, buying guides, and comparisons for grinders, pour-over kits, espresso machines, brewers, scales, kettles, and accessories at real-person prices. This is site #2 of the empire, cloned from the proven BudgetRigLab pipeline (`Desktop\NicheSite`).

- **Stack:** Python 3.12 static site generator (stdlib + `markdown`), no JS frameworks, one CSS file, dark-friendly.
- **Hosting:** GitHub Pages (free), serving the `docs/` folder on `main`.
- **Revenue:** Amazon Associates affiliate links — note coffee gear falls under Amazon's *Kitchen* commission category (~4.5%), nearly double the PC-components rate BudgetRigLab earns.
- **Automation:** the Windows scheduled task **"BrewLab Daily Article"** (10:30 AM) invokes Claude Code daily to write one new article, rebuild, and push.

> **Name/domain note:** "BudgetBrewLab" was picked as a clean, brandable sibling to BudgetRigLab. Domain availability was NOT verified — check `budgetbrewlab.com` before printing business cards. Everything (config, templates) makes the name easy to change in one place: `config.json`.

---

## Honest revenue expectations (read this first)

Same rules as BudgetRigLab, and they still apply:

- **SEO traffic takes 3–6+ months.** Near-zero visitors at first is normal, not failure.
- **AI-content sites must add real value** — specific recommendations, honest tradeoffs, comparison data, and human review. Pure unreviewed autopilot is how sites get deindexed.
- **Consistency beats bursts.** One decent article a day compounds.
- **Realistic math:** ~10k monthly visitors for the first meaningful money; usually a year. Coffee's higher commission rate (~4.5% vs 2.5%) and higher-priced carts help, but the timeline is the same.
- **Amazon Associates:** 3 qualifying sales within 180 days of joining or the account closes. One Associates account covers both sites — add each site to the account's site list.

---

## Folder layout

```
BrewLab/
├── config.json          Site name, URL, affiliate tag, settings
├── content/             Articles (markdown + frontmatter)
│   └── pages/           About + Affiliate Disclosure
├── templates/           base.html, article.html
├── static/              style.css, favicon (copied into docs/ at build)
├── docs/                BUILD OUTPUT — GitHub Pages serves this. Don't edit by hand.
└── scripts/
    ├── build.py                  Static site generator
    ├── lint_content.py           Content quality lint (runs inside build)
    ├── new_article.ps1           Claude Code writes 1 article + deploys (with retry)
    ├── deploy.ps1                Build + git commit + push
    ├── register_daily_task.ps1   One-time: register 10:30 AM daily task
    └── logs/                     Automation run logs
```

## Article format

```markdown
---
title: Best Budget Coffee Grinders Under $60 in 2026
description: One-sentence meta description (~150 chars) for search results.
date: 2026-07-05
category: Grinders
tags: grinders, under-60, kingrinder, listicle
---

Article body in markdown. Tables, FAQ section, internal links to other
articles as relative links like [text](other-article-slug.html).
```

**Affiliate links** use the `aff:` scheme in markdown: `[Kingrinder K2](aff:B09KXYZ1K2)`. The build rewrites these to `https://www.amazon.com/dp/<ASIN>?tag=<your-tag>` with `rel="nofollow sponsored"` — the tag comes from `config.json`.

> **ASINs verified 2026-07-05** against live amazon.com listings via web search (AeroPress, Bodum Chambord, Hario V60/filters/server/Skerton Pro, Kingrinder K2, Timemore C2, Krups GX5000, BAGAIL scale). Articles the daily automation writes still use plausible ASINs — spot-check those during your article skims, or rerun a verification pass periodically.

## Building locally

```powershell
# Once (already satisfied on this machine):
python -m pip install markdown

# Build (output -> docs/):
python scripts\build.py
```

Python 3.12 ARM64 is installed at `%LOCALAPPDATA%\Programs\Python\Python312-arm64\python.exe` if `python` isn't on PATH. Open `docs\index.html` in a browser to preview.

---

## One-time setup checklist (owner)

1. ~~Create the public GitHub repo~~ — **DONE 2026-07-05** (`hfalmalik/budgetbrewlab`, created via the machine's cached GitHub credentials).
2. ~~Connect and push~~ — **DONE 2026-07-05** (remote added, main pushed).
3. ~~Enable GitHub Pages~~ — **DONE 2026-07-05** (main `/docs`; live at `https://hfalmalik.github.io/budgetbrewlab/`).
4. ~~Verify seed-article ASINs~~ — **DONE 2026-07-05** (see note above).
5. **Google Search Console** (still yours): add the property, verify, submit `sitemap.xml`.
6. **Amazon Associates** (still yours): once you have the Associates account (pending for BudgetRigLab), add this site to the account's site list and put the same tag in `config.json` → `affiliate_tag`, then redeploy.

## Daily automation

Already registered: **"BrewLab Daily Article"**, daily at **10:30 AM** (30 min after BudgetRigLab's, so the two sites never fight over the CLI). It:

1. Invokes Claude Code headlessly to write one new 1200+ word coffee-gear article (retries once on transient CLI login blips);
2. Rebuilds the site;
3. Commits and pushes — GitHub Pages republishes automatically.

Logs land in `scripts\logs\`. **Recommended human-in-the-loop:** skim each new article within a day or two — check ASINs, prices, claims.

## Editorial standard (used by the automation too)

Every article must have: 1200+ words; specific products with realistic street prices; **at least one honest downside per product**; a markdown comparison table; an FAQ section; 2–3 internal links to related articles; `aff:` links for products; a frontmatter block matching the format above. Article types rotate between "best X under $Y" listicles, head-to-head comparisons, and how-to guides.

## Cross-promotion (EmpireHQ)

`scripts/build.py` reads `Desktop\EmpireHQ\links.json` and adds "Watch us on YouTube" / "Our digital products" links to the footer and About page for non-empty URLs. Already live since links.json is filled in.

## Maintenance

- **Change site name/URL/tag:** `config.json`, then rebuild.
- **Change design:** `static/style.css` and `templates/`, then rebuild.
- **Remove an article:** delete its `.md` from `content/`, rebuild, deploy.
- **Thin-content warning:** the build prints a warning for any article under 1000 words — fix or delete those.
