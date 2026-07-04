#!/usr/bin/env python3
"""
BudgetBrewLab static site generator (cloned from the BudgetRigLab pipeline).

Stdlib + the `markdown` package only. Renders content/*.md into docs/
(GitHub Pages serves from docs/ on the main branch).

Features:
  - Frontmatter parsing (title, description, date, category, tags)
  - aff: link rewriting -> Amazon affiliate URLs using config.json affiliate_tag
  - Index page grouped by category, per-category pages
  - About / Affiliate Disclosure pages from content/pages/
  - sitemap.xml, robots.txt, rss.xml
  - Related-article internal links (shared category/tags)
  - FTC/Amazon affiliate disclosure on every page (baked into base template)

Usage:  python scripts/build.py
"""

import json
import re
import shutil
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Missing dependency. Run:  python -m pip install markdown")

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PAGES = CONTENT / "pages"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

MD_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "smarty"]

AFF_RE = re.compile(r'href="aff:([A-Za-z0-9]+)"')


# ---------------------------------------------------------------- helpers

# Cross-promotion: EmpireHQ/links.json (Desktop\EmpireHQ) is the single source
# of truth for youtube_url / gumroad_url; config.json values are the fallback.
# site_url always comes from config.json (it anchors canonicals/sitemap/RSS).
LINKS_FILE = ROOT.parent / "EmpireHQ" / "links.json"


def load_config():
    with open(ROOT / "config.json", encoding="utf-8") as f:
        cfg = json.load(f)
    try:
        links = json.loads(LINKS_FILE.read_text(encoding="utf-8"))
        for key in ("youtube_url", "gumroad_url"):
            if str(links.get(key) or "").strip():
                cfg[key] = str(links[key]).strip()
    except Exception:
        pass  # missing/unreadable links.json -> plain config.json behavior
    return cfg


def promo_links(cfg):
    """(label, url) pairs for the non-empty cross-promo URLs.
    Empty values yield no pairs, so no dead links ever render."""
    pairs = []
    if str(cfg.get("youtube_url") or "").strip():
        pairs.append(("Watch us on YouTube", str(cfg["youtube_url"]).strip()))
    if str(cfg.get("gumroad_url") or "").strip():
        pairs.append(("Our digital products", str(cfg["gumroad_url"]).strip()))
    return pairs


def promo_links_html(cfg, sep=" &middot; "):
    return sep.join(
        f'<a href="{escape(url)}" rel="noopener" target="_blank">{escape(label)}</a>'
        for label, url in promo_links(cfg)
    )


def load_template(name):
    return (TEMPLATES / name).read_text(encoding="utf-8")


def render(template, **ctx):
    """Tiny mustache-ish renderer: replaces {{key}} tokens."""
    out = template
    for key, val in ctx.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out


def parse_frontmatter(text, path):
    """Returns (meta dict, body str). Frontmatter is --- delimited key: value."""
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip().lower()] = val.strip().strip('"')
            body = parts[2].lstrip("\n")
    for required in ("title", "description", "date"):
        if required not in meta:
            sys.exit(f"ERROR: {path.name} is missing required frontmatter field '{required}'")
    return meta, body


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "page"


def rewrite_affiliate_links(html, tag):
    """aff:ASIN hrefs -> tagged Amazon links, opened in a new tab, rel per Google/FTC."""
    def repl(m):
        asin = m.group(1)
        return (f'href="https://www.amazon.com/dp/{asin}?tag={tag}" '
                f'rel="nofollow sponsored noopener" target="_blank"')
    return AFF_RE.sub(repl, html)


def md_to_html(body, cfg):
    html = markdown.markdown(body, extensions=MD_EXTENSIONS)
    html = rewrite_affiliate_links(html, cfg["affiliate_tag"])
    return wrap_tables(html)


TABLE_RE = re.compile(r"<table>.*?</table>", re.S)


def wrap_tables(html):
    """Wrap every table in a scroll container so wide comparison tables
    don't break the layout on ~380px mobile screens."""
    return TABLE_RE.sub(lambda m: f'<div class="table-wrap">{m.group(0)}</div>', html)


# ---------------------------------------------------------------- FAQ / JSON-LD

MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MD_INLINE_RE = re.compile(r"[*_`]+")


