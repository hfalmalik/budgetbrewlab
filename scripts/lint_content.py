#!/usr/bin/env python3
"""
BudgetRigLab content linter.

Checks every content/*.md (article) for:
  - 1000+ words in the body
  - required frontmatter fields: title, description, date, category, tags
  - at least one affiliate link (aff:ASIN)
  - at least one comparison table (markdown pipe table)
  - no duplicate titles or slugs across articles

Usage:  python scripts/lint_content.py
Exit code 0 = clean, 1 = issues found. build.py also imports run_lint()
and reports the same issues as non-fatal warnings.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

MIN_WORDS = 1000
REQUIRED_FIELDS = ("title", "description", "date", "category", "tags")
AFF_RE = re.compile(r"\(aff:[A-Za-z0-9]+\)")
TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$", re.M)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_frontmatter(text):
    """Returns (meta dict, body str); meta is {} when no frontmatter block."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip().lower()] = val.strip().strip('"')
    return meta, parts[2]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "page"


def run_lint(content_dir=CONTENT):
    """Lint all top-level articles. Returns a list of human-readable issues."""
    issues = []
    seen_titles = {}
    seen_slugs = {}

    paths = sorted(Path(content_dir).glob("*.md"))
    if not paths:
        return [f"no articles found in {content_dir}"]

    for path in paths:
        name = path.name
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))

        if not meta:
            issues.append(f"{name}: missing or malformed frontmatter block")
        for field in REQUIRED_FIELDS:
            if not meta.get(field):
                issues.append(f"{name}: missing frontmatter field '{field}'")
        if meta.get("date") and not DATE_RE.match(meta["date"]):
            issues.append(f"{name}: date '{meta['date']}' is not YYYY-MM-DD")

        words = len(body.split())
        if words < MIN_WORDS:
            issues.append(f"{name}: only {words} words (minimum {MIN_WORDS})")

        if not AFF_RE.search(body):
            issues.append(f"{name}: no affiliate (aff:ASIN) links")

        if len(TABLE_ROW_RE.findall(body)) < 3:  # header + divider + 1 data row
            issues.append(f"{name}: no comparison table found")

        title = meta.get("title", "").lower()
        if title:
            if title in seen_titles:
                issues.append(f"{name}: duplicate title (also in {seen_titles[title]})")
            else:
                seen_titles[title] = name

        slug = slugify(path.stem)
        if slug in seen_slugs:
            issues.append(f"{name}: duplicate slug '{slug}' (also in {seen_slugs[slug]})")
        else:
            seen_slugs[slug] = name

    return issues


def main():
    issues = run_lint()
    paths = sorted(CONTENT.glob("*.md"))
    if issues:
        print(f"Content lint: {len(issues)} issue(s) across {len(paths)} articles:")
        for issue in issues:
            print(f"  FAIL {issue}")
        sys.exit(1)
    print(f"Content lint: all {len(paths)} articles pass.")


if __name__ == "__main__":
    main()
