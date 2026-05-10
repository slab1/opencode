/**
 * OpenCode Acode Plugin — Main Plugin Class
 *
 * Ties together the OpenCode client, commands, and UI.
 * This is the core of the Acode plugin.
 */

(function () {
  const PLUGIN_ID = 'com.opencode.acode';
  const DEFAULT_PORT = 9878; // CORS proxy (server runs on 9876, proxy on 9878)

  /**
   * Initialize the plugin.
   * Called by Acode when the plugin is navigated to in the sidebar.
   *
   * @param {string} baseUrl - Plugin base URL for accessing assets
   * @param {object} $page - WcPage instance for displaying UI
   * @param {object} cache - Plugin cache { cacheFile, cacheFileUrl, firstInit, ctx }
   */
  function init(baseUrl, $page, cache) {
    // ── Configuration ──────────────────────────────
    const config = loadConfig(cache);

    // ── Set up OpenCode client ─────────────────────
    const serverUrl = `http://127.0.0.1:${config.port || DEFAULT_PORT}`;
    const client = new window.__OpencodeClient(serverUrl);

    // ── Set up UI helpers ─────────────────────────
    const ui = window.__OpencodeUI($page);

    // ── Show page content so Acode renders properly ──
    try {
      if ($page) {
        $page.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--text-secondary,#888);">' +
          'OpenCode AI is active. Use the OC button (bottom-right) or Ctrl+Shift+[A/F/E/G/M/H/S/D].' +
          '</div>';
        $page.show();
      }
    } catch (e) {}

    // ── Register commands ─────────────────────────
    window.__OpencodeCommands.register(client, ui);

    // ── Show welcome on first install ──────────────
    if (cache.firstInit) {
      showWelcome($page, ui, client, config);
    }

    // ── Background health check ────────────────────
    checkServerStatus(client, ui);
  }

  /**
   * Clean up when the plugin is unloaded (acode.setPluginUnmount).
   * Removes all registered commands.
   * Note: Floating button, keydown listener, and $page cleanup
   * are handled by destroyPlugin() in main.js.
   */
  function destroy() {
    window.__OpencodeCommands.unregister();
  }

  // ─── Configuration ────────────────────────────────

  function loadConfig(cache) {
    const defaults = { port: DEFAULT_PORT, agent: 'build' };
    try {
      if (cache && cache.ctx) {
        const cfg = { ...defaults };
        if (cache.ctx.port !== undefined && cache.ctx.port !== null && cache.ctx.port !== '') {
          cfg.port = Number(cache.ctx.port);
        }
        if (cache.ctx.agent !== undefined && cache.ctx.agent !== null && cache.ctx.agent !== '') {
          cfg.agent = String(cache.ctx.agent);
        }
        return cfg;
      }
    } catch {}
    return defaults;
  }

  // Note: Settings are persisted automatically by Acode via
  // acode.setPluginInit's settings `list`. Each setting's `key`
  // maps directly to cache.ctx.<key> (e.g., cache.ctx.port).
  // No manual saveConfig is needed.

  // ─── Welcome Screen ────────────────────────────────

  function showWelcome($page, ui, client, config) {
    const serverUrl = `http://127.0.0.1:${config.port || DEFAULT_PORT}`;

    $page.innerHTML = `
      <div style="padding: 20px; font-family: sans-serif;">
        <h2 style="margin: 0 0 8px; font-size: 18px;">Welcome to OpenCode 🚀</h2>
        <p style="color: var(--text-secondary, #888); font-size: 13px; line-height: 1.6;">
          OpenCode brings AI-powered coding assistance to Acode.
        </p>

        <div style="
          margin: 16px 0; padding: 12px; border-radius: 6px;
          background: var(--bg-secondary, #1a1a2e); font-size: 13px;
        ">
          <strong style="display:block;margin-bottom:6px;">Getting Started:</strong>
          <ol style="margin: 0; padding-left: 20px; line-height: 1.8;">
            <li><strong>Open Termux</strong> on your device</li>
            <li>Run: <code style="background:#333;padding:1px 4px;border-radius:3px;">opencode serve --port ${config.port || DEFAULT_PORT}</code></li>
            <li>Come back here and run <strong>Ctrl+Shift+A</strong> to ask a question</li>
          </ol>
        </div>

        <div style="
          padding: 8px 12px; border-radius: 6px;
          background: rgba(45, 127, 249, 0.1);
          border: 1px solid rgba(45, 127, 249, 0.3);
          font-size: 12px; color: var(--text-secondary, #888);
        ">
          <strong>⚡ Quick Commands:</strong><br>
          Ctrl+Shift+A → Ask OpenCode<br>
          Ctrl+Shift+F → Fix selected code<br>
          Ctrl+Shift+E → Explain selected code<br>
          Ctrl+Shift+G → Generate code<br>
          Ctrl+Shift+M → Multi-file ask<br>
          Ctrl+Shift+H → Chat history
        </div>
      </div>
    `;
    $page.show();
  }

  // ─── Server Status Check ──────────────────────────

  async function checkServerStatus(client, ui) {
    const ok = await client.healthCheck();
    if (!ok) {
      // Show a subtle indicator that the server isn't running
      console.log('[OpenCode] Server not reachable. Run `opencode serve --port 9876` in Termux.');
    } else {
      console.log('[OpenCode] Server connected and ready.');
    }
  }

  // ─── Register Lifecycle Hooks ─────────────────────

  /**
   * Register plugin init/unmount with Acode.
   * This must be called at the top level of main.js.
   */
  function registerLifecycle() {
    acode.setPluginInit(PLUGIN_ID, init, {
      list: [
        {
          key: 'port',
          text: 'Server Port',
          info: 'Port to connect to. Default 9878 (CORS proxy). If running opencode serve directly without proxy, use 9876.',
          value: DEFAULT_PORT,
          prompt: 'Change Port',
          promptType: 'number',
          // Phase 2.2: Live reconnect on port change
          cb: function (key, value) {
            const newUrl = `http://127.0.0.1:${value}`;
            window.__OpencodeClient = new window.__OpencodeClient(newUrl);
            // Note: In the bundled main.js, _activeClient is used instead
          },
        },
        {
          key: 'agent',
          text: 'Default Agent',
          info: 'OpenCode agent to use (build, debug, plan, architect, etc.)',
          value: 'build',
          prompt: 'Change Agent',
          promptType: 'text',
          // Phase 2.2: Agent is used on next prompt, no reconnect needed
          cb: function (key, value) {
            console.log('[OpenCode] Agent changed to:', value);
          },
        },
      ],
    });

    acode.setPluginUnmount(PLUGIN_ID, destroy);
  }

  // ─── Bootstrap ─────────────────────────────────

  registerLifecycle();
})();
