---
name: playwright-patterns
description: Playwright + Chromium patterns for the web-browser agent. Use when navigating sites, filling forms, clicking elements, taking screenshots, scraping data, or booking flights. Captures the patterns that actually work on Alpine + Chromium 136 + Playwright.
license: MIT
compatibility: opencode>=1.16.0
---

# Playwright Patterns

The web-browser agent uses **Playwright (Node.js)** with **Chromium 136** on Alpine. This skill captures the patterns that work in this environment.

## Setup check

```bash
# Verify Playwright is installed
node -e "require('playwright')"

# Verify Chromium is available
which chromium

# For headed mode (VNC display):
which Xvfb x11vnc
```

If any check fails, run `oc-doctor --fix` to repair.

## Common patterns

### 1. Basic navigation

```javascript
const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({
        headless: true,                    // false for headed mode
        args: ['--no-sandbox', '--disable-dev-shm-usage']  // Required for Alpine/Android
    });
    const page = await browser.newPage();
    await page.goto('https://example.com', { waitUntil: 'networkidle' });
    console.log('Title:', await page.title());
    await browser.close();
})();
```

**Critical Alpine args**: `--no-sandbox` and `--disable-dev-shm-usage` are REQUIRED on Alpine (musl) and Android. Without them, Chromium fails to start.

### 2. Form filling

```javascript
await page.fill('input[name="email"]', 'user@example.com');
await page.fill('input[name="password"]', 'secret');
await page.check('input[type="checkbox"][name="agree"]');
await page.selectOption('select[name="country"]', 'US');
await page.click('button[type="submit"]');
```

### 3. Wait strategies

```javascript
// Wait for navigation
await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle' }),
    page.click('a.next-page')
]);

// Wait for element
await page.waitForSelector('.result-loaded', { timeout: 30000 });

// Wait for specific text
await page.waitForFunction(() => 
    document.body.innerText.includes('Success')
);

// Wait for network to be idle (after AJAX)
await page.waitForLoadState('networkidle');
```

### 4. Screenshots

```javascript
// Full page
await page.screenshot({ path: '/tmp/full.png', fullPage: true });

// Specific element
const element = await page.$('.chart');
await element.screenshot({ path: '/tmp/chart.png' });

// With options
await page.screenshot({
    path: '/tmp/shot.png',
    fullPage: true,
    type: 'png',
    omitBackground: false,
});
```

### 5. Data extraction

```javascript
// Single element
const title = await page.textContent('h1');

// Multiple elements
const items = await page.$$eval('.item', els => els.map(e => e.textContent));

// Attribute
const href = await page.getAttribute('a', 'href');

// Form data
const formData = await page.evaluate(() => {
    return {
        title: document.title,
        url: location.href,
        cookies: document.cookie,
    };
});
```

### 6. Use cheerio for HTML parsing (faster than browser eval)

```javascript
const cheerio = require('cheerio');
const html = await page.content();
const $ = cheerio.load(html);
const titles = $('h2').map((i, el) => $(el).text()).get();
```

### 7. File upload

```javascript
const fileInput = await page.$('input[type="file"]');
await fileInput.setInputFiles('/path/to/file.pdf');
// Or multiple files:
await fileInput.setInputFiles(['file1.pdf', 'file2.pdf']);
```

### 8. Cookie/session management

```javascript
// Save cookies
const cookies = await page.context().cookies();

// Restore cookies
await page.context().addCookies(cookies);

// Local storage
await page.evaluate(() => localStorage.setItem('token', 'abc123'));
const token = await page.evaluate(() => localStorage.getItem('token'));
```

## Anti-detection (use carefully)

```javascript
await page.setExtraHTTPHeaders({
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...',
    'Accept-Language': 'en-US,en;q=0.9',
});

// Random delays
await page.waitForTimeout(1000 + Math.random() * 2000);

// Viewport variation
await page.setViewportSize({ width: 1280, height: 800 });
```

**Note**: Use anti-detection only for legitimate use cases. Respect robots.txt.

## Alpine-specific gotchas

| Issue | Cause | Fix |
|-------|-------|-----|
| `Browser closed unexpectedly` | Missing --no-sandbox | Add `args: ['--no-sandbox']` |
| `Cannot create /dev/shm` | shm too small | Add `--disable-dev-shm-usage` |
| `Failed to launch: Host system is missing` | Missing libs | `apk add nss freetype harfbuzz` |
| `TimeoutError: Timeout exceeded` | Slow page | Increase `timeout` in waitFor |
| `Target page, context or browser has been closed` | Browser crashed | Catch error, restart with `chromium.launch()` |

## The full pipeline (Playwright + VNC)

For headed mode with VNC viewing:

```bash
# 1. Start display
oc-display start  # or ensure_display()

# 2. Set DISPLAY env
export DISPLAY=:99

# 3. Run Playwright with headless=false
node script.js  # with headless: false in launch()
```

The `display-agent` handles this — invoke it first to get VNC connection info.

## When to use

- Navigating to a URL the user provides
- Filling out a form
- Booking (flights, hotels, restaurants)
- Scraping data from a page
- Taking screenshots
- Testing a web app

## When NOT to use

- Read-only fetch (use `webfetch` tool — much faster)
- Search (use `websearch` tool)
- Bulk scraping (use `firecrawl` MCP instead — it's designed for it)
- The user just wants a URL preview (use `webfetch`)
