# gstack

gstack is installed at `~/.claude/skills/gstack` (user-scoped; all skills registered).

## Web browsing policy
- **Default:** use gstack's `/browse` skill for general web browsing, scraping, and QA.
- **Exception:** when a task requires Hamad's logged-in Chrome session (Amazon/KDP, Gmail, Gumroad, YouTube Studio, banking-adjacent dashboards), use the `mcp__claude-in-chrome__*` tools instead — gstack's browser is a separate Chromium with no logins.

## Available gstack skills
/office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /design-consultation, /design-shotgun, /design-html, /review, /ship, /land-and-deploy, /canary, /benchmark, /browse, /connect-chrome, /qa, /qa-only, /design-review, /setup-browser-cookies, /setup-deploy, /setup-gbrain, /retro, /investigate, /document-release, /document-generate, /codex, /cso, /autoplan, /plan-devex-review, /devex-review, /careful, /freeze, /guard, /unfreeze, /gstack-upgrade, /learn

## Maintenance
- Windows install uses file copies, not symlinks: after any `git pull` in `~/.claude/skills/gstack`, re-run `./setup`.
- `/gstack-upgrade` keeps it current.
