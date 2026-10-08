---
name: web-captcha-handling
description: "Detect and handle captcha/bot-challenge pages (DuckDuckGo, Bing, Firecrawl IP-block) by falling back to real-browser automation or user-assisted solving. Use when webfetch or search returns a captcha challenge instead of results."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [captcha, bot-check, duckduckgo, bing, webfetch, firecrawl, browser, fallback, scraping]
    category: research
    requires_toolsets: [terminal, webfetch]
---

# Web Captcha Handling for DuckDuckGo / Bing

## Purpose
Handle captcha challenges that block automated web search for DuckDuckGo and Bing when searching for `jev` / `laya` and similar queries.

## When to use
- `webfetch` returns a captcha challenge page
- DuckDuckGo returns "Select all squares containing a duck" or similar
- Bing returns a bot verification page
- Firecrawl is blocked by IP suspicion

## Workflow
1. Detect captcha
   - Check response body for keywords: `captcha`, `challenge`, `Select all squares`, `Please complete the following challenge`, `error-lite`
2. Fallback strategy
   - Prefer `faster-chrome-devtools-skill` for real browser automation
   - Use `web-browser` agent for interactive solving
   - If manual solving required, pause and request user input with `question` tool
3. Retry
   - After solving, re-fetch the original URL
   - Cache successful result to avoid repeat challenges

## Implementation notes
- DuckDuckGo HTML endpoint: `https://html.duckduckgo.com/html/?q=...`
- Bing search: `https://www.bing.com/search?q=...`
- Use `faster-chrome-devtools-skill` to:
  - Navigate to search URL
  - Wait for captcha iframe
  - Capture screenshot for user verification
  - Inject solution or wait for user input
- Do not attempt to bypass captcha automatically without user consent

## Safety
- Never store captcha tokens
- Respect site ToS
- Prefer official APIs when available

## Example
```bash
# Detect captcha
webfetch https://html.duckduckgo.com/html/?q=jev+laya
# If captcha detected → launch web-browser agent with faster-chrome-devtools-skill
```

## Related skills
- `faster-chrome-devtools-skill`
- `cdp-skill`
- `web-browser`