def md_plain(text):
    """Strip basic markdown (links, emphasis, code) for use in JSON-LD text."""
    text = MD_LINK_RE.sub(r"\1", text)
    text = MD_INLINE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_faq(body):
    """Parse an '## FAQ' section from markdown. Supports two shapes:
       **Question?**\\nAnswer paragraph   and   ### Question?\\n\\nAnswer paragraph.
       Returns a list of (question, answer) plain-text tuples."""
    m = re.search(r"^##\s+FAQ\b.*$", body, re.M)
    if not m:
        return []
    section = body[m.end():]
    nxt = re.search(r"^##\s", section, re.M)
    if nxt:
        section = section[: nxt.start()]
    paras = [p.strip() for p in re.split(r"\n\s*\n", section) if p.strip()]
    faqs = []
    i = 0
    while i < len(paras):
        p = paras[i]
        h3 = re.match(r"###\s+(.+)", p)
        if h3:
            if i + 1 < len(paras) and not paras[i + 1].startswith("#"):
                faqs.append((md_plain(h3.group(1)), md_plain(paras[i + 1])))
                i += 2
                continue
            i += 1
            continue
        bold = re.match(r"\*\*(.+?)\*\*\s*(.*)", p, re.S)
        if bold and bold.group(2).strip():
            faqs.append((md_plain(bold.group(1)), md_plain(bold.group(2))))
        i += 1
    return faqs


def jsonld_script(data):
    return ('<script type="application/ld+json">'
            + json.dumps(data, ensure_ascii=False)
            + "</script>")


def article_jsonld(a, cfg, site_url, faqs):
    """Article + BreadcrumbList (+ FAQPage when the article has an FAQ section)."""
    org = {"@type": "Organization", "name": cfg["site_name"], "url": f"{site_url}/"}
    canonical = f'{site_url}/{a["url"]}'
    blocks = [
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": a["title"],
            "description": a["description"],
            "datePublished": a["date_str"],
            "dateModified": a["date_str"],
            "author": org,
            "publisher": org,
            "url": canonical,
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home",
                 "item": f"{site_url}/"},
                {"@type": "ListItem", "position": 2, "name": a["category"],
                 "item": f'{site_url}/category-{slugify(a["category"])}.html'},
                {"@type": "ListItem", "position": 3, "name": a["title"],
                 "item": canonical},
            ],
        },
    ]
    if faqs:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": ans},
                }
                for q, ans in faqs
            ],
        })
    return "\n".join(jsonld_script(b) for b in blocks)


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d")


def rfc822(dt):
    return dt.replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")


# ---------------------------------------------------------------- build steps

