#!/usr/bin/env node
/**
 * Playwright Browser Backend for OpenCode Web Automation.
 *
 * Reads JSON commands from stdin, executes them via Playwright,
 * and writes JSON results to stdout.
 *
 * Usage:
 *   echo '{"action":"navigate","url":"https://example.com"}' | node browser.js
 *
 * Commands:
 *   init           - Launch the browser
 *   close          - Close the browser
 *   navigate       - Go to a URL (with optional wait_until)
 *   click          - Click an element by selector
 *   fill           - Type text into a field
 *   select_option  - Select an option in a dropdown
 *   get_text       - Get text content from a selector
 *   get_attribute  - Get an attribute from a selector
 *   get_html       - Get inner HTML
 *   get_links      - Get all links on the page
 *   get_title      - Get page title
 *   get_url        - Get current URL
 *   screenshot     - Take a screenshot
 *   wait           - Wait for a selector or duration
 *   scroll         - Scroll the page
 *   evaluate       - Run JavaScript in the page context
 *   press          - Press a key
 *   check          - Check/Uncheck a checkbox
 *   upload_file    - Upload a file
 *   form_data      - Get all form field values
 *   submit_form    - Submit a form
 *   get_cookies    - Get all cookies
 *   set_cookies    - Set cookies
 *   clear_cookies  - Clear cookies
 *   get_local_storage  - Get localStorage data
 *   back           - Navigate back
 *   forward        - Navigate forward
 *   reload         - Reload the page
 *   new_page       - Open a new tab
 *   switch_page    - Switch to a tab by index
 *   pages          - List all open pages/tabs
 *   close_page     - Close current page / tab by index
 *   status         - Get browser status
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const http = require('http');

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

let context = null;
let browser = null;
let pages = [];
let currentPageIndex = 0;
let defaultTimeout = 30000;
let chromeProc = null;

const headedState = {
  cdpPort: null,
  dataDir: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getPage() {
  if (!pages.length) throw new Error('No open pages');
  if (currentPageIndex >= pages.length) currentPageIndex = pages.length - 1;
  return pages[currentPageIndex];
}

function result(data) {
  console.log(JSON.stringify({ status: 'ok', data }));
}

function error(msg) {
  console.log(JSON.stringify({ status: 'error', error: msg }));
}

// ---------------------------------------------------------------------------
// Navigation mirroring
// ---------------------------------------------------------------------------

function mirrorNavigation(url) {
  if (!headedState.cdpPort) return;
  const baseUrl = `http://127.0.0.1:${headedState.cdpPort}`;

  http.get(`${baseUrl}/json`, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      try {
        const targets = JSON.parse(data);
        const pages = targets.filter(t => t.type === 'page');
        const toClose = pages.length > 0 ? pages.slice(1) : [];
        toClose.forEach(p => {
          http.get(`${baseUrl}/json/close/${p.id}`, () => {}).on('error', () => {});
        });
        if (pages.length > 0) {
          http.get(`${baseUrl}/json/new?url=${encodeURIComponent(url)}`, () => {}).on('error', () => {});
          setImmediate(() => {
            http.get(`${baseUrl}/json/close/${pages[0].id}`, () => {}).on('error', () => {});
          });
        } else {
          http.get(`${baseUrl}/json/new?url=${encodeURIComponent(url)}`, () => {}).on('error', () => {});
        }
      } catch (e) {}
    });
  }).on('error', () => {});
}

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

const handlers = {};

handlers.init = async (args) => {
  if (context) {
    try { await context.close(); } catch (e) {}
  }
  if (chromeProc) {
    try { chromeProc.kill(); } catch (e) {}
  }
  context = null;
  browser = null;
  pages = [];
  currentPageIndex = 0;
  chromeProc = null;

  const isHeadless = args.headless !== false;
  const userDataDir = `/tmp/playwright_profile_${Date.now()}`;

  if (!isHeadless) {
    try { require('child_process').execSync('pkill -9 -f remote-debugging', { stdio: 'ignore' }); } catch (e) {}
  }

  if (isHeadless) {
    context = await chromium.launchPersistentContext(userDataDir, {
      headless: true,
      executablePath: args.executablePath || '/usr/bin/chromium',
      args: [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        ...(args.args || []),
      ],
      viewport: args.viewport || { width: 1280, height: 720 },
      userAgent: args.userAgent || undefined,
      acceptDownloads: true,
      ...(args.contextOptions || {}),
    });
    browser = context.browser();

  } else {
    context = await chromium.launchPersistentContext(userDataDir, {
      headless: true,
      executablePath: args.executablePath || '/usr/bin/chromium',
      args: [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process',
        ...(args.args || []),
      ],
      viewport: args.viewport || { width: 1280, height: 720 },
      userAgent: args.userAgent || undefined,
      acceptDownloads: true,
      ...(args.contextOptions || {}),
    });
    browser = context.browser();

    const headedPort = 10222 + Math.floor(Math.random() * 9000);
    const headedDataDir = `/tmp/headed_profile_${Date.now()}`;

    const headedArgs = [
      '--no-sandbox',
      '--disable-dev-shm-usage',
      '--no-first-run',
      '--no-default-browser-check',
      '--disable-gpu',
      `--user-data-dir=${headedDataDir}`,
      `--remote-debugging-port=${headedPort}`,
      'about:blank',
    ];

    chromeProc = spawn(args.executablePath || '/usr/bin/chromium', headedArgs, {
      stdio: ['ignore', 'ignore', 'ignore'],
      env: { ...process.env },
    });

    const headedUrl = `http://127.0.0.1:${headedPort}`;
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error(`Headed CDP not ready on port ${headedPort} after 15s`)), 15000);
      const poll = () => {
        http.get(`${headedUrl}/json/version`, (res) => {
          if (res.statusCode === 200) { clearTimeout(timeout); resolve(); }
          else { setTimeout(poll, 300); }
        }).on('error', () => setTimeout(poll, 300));
      };
      poll();
    });

    headedState.cdpPort = headedPort;
    headedState.dataDir = headedDataDir;
  }

  context.on('page', (page) => {
    pages.push(page);
    page.setDefaultTimeout(defaultTimeout);
    page.on('close', () => {
      const idx = pages.indexOf(page);
      if (idx !== -1) {
        pages.splice(idx, 1);
        if (currentPageIndex >= pages.length && pages.length > 0) {
          currentPageIndex = pages.length - 1;
        }
      }
    });
  });

  const ctxPages = context.pages();
  for (const p of ctxPages) {
    p.setDefaultTimeout(defaultTimeout);
    pages.push(p);
  }

  if (pages.length === 0) {
    const newPage = await context.newPage();
    newPage.setDefaultTimeout(defaultTimeout);
    pages.push(newPage);
  }

  currentPageIndex = 0;

  result({
    browser_version: browser ? browser.version() : 'unknown',
    pages_open: pages.length,
    headless: isHeadless,
  });
};

handlers.close = async () => {
  if (context) {
    try { await context.close(); } catch (e) {}
    context = null;
  }
  if (chromeProc) {
    try { chromeProc.kill('SIGTERM'); } catch (e) {}
    chromeProc = null;
  }
  headedState.cdpPort = null;
  headedState.dataDir = null;
  browser = null;
  pages = [];
  currentPageIndex = 0;
  result({ closed: true });
};

handlers.navigate = async (args) => {
  const page = getPage();
  const waitUntil = args.wait_until || 'load';
  const response = await page.goto(args.url, {
    waitUntil,
    timeout: args.timeout || defaultTimeout,
  });
  mirrorNavigation(page.url());
  result({
    url: page.url(),
    title: await page.title(),
    status: response ? response.status() : null,
  });
};

handlers.click = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const options = {};
  if (args.button) options.button = args.button;
  if (args.click_count) options.clickCount = args.click_count;
  if (args.delay) options.delay = args.delay;
  if (args.force) options.force = true;
  if (args.position) options.position = args.position;

  await page.waitForSelector(selector, { timeout: args.timeout || defaultTimeout });
  await page.click(selector, options);
  result({ clicked: selector });
};

handlers.fill = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const value = String(args.value ?? '');

  await page.waitForSelector(selector, { timeout: args.timeout || defaultTimeout });
  await page.fill(selector, value);
  result({ filled: selector, value });
};

handlers.type = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const value = String(args.value ?? '');
  await page.waitForSelector(selector, { timeout: args.timeout || defaultTimeout });
  await page.click(selector);
  await page.type(selector, value, { delay: args.delay || 0 });
  result({ typed: selector, value });
};

handlers.select_option = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const value = args.value;
  await page.waitForSelector(selector, { timeout: args.timeout || defaultTimeout });
  await page.selectOption(selector, value);
  result({ selected: selector, value });
};

handlers.get_text = async (args) => {
  const page = getPage();
  if (args.selector) {
    const el = await page.$$(args.selector);
    const texts = await Promise.all(el.map((e) => e.textContent()));
    result({ texts: texts.map((t) => (t || '').trim()) });
  } else {
    const text = await page.evaluate(() => document.body.innerText);
    result({ text: text.trim() });
  }
};

handlers.get_attribute = async (args) => {
  const page = getPage();
  const attr = await page.getAttribute(args.selector, args.attribute);
  result({ attribute: attr });
};

handlers.get_html = async (args) => {
  const page = getPage();
  if (args.selector) {
    const html = await page.innerHTML(args.selector);
    result({ html });
  } else {
    const html = await page.content();
    result({ html });
  }
};

handlers.get_links = async (args) => {
  const page = getPage();
  const links = await page.$$eval('a[href]', (els) =>
    els.map((el) => ({
      text: (el.textContent || '').trim(),
      href: el.getAttribute('href'),
      title: el.getAttribute('title') || '',
    }))
  );
  const filtered = links.filter((l) => l.href && !l.href.startsWith('javascript:'));
  result({ links: filtered, total: filtered.length });
};

handlers.get_title = async () => {
  const page = getPage();
  result({ title: await page.title() });
};

handlers.get_url = async () => {
  const page = getPage();
  result({ url: page.url() });
};

handlers.screenshot = async (args) => {
  const page = getPage();
  const outputPath = args.path || `/tmp/screenshot_${Date.now()}.png`;
  const options = { path: outputPath, fullPage: args.full_page === true };
  if (args.type) options.type = args.type;
  if (args.quality) options.quality = args.quality;
  await page.screenshot(options);
  const stats = fs.statSync(outputPath);
  result({ path: outputPath, size: stats.size, full_page: !!args.full_page });
};

handlers.wait = async (args) => {
  const page = getPage();
  if (args.selector) {
    const state = args.state || 'visible';
    await page.waitForSelector(args.selector, {
      state,
      timeout: args.timeout || defaultTimeout,
    });
    result({ waited: true, for: `selector '${args.selector}' (${state})` });
  } else if (args.timeout) {
    await new Promise((r) => setTimeout(r, args.timeout));
    result({ waited: true, for: `${args.timeout}ms` });
  } else if (args.function) {
    await page.waitForFunction(args.function, args.arg, { timeout: args.timeout || defaultTimeout });
    result({ waited: true, for: 'function' });
  } else {
    result({ waited: false, error: 'no wait condition specified' });
  }
};

handlers.scroll = async (args) => {
  const page = getPage();
  const x = args.x || 0;
  const y = args.y || 0;
  if (args.selector) {
    await page.$eval(args.selector, (el, { dx, dy }) => {
      el.scrollBy(dx, dy);
    }, { dx: x, dy: y });
  } else {
    await page.evaluate(({ dx, dy }) => window.scrollBy(dx, dy), { dx: x, dy: y });
  }
  result({ scrolled: true, x, y });
};

handlers.evaluate = async (args) => {
  if (!args.function && !args.expression) {
    throw new Error('evaluate requires "function" or "expression"');
  }
  const page = getPage();
  if (args.function) {
    const fn = eval('(' + args.function + ')');
    const result_val = await page.evaluate(fn, args.arg);
    result({ result: result_val });
  } else {
    const result_val = await page.evaluate(args.expression);
    result({ result: result_val });
  }
};

handlers.press = async (args) => {
  const page = getPage();
  const key = args.key;
  if (args.selector) {
    await page.press(args.selector, key);
  } else {
    await page.keyboard.press(key);
  }
  result({ pressed: key });
};

handlers.check = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const checked = args.checked !== false;
  if (checked) {
    await page.check(selector, { timeout: args.timeout || defaultTimeout });
  } else {
    await page.uncheck(selector, { timeout: args.timeout || defaultTimeout });
  }
  result({ selector, checked });
};

handlers.upload_file = async (args) => {
  const page = getPage();
  const selector = args.selector;
  const filePaths = Array.isArray(args.path) ? args.path : [args.path];
  await page.waitForSelector(selector, { timeout: args.timeout || defaultTimeout });
  await page.setInputFiles(selector, filePaths);
  result({ uploaded: selector, files: filePaths });
};

handlers.form_data = async (args) => {
  const page = getPage();
  const selector = args.selector || 'form';
  const data = await page.$$eval(`${selector} input, ${selector} select, ${selector} textarea`, (els) =>
    els.map((el) => ({
      name: el.getAttribute('name') || el.id || '',
      type: el.getAttribute('type') || el.tagName.toLowerCase(),
      value: el.value || '',
      placeholder: el.getAttribute('placeholder') || '',
      id: el.id,
      required: el.required || false,
    }))
  );
  result({ fields: data, count: data.length });
};

handlers.submit_form = async (args) => {
  const page = getPage();
  const selector = args.selector || 'form';
  await page.evaluate((sel) => {
    const form = document.querySelector(sel);
    if (form && form.submit) form.submit();
  }, selector);
  result({ submitted: selector });
};

handlers.get_cookies = async () => {
  if (!context) throw new Error('No browser context');
  const cookies = await context.cookies();
  result({ cookies, count: cookies.length });
};

handlers.set_cookies = async (args) => {
  if (!context) throw new Error('No browser context');
  const cookies = Array.isArray(args.cookies) ? args.cookies : [args.cookies];
  await context.addCookies(cookies);
  result({ set: cookies.length });
};

handlers.clear_cookies = async () => {
  if (!context) throw new Error('No browser context');
  await context.clearCookies();
  result({ cleared: true });
};

handlers.get_local_storage = async (args) => {
  const page = getPage();
  if (args.key) {
    const val = await page.evaluate((k) => localStorage.getItem(k), args.key);
    result({ key: args.key, value: val });
  } else {
    const data = await page.evaluate(() => {
      const all = {};
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        all[k] = localStorage.getItem(k);
      }
      return all;
    });
    result({ data, count: Object.keys(data).length });
  }
};

handlers.back = async () => {
  const page = getPage();
  await page.goBack();
  mirrorNavigation(page.url());
  result({ url: page.url(), title: await page.title() });
};

handlers.forward = async () => {
  const page = getPage();
  await page.goForward();
  mirrorNavigation(page.url());
  result({ url: page.url(), title: await page.title() });
};

handlers.reload = async () => {
  const page = getPage();
  await page.reload();
  mirrorNavigation(page.url());
  result({ url: page.url(), title: await page.title() });
};

handlers.new_page = async (args) => {
  if (!context) throw new Error('No browser context');
  const page = await context.newPage();
  page.setDefaultTimeout(defaultTimeout);
  if (args.url) await page.goto(args.url, { waitUntil: 'load' });
  pages.push(page);
  currentPageIndex = pages.length - 1;
  result({ page_index: currentPageIndex, url: page.url() });
};

handlers.switch_page = async (args) => {
  const idx = args.index;
  if (idx < 0 || idx >= pages.length) throw new Error(`Invalid page index ${idx}, open pages: ${pages.length}`);
  currentPageIndex = idx;
  const page = getPage();
  await page.bringToFront();
  result({ index: idx, url: page.url(), title: await page.title() });
};

handlers.pages = async () => {
  const info = await Promise.all(
    pages.map(async (p, i) => ({
      index: i,
      url: p.url(),
      title: await p.title(),
      current: i === currentPageIndex,
    }))
  );
  result({ pages: info, count: info.length, current: currentPageIndex });
};

handlers.close_page = async (args) => {
  if (pages.length <= 1) {
    throw new Error('Cannot close the last open page');
  }
  const idx = args.index !== undefined ? args.index : currentPageIndex;
  if (idx < 0 || idx >= pages.length) throw new Error(`Invalid page index ${idx}`);
  await pages[idx].close();
  pages.splice(idx, 1);
  if (currentPageIndex >= pages.length) currentPageIndex = pages.length - 1;
  result({ closed_index: idx, pages_remaining: pages.length });
};

handlers.status = async () => {
  result({
    running: !!(context && browser),
    pages_open: pages.length,
    current_page: currentPageIndex,
    browser_version: browser ? browser.version() : null,
  });
};

handlers.wait_for_navigation = async (args) => {
  const page = getPage();
  const waitUntil = args.wait_until || 'load';
  await page.waitForNavigation({ waitUntil, timeout: args.timeout || defaultTimeout });
  result({ url: page.url(), title: await page.title() });
};

handlers.hover = async (args) => {
  const page = getPage();
  await page.waitForSelector(args.selector, { timeout: args.timeout || defaultTimeout });
  await page.hover(args.selector);
  result({ hovered: args.selector });
};

handlers.focus = async (args) => {
  const page = getPage();
  await page.waitForSelector(args.selector, { timeout: args.timeout || defaultTimeout });
  await page.focus(args.selector);
  result({ focused: args.selector });
};

handlers.get_value = async (args) => {
  const page = getPage();
  const value = await page.$eval(args.selector, (el) => el.value);
  result({ selector: args.selector, value });
};

handlers.is_visible = async (args) => {
  const page = getPage();
  const visible = await page.isVisible(args.selector, { timeout: args.timeout || 5000 });
  result({ selector: args.selector, visible });
};

handlers.get_console_logs = async (args) => {
  const page = getPage();
  const logs = [];
  page.on('console', (msg) => {
    logs.push({ type: msg.type(), text: msg.text() });
  });
  if (args.wait_ms) await new Promise((r) => setTimeout(r, args.wait_ms));
  result({ logs });
};

// ---------------------------------------------------------------------------
// Main execution loop
// ---------------------------------------------------------------------------

function readCommand() {
  return new Promise((resolve) => {
    const onData = (chunk) => {
      buffer += chunk;
      const newlineIdx = buffer.indexOf('\n');
      if (newlineIdx !== -1) {
        const line = buffer.substring(0, newlineIdx).trim();
        buffer = buffer.substring(newlineIdx + 1);
        process.stdin.removeListener('data', onData);
        process.stdin.removeListener('end', onEnd);
        if (line) {
          resolve(line);
        } else {
          process.stdin.on('data', onData);
        }
      }
    };
    const onEnd = () => {
      process.stdin.removeListener('data', onData);
      if (buffer.trim()) {
        resolve(buffer.trim());
        buffer = '';
      } else {
        resolve(null);
      }
    };
    process.stdin.on('data', onData);
    process.stdin.on('end', onEnd);
  });
}

let buffer = '';

async function main() {
  process.stdin.setEncoding('utf8');
  process.stdin.setRawMode && process.stdin.setRawMode(false);

  console.log(JSON.stringify({ status: 'ok', data: { backend: 'ready', pid: process.pid } }));

  while (true) {
    const line = await readCommand();
    if (line === null) break;

    let commands;
    try {
      commands = JSON.parse(line);
    } catch (e) {
      console.log(JSON.stringify({ status: 'error', error: `Invalid JSON: ${e.message}` }));
      continue;
    }

    if (!Array.isArray(commands)) commands = [commands];

    for (const cmd of commands) {
      const action = cmd.action;
      const args = cmd.args || cmd;

      if (!action) {
        console.log(JSON.stringify({ status: 'error', error: 'No action specified' }));
        continue;
      }

      const handler = handlers[action];
      if (!handler) {
        console.log(JSON.stringify({ status: 'error', error: `Unknown action: ${action}` }));
        continue;
      }

      try {
        await handler(args);
      } catch (e) {
        console.log(JSON.stringify({ status: 'error', action, error: e.message }));
      }
    }
  }

  if (context) {
    try { await context.close(); } catch (e) {}
  }
  if (chromeProc) {
    try { chromeProc.kill(); } catch (e) {}
  }
}

process.on('unhandledRejection', (err) => {
  error(`Unhandled rejection: ${err.message}`);
  process.exit(1);
});

main().catch((err) => {
  error(`Fatal: ${err.message}`);
  process.exit(1);
});
