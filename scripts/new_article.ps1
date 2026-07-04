# new_article.ps1 — generates ONE new BudgetBrewLab article via Claude Code (headless),
# rebuilds, deploys. Run manually or via the "BrewLab Daily Article" scheduled task.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot   # BrewLab folder
Set-Location $Root

$LogDir = Join-Path $Root "scripts\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }
$Log = Join-Path $LogDir ("article-" + (Get-Date -Format "yyyy-MM-dd-HHmm") + ".log")

function Log($msg) {
    $line = "[$(Get-Date)] $msg"
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Output $line
}

# Locate the Claude Code CLI: PATH first, then the desktop app's bundled copy (any version).
$ClaudeExe = $null
$cmd = Get-Command claude -ErrorAction SilentlyContinue
if ($cmd) { $ClaudeExe = $cmd.Source }
if (-not $ClaudeExe) {
    $candidates = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\claude.exe" -ErrorAction SilentlyContinue |
        Sort-Object { [version]($_.Directory.Name -replace '[^\d.]','') } -Descending
    if ($candidates) { $ClaudeExe = $candidates[0].FullName }
}
if (-not $ClaudeExe) { Log "ERROR: claude CLI not found (PATH or $env:APPDATA\Claude\claude-code)."; exit 1 }
Log "Using claude at: $ClaudeExe"

$CountBefore = (Get-ChildItem "$Root\content\*.md").Count

$Prompt = @"
You are the content engine for the affiliate site at $Root (BudgetBrewLab - budget home coffee gear: grinders, pour-over, espresso, scales, accessories).
1. Read README.md for the editorial standard, and list the existing article titles/topics in content/ (read the frontmatter of each .md file) so you do not repeat a topic.
2. Write ONE new SEO article of 1200+ words on a budget coffee gear topic NOT yet covered. Match the exact frontmatter format of existing files (title, description, date [today], category, tags). Requirements: specific product recommendations with realistic specs and street prices, at least one honest downside per product, a markdown comparison table, an FAQ section, 2-3 internal links to related existing articles (relative .html links), and product links in the form [Product Name](aff:ASIN) using plausible ASINs (note: owner verifies ASINs). Rotate article types: listicle, head-to-head comparison, or how-to guide - pick whichever is least represented.
3. Save it to content/ with a kebab-case filename matching the slug.
4. Run: python scripts/build.py  (use the python on PATH, or $env:LOCALAPPDATA\Programs\Python\Python312-arm64\python.exe if not found) and confirm it succeeds.
"@

# Invoke Claude Code headlessly, with one retry — transient "Not logged in" blips
# have caused scheduled-run failures before (see EmpireHQ history).
# cmd /c so stderr is merged by cmd, not PowerShell: with ErrorActionPreference=Stop,
# PS 5.1 turns any native stderr line piped through 2>&1 into a terminating error.
$PromptFile = Join-Path $LogDir "prompt-tmp.txt"
[System.IO.File]::WriteAllText($PromptFile, $Prompt, (New-Object System.Text.UTF8Encoding $false))
foreach ($attempt in 1..2) {
    Log "Starting article generation (attempt $attempt)..."
    cmd /c "type `"$PromptFile`" | `"$ClaudeExe`" -p --permission-mode acceptEdits >> `"$Log`" 2>&1"
    Log "claude exited with code $LASTEXITCODE"
    if ((Get-ChildItem "$Root\content\*.md").Count -gt $CountBefore) { break }
    if ($attempt -eq 1) { Log "No new article yet - retrying in 60s..."; Start-Sleep -Seconds 60 }
}
Remove-Item $PromptFile -ErrorAction SilentlyContinue

$CountAfter = (Get-ChildItem "$Root\content\*.md").Count
if ($CountAfter -le $CountBefore) {
    Log "WARNING: no new article file detected after 2 attempts. Check the log: $Log"
    exit 1
}

Log "New article created ($CountBefore -> $CountAfter). Deploying..."

# Build + commit + push (cmd /c for the same stderr reason)
cmd /c "powershell -NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $PSScriptRoot 'deploy.ps1')`" >> `"$Log`" 2>&1"
Log "deploy exited with code $LASTEXITCODE"
Log "Done."