def collect_articles(cfg):
    articles = []
    for path in sorted(CONTENT.glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
        slug = slugify(path.stem)
        tags = [t.strip().lower() for t in meta.get("tags", "").split(",") if t.strip()]
        articles.append({
            "slug": slug,
            "url": f"{slug}.html",
            "title": meta["title"],
            "description": meta["description"],
            "date": parse_date(meta["date"]),
            "date_str": meta["date"],
            "category": meta.get("category", "Uncategorized"),
            "tags": tags,
            "html": md_to_html(body, cfg),
            "words": len(body.split()),
            "faqs": extract_faq(body),
        })
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def related_articles(article, articles, limit=3):
    scored = []
    for other in articles:
        if other["slug"] == article["slug"]:
            continue
        score = len(set(article["tags"]) & set(other["tags"]))
        if other["category"] == article["category"]:
            score += 2
        if score:
            scored.append((score, other))
    scored.sort(key=lambda x: (-x[0], x[1]["date"]), reverse=False)
    return [o for _, o in scored[:limit]]


def article_card(a):
    return (
        '<article class="card">'
        f'<p class="card-meta">{escape(a["category"])} &middot; '
        f'<time datetime="{a["date_str"]}">{a["date"].strftime("%b %d, %Y")}</time></p>'
        f'<h3><a href="{a["url"]}">{escape(a["title"])}</a></h3>'
        f'<p>{escape(a["description"])}</p>'
        "</article>"
    )


def build_page(base, cfg, *, title, description, canonical, content,
               og_type="website", jsonld=""):
    links = promo_links_html(cfg)
    return render(
        base,
        site_name=cfg["site_name"],
        site_tagline=cfg["site_tagline"],
        site_url=cfg["site_url"],
        page_title=escape(title),
        meta_description=escape(description),
        canonical_url=canonical,
        og_type=og_type,
        content=content,
        jsonld=jsonld,
        year=datetime.now().year,
        footer_links=f"<p>{links}</p>" if links else "",
    )


def run_content_lint():
    """Non-fatal lint pass: warn about content problems without failing the build."""
    try:
        import lint_content
        issues = lint_content.run_lint(CONTENT)
    except Exception as e:  # lint must never break the build
        print(f"NOTE: content lint skipped ({e})")
        return
    if issues:
        print(f"LINT WARNINGS ({len(issues)}) — build continues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("Content lint: all articles pass.")


def main():
    cfg = load_config()
    out = ROOT / cfg.get("output_dir", "docs")
    site_url = cfg["site_url"].rstrip("/")

    if cfg["affiliate_tag"].startswith("CHANGEME"):
        print("NOTE: affiliate_tag in config.json is still the placeholder "
              "'CHANGEME-20'. Replace it after Amazon Associates approval.")

    # Clean output dir (keep the dir itself so git/OneDrive stay calm)
    out.mkdir(exist_ok=True)
    for item in out.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    base = load_template("base.html")
    article_tpl = load_template("article.html")

    articles = collect_articles(cfg)
    if not articles:
        sys.exit("ERROR: no articles found in content/")

    # --- article pages
    for a in articles:
        rel = related_articles(a, articles)
        related_html = ""
        if rel:
            items = "".join(
                f'<li><a href="{r["url"]}">{escape(r["title"])}</a></li>' for r in rel
            )
            related_html = (f'<aside class="related"><h2>Related articles</h2>'
                            f"<ul>{items}</ul></aside>")
        content = render(
            article_tpl,
            title=escape(a["title"]),
            category=escape(a["category"]),
            category_url=f'category-{slugify(a["category"])}.html',
            date_str=a["date_str"],
            date_human=a["date"].strftime("%B %d, %Y"),
            body=a["html"],
            related=related_html,
        )
        page = build_page(base, cfg, title=f'{a["title"]} — {cfg["site_name"]}',
                          description=a["description"],
                          canonical=f'{site_url}/{a["url"]}',
                          content=content, og_type="article",
                          jsonld=article_jsonld(a, cfg, site_url, a["faqs"]))
        (out / a["url"]).write_text(page, encoding="utf-8")

    # --- categories
    categories = {}
    for a in articles:
        categories.setdefault(a["category"], []).append(a)

    for cat, items in sorted(categories.items()):
        cat_slug = slugify(cat)
        cards = "".join(article_card(a) for a in items)
        content = (f'<h1>{escape(cat)}</h1>'
                   f'<p class="lede">{len(items)} article(s) in this category.</p>'
                   f'<div class="cards">{cards}</div>')
        page = build_page(base, cfg, title=f'{cat} — {cfg["site_name"]}',
                          description=f'All {cfg["site_name"]} articles about {cat.lower()}.',
                          canonical=f"{site_url}/category-{cat_slug}.html",
                          content=content)
        (out / f"category-{cat_slug}.html").write_text(page, encoding="utf-8")

    # --- index
    cat_nav = " ".join(
        f'<a class="pill" href="category-{slugify(c)}.html">{escape(c)} '
        f"({len(items)})</a>"
        for c, items in sorted(categories.items())
    )
    latest = "".join(article_card(a) for a in articles)
    index_content = (
        f'<section class="hero"><h1>{escape(cfg["site_name"])}</h1>'
        f'<p class="lede">{escape(cfg["site_tagline"])}. Every pick here pays for itself '
        f"within months of skipped cafe runs, and we tell you what you give up at each price.</p>"
        f'<nav class="pills" aria-label="Categories">{cat_nav}</nav></section>'
        f"<h2>Latest articles</h2>"
        f'<div class="cards">{latest}</div>'
    )
    site_jsonld = jsonld_script({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": cfg["site_name"],
        "description": cfg["site_description"],
        "url": f"{site_url}/",
    })
    page = build_page(base, cfg, title=f'{cfg["site_name"]} — {cfg["site_tagline"]}',
                      description=cfg["site_description"],
                      canonical=f"{site_url}/", content=index_content,
                      jsonld=site_jsonld)
    (out / "index.html").write_text(page, encoding="utf-8")

    # --- 404 page (GitHub Pages serves 404.html from the publish root)
    content_404 = (
        '<section class="hero" style="text-align:center; padding:3rem 0;">'
        '<h1>404 — page not found</h1>'
        '<p class="lede">That page moved, was renamed, or never existed. '
        "The coffee gear reviews are still here though.</p>"
        f'<p style="margin-top:1.5rem;"><a class="pill" href="{site_url}/">'
        "&larr; Back to the BudgetBrewLab homepage</a></p>"
        "</section>"
    )
    page_404 = build_page(base, cfg, title=f'Page not found — {cfg["site_name"]}',
                          description=f'404 — this {cfg["site_name"]} page does not exist.',
                          canonical=f"{site_url}/404.html", content=content_404)
    # Root-relative asset links so the 404 works from any missing path depth.
    page_404 = (page_404
                .replace('href="style.css"', f'href="{site_url}/style.css"')
                .replace('href="favicon.svg"', f'href="{site_url}/favicon.svg"')
                .replace('href="index.html"', f'href="{site_url}/"')
                .replace('href="about.html"', f'href="{site_url}/about.html"')
                .replace('href="affiliate-disclosure.html"',
                         f'href="{site_url}/affiliate-disclosure.html"')
                .replace('href="rss.xml"', f'href="{site_url}/rss.xml"')
                .replace('href="sitemap.xml"', f'href="{site_url}/sitemap.xml"'))
    (out / "404.html").write_text(page_404, encoding="utf-8")

    # --- static pages (about, affiliate disclosure)
    static_pages = []
    for path in sorted(PAGES.glob("*.md")) if PAGES.exists() else []:
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"), path)
        slug = slugify(path.stem)
        html = md_to_html(body, cfg)
        # Cross-promotion on the About page — only when URLs exist (see promo_links)
        if slug == "about" and promo_links(cfg):
            html += ("<h2>More from us</h2><p>BudgetBrewLab is part of a small "
                     f"family of projects: {promo_links_html(cfg)}.</p>")
        page = build_page(base, cfg, title=f'{meta["title"]} — {cfg["site_name"]}',
                          description=meta["description"],
                          canonical=f"{site_url}/{slug}.html",
                          content=f'<article class="prose">{html}</article>')
        (out / f"{slug}.html").write_text(page, encoding="utf-8")
        static_pages.append({"url": f"{slug}.html", "date_str": meta["date"]})

    # --- static assets
    if STATIC.exists():
        for item in STATIC.iterdir():
            if item.is_file():
                shutil.copy2(item, out / item.name)

    # --- robots.txt
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {site_url}/sitemap.xml\n", encoding="utf-8")

    # --- .nojekyll (skip Jekyll processing on GitHub Pages)
    (out / ".nojekyll").write_text("", encoding="utf-8")

    # --- sitemap.xml (lastmod: article/page frontmatter date; newest date for
    #     index and category pages, since they change whenever content does)
    today = datetime.now().strftime("%Y-%m-%d")
    newest = max((a["date_str"] for a in articles), default=today)
    urls = [(f"{site_url}/", newest)]
    urls += [(f"{site_url}/{a['url']}", a["date_str"]) for a in articles]
    urls += [
        (f"{site_url}/category-{slugify(c)}.html",
         max(a["date_str"] for a in items))
        for c, items in sorted(categories.items())
    ]
    urls += [(f"{site_url}/{p['url']}", p["date_str"]) for p in static_pages]
    entries = "".join(
        f"  <url><loc>{escape(u)}</loc><lastmod>{lm}</lastmod></url>\n"
        for u, lm in urls)
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n", encoding="utf-8")

    # --- rss.xml
    items = ""
    for a in articles[: cfg.get("posts_per_feed", 20)]:
        items += (
            "  <item>\n"
            f"    <title>{escape(a['title'])}</title>\n"
            f"    <link>{site_url}/{a['url']}</link>\n"
            f"    <guid>{site_url}/{a['url']}</guid>\n"
            f"    <pubDate>{rfc822(a['date'])}</pubDate>\n"
            f"    <description>{escape(a['description'])}</description>\n"
            "  </item>\n"
        )
    (out / "rss.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0"><channel>\n'
        f"  <title>{escape(cfg['site_name'])}</title>\n"
        f"  <link>{site_url}/</link>\n"
        f"  <description>{escape(cfg['site_description'])}</description>\n"
        f"  <lastBuildDate>{rfc822(datetime.now())}</lastBuildDate>\n"
        f"{items}</channel></rss>\n", encoding="utf-8")

    # --- summary
    thin = [a for a in articles if a["words"] < 1000]
    faq_count = sum(1 for a in articles if a["faqs"])
    print(f"Built {len(articles)} articles ({faq_count} with FAQPage schema), "
          f"{len(categories)} categories, {len(static_pages)} static pages -> {out}")
    if thin:
        print("WARNING: articles under 1000 words (thin content hurts SEO):")
        for a in thin:
            print(f"  - {a['slug']} ({a['words']} words)")

    # --- content lint (warnings only, never fails the build)
    run_content_lint()


if __name__ == "__main__":
    main()
