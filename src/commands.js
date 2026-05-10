/**
 * OpenCode Acode Plugin — Command Registrations
 *
 * Registers editor commands that connect to the OpenCode server.
 */

(function () {
  const PLUGIN_ID = 'com.opencode.acode';

  /**
   * Register all OpenCode commands.
   * @param {import('./client.js').default} client - OpenCode client instance
   * @param {object} ui - UI helpers { showPanel, showToast, showProgress }
   */
  function registerCommands(client, ui) {
    const commands = acode.require('commands');

    // ─── Ask OpenCode ─────────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.ask`,
      description: 'Ask OpenCode about the current file or selection',
      bindKey: { win: 'Ctrl-Shift-A', mac: 'Cmd-Shift-A' },
      exec: (view) => handleAsk(client, ui, view),
    });

    // ─── Fix Code ─────────────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.fix`,
      description: 'Fix selected code with OpenCode',
      bindKey: { win: 'Ctrl-Shift-F', mac: 'Cmd-Shift-F' },
      exec: (view) => handleFix(client, ui, view),
    });

    // ─── Explain Code ────────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.explain`,
      description: 'Explain selected code with OpenCode',
      bindKey: { win: 'Ctrl-Shift-E', mac: 'Cmd-Shift-E' },
      exec: (view) => handleExplain(client, ui, view),
    });

    // ─── Generate Code ──────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.generate`,
      description: 'Generate code from description with OpenCode',
      bindKey: { win: 'Ctrl-Shift-G', mac: 'Cmd-Shift-G' },
      exec: (view) => handleGenerate(client, ui, view),
    });

    // ─── Multi-file Ask ──────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.multifile`,
      description: 'Ask OpenCode with multiple open files as context',
      bindKey: { win: 'Ctrl-Shift-M', mac: 'Cmd-Shift-M' },
      exec: () => handleMultiFileAsk(client, ui),
    });

    // ─── Chat History ────────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.history`,
      description: 'View OpenCode chat history',
      bindKey: { win: 'Ctrl-Shift-H', mac: 'Cmd-Shift-H' },
      exec: () => handleHistory(client, ui),
    });

    // ─── Health Check ────────────────────────────
    commands.addCommand({
      name: `${PLUGIN_ID}.status`,
      description: 'Check OpenCode server status',
      exec: () => handleStatus(client, ui),
    });
  }

  /**
   * Remove all OpenCode commands.
   */
  function unregisterCommands() {
    const commands = acode.require('commands');
    const prefix = PLUGIN_ID;
    const all = commands.registry.list();
    all.forEach((cmd) => {
      if (cmd.name && cmd.name.startsWith(prefix)) {
        commands.removeCommand(cmd.name);
      }
    });
  }

  // ─── History Storage ────────────────────────────
  const HISTORY_KEY = 'opencode:history';
  const MAX_HISTORY = 50;

  function saveToHistory(entry) {
    let history = getHistory();
    history.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      timestamp: Date.now(),
      ...entry,
    });
    if (history.length > MAX_HISTORY) {
      history = history.slice(0, MAX_HISTORY);
    }
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (e) {
      if (e.name === 'QuotaExceededError') {
        // Storage full — trim more aggressively and retry
        history = history.slice(0, 20);
        try {
          localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
        } catch (_) {}
      }
      console.error('[OpenCode] Failed to save history:', e);
    }
  }

  function getHistory() {
    try {
      const data = localStorage.getItem(HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  function clearHistory() {
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch (e) {
      console.error('[OpenCode] Failed to clear history:', e);
    }
  }

  // ─── Multi-file Helpers ─────────────────────────

  /**
   * Get all open editors from Acode's editor manager.
   * @returns {Array<{editor: object, filename: string, content: string}>}
   */
  function getAllOpenEditors() {
    const result = [];
    try {
      let editors = [];
      if (editorManager && typeof editorManager.editors !== 'undefined') {
        editors = editorManager.editors;
      }
      // Fallback: try to iterate if it's not an array (e.g. object map)
      if (!Array.isArray(editors)) {
        const vals = Object.values(editors);
        if (Array.isArray(vals)) editors = vals;
      }
      if (editors.length === 0 && editorManager && editorManager.editor) {
        editors = [editorManager.editor];
      }
      for (let i = 0; i < editors.length; i++) {
        const ed = editors[i];
        if (!ed || !ed.state || !ed.state.doc) continue;
        try {
          const filename = (ed.getOption && ed.getOption('filename')) || 'untitled-' + (i + 1);
          const content = ed.state.doc.toString();
          if (content) {
            result.push({ editor: ed, filename, content });
          }
        } catch (e) {
          console.warn('[OpenCode] Skipping editor ' + i + ': ' + e.message);
        }
      }
    } catch (e) {
      console.error('[OpenCode] Failed to list editors:', e);
    }
    return result;
  }

  /**
   * Show a file picker overlay for multi-file selection.
   * @param {Array<{editor, filename, content}>} editors
   * @param {function(Array<{editor, filename, content}>)} onSelect - Called with selected files
   */
  function showFilePicker(editors, onSelect) {
    const overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    let listHtml = '';
    for (let i = 0; i < editors.length; i++) {
      const f = editors[i].filename;
      const size = editors[i].content.length;
      const label = size > 1024 ? (size / 1024).toFixed(1) + 'KB' : size + 'B';
      const checked = i < 10 ? 'checked' : ''; // Auto-check first 10 files
      listHtml +=
        '<label style="display:flex;align-items:center;gap:8px;padding:6px 4px;' +
        'border-bottom:1px solid #333;cursor:pointer;font-size:12px;">' +
        '<input type="checkbox" id="oc-file-' + i + '" ' + checked +
        ' style="width:16px;height:16px;accent-color:#2d7ff9;">' +
        '<span style="flex:1;color:var(--text-primary,#c9d1d9);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
        escapeHtml(f) + '</span>' +
        '<span style="color:var(--text-secondary,#888);font-size:11px;">' + label + '</span></label>';
    }

    overlay.innerHTML =
      '<div style="max-width:92%;max-height:80vh;width:480px;' +
      'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
      'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
      '<h3 style="margin:0 0 4px;font-size:15px;color:var(--text-primary,#c9d1d9);">' +
      'Select Files for Context</h3>' +
      '<p style="margin:0 0 12px;font-size:11px;color:var(--text-secondary,#888);">' +
      editors.length + ' file(s) open. Check the files to include.</p>' +
      '<div style="max-height:50vh;overflow-y:auto;margin-bottom:12px;">' +
      listHtml + '</div>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;">' +
      '<button id="oc-pick-ask" style="padding:6px 16px;border:none;' +
      'background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Ask with ' + editors.length + ' files</button>' +
      '<button id="oc-pick-cancel" style="padding:6px 16px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Cancel</button></div></div>';

    document.body.appendChild(overlay);

    // Update button label as checkboxes change
    const updateLabel = () => {
      const count = overlay.querySelectorAll('input[type=checkbox]:checked').length;
      document.getElementById('oc-pick-ask').textContent = 'Ask with ' + count + ' file(s)';
    };
    overlay.querySelectorAll('input[type=checkbox]').forEach(function (cb) {
      cb.onchange = updateLabel;
    });

    document.getElementById('oc-pick-ask').onclick = function () {
      const selected = [];
      overlay.querySelectorAll('input[type=checkbox]:checked').forEach(function (cb) {
        const idx = parseInt(cb.id.replace('oc-file-', ''), 10);
        if (editors[idx]) selected.push(editors[idx]);
      });
      overlay.remove();
      if (selected.length > 0) {
        onSelect(selected);
      }
    };

    document.getElementById('oc-pick-cancel').onclick = function () {
      overlay.remove();
    };
  }

  // ─── Command Handlers ──────────────────────────

  async function handleAsk(client, ui, view) {
    const { text, selection } = getEditorContext(view);
    if (!text) {
      ui.showToast('No file content available');
      return;
    }

    const prompt = buildPrompt('ask', text, selection);
    await executePrompt(client, ui, prompt, { applyEdits: false });
  }

  async function handleFix(client, ui, view) {
    const { text, selection } = getEditorContext(view);
    if (!text) {
      ui.showToast('No file content available');
      return;
    }
    if (!selection && !ui.confirm('No text selected. Fix the entire file?')) {
      return;
    }

    const prompt = buildPrompt('fix', text, selection);
    await executePrompt(client, ui, prompt, { applyEdits: true });
  }

  async function handleExplain(client, ui, view) {
    const { text, selection } = getEditorContext(view);
    if (!text) {
      ui.showToast('No file content available');
      return;
    }
    if (!selection) {
      ui.showToast('Select some code first to explain it');
      return;
    }

    const prompt = buildPrompt('explain', text, selection);
    await executePrompt(client, ui, prompt, { applyEdits: false });
  }

  async function handleGenerate(client, ui, view) {
    const description = window.prompt('Describe the code to generate:');
    if (!description || !description.trim()) {
      ui.showToast('Generation cancelled');
      return;
    }

    // Detect language from editor file name
    let lang = 'code';
    try {
      if (editorManager && editorManager.editor) {
        const ed = editorManager.editor;
        let filename = '';
        if (typeof ed.getOption === 'function') {
          filename = ed.getOption('filename') || '';
        }
        if (filename) {
          const parts = filename.split('.');
          if (parts.length > 1) lang = parts[parts.length - 1];
        }
      }
    } catch (e) {}

    const prompt =
      `Generate ${lang} code for the following request. ` +
      `Return ONLY the code without explanations, wrapped in a code block.\n\n` +
      description;

    ui.showToast(`Generating ${lang} code...`);
    await executePrompt(client, ui, prompt, { applyEdits: false });
  }

  async function handleStatus(client, ui) {
    const ok = await client.healthCheck();
    if (ok) {
      const agents = await client.listAgents().catch(() => []);
      const agentList = (agents || []).map((a) => a.id || a.name).join(', ');
      ui.showToast(
        `✓ OpenCode server is running\nAgents: ${agentList || 'unknown'}`
      );
    } else {
      ui.showToast(
        '✗ OpenCode server not reachable\nStart it in Termux: opencode serve --port 9876'
      );
    }
  }

  // ─── Multi-file Ask ────────────────────────────

  async function handleMultiFileAsk(client, ui) {
    const editors = getAllOpenEditors();
    if (editors.length === 0) {
      ui.showToast('No open files available');
      return;
    }
    if (editors.length === 1) {
      // Single file — just do a normal ask
      const { text, selection } = getEditorContext(editors[0].editor);
      if (!text) {
        ui.showToast('No file content available');
        return;
      }
      const prompt = buildPrompt('ask', text, selection);
      await executePrompt(client, ui, prompt, { applyEdits: false, mode: 'multi', files: editors });
      return;
    }

    // Multiple files — show file picker, then ask question, then execute
    showFilePicker(editors, function (selected) {
      const question = window.prompt('Ask about the selected files:');
      if (!question || !question.trim()) {
        ui.showToast('Multi-file ask cancelled');
        return;
      }
      const fullPrompt = buildMultiFilePrompt(selected, question);
      ui.showToast('Asking with ' + selected.length + ' file(s)...');
      executePrompt(client, ui, fullPrompt, { applyEdits: true, mode: 'multi', files: selected });
    });
  }

  // ─── History ────────────────────────────────────

  async function handleHistory(client, ui) {
    const history = getHistory();
    if (history.length === 0) {
      ui.showToast('No chat history yet');
      return;
    }
    showHistoryList(history, function (entry) {
      // Show the selected history entry in detail
      showHistoryDetail(entry, function () {
        // Re-ask: send the same prompt again
        ui.showToast('Re-asking...');
        executePrompt(client, ui, entry.prompt, {
          applyEdits: entry.diffs && entry.diffs.length > 0,
          mode: entry.mode || 'single',
          files: entry.files ? entry.files.map(function (f) {
            // Try to find the editor for this filename
            const editors = getAllOpenEditors();
            var match = null;
            for (var i = 0; i < editors.length; i++) {
              if (editors[i].filename === f || editors[i].filename.endsWith('/' + f) || editors[i].filename.endsWith('\\' + f)) {
                match = editors[i];
                break;
              }
            }
            return match || { filename: f, content: '', editor: null };
          }) : [],
        });
      });
    });
  }

  /**
   * Show history list overlay.
   */
  function showHistoryList(history, onSelect) {
    const overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    var listHtml = '';
    for (var i = 0; i < history.length; i++) {
      var h = history[i];
      var date = new Date(h.timestamp);
      var timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      var preview = (h.prompt || '').slice(0, 80) + ((h.prompt || '').length > 80 ? '...' : '');
      var badge = (h.mode || 'single') === 'multi' ? 'MF' : (h.agent || 'build').charAt(0).toUpperCase();
      listHtml +=
        '<div class="oc-history-item" data-idx="' + i + '" style="' +
        'padding:8px 10px;border-bottom:1px solid #333;cursor:pointer;' +
        'transition:background 0.15s;border-radius:4px;" ' +
        'onmouseenter="this.style.background=\'rgba(45,127,249,0.1)\'" ' +
        'onmouseleave="this.style.background=\'transparent\'">' +
        '<div style="display:flex;align-items:center;gap:8px;">' +
        '<span style="background:var(--accent-color,#2d7ff9);color:#fff;border-radius:3px;' +
        'padding:1px 5px;font-size:10px;font-weight:bold;">' + badge + '</span>' +
        '<span style="flex:1;font-size:12px;color:var(--text-primary,#c9d1d9);overflow:hidden;' +
        'text-overflow:ellipsis;white-space:nowrap;">' + escapeHtml(preview) + '</span>' +
        '<span style="font-size:10px;color:var(--text-secondary,#888);white-space:nowrap;">' + timeStr + '</span>' +
        '</div></div>';
    }

    overlay.innerHTML =
      '<div style="max-width:92%;max-height:80vh;width:500px;' +
      'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
      'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">' +
      '<h3 style="margin:0;font-size:15px;color:var(--text-primary,#c9d1d9);">Chat History (' + history.length + ')</h3>' +
      '<div style="display:flex;gap:6px;">' +
      '<button id="oc-history-clear" style="padding:3px 10px;border:1px solid #e44;' +
      'background:transparent;color:#e44;border-radius:4px;cursor:pointer;font-size:11px;">Clear</button>' +
      '<button id="oc-history-close" style="padding:3px 10px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:11px;">Close</button>' +
      '</div></div>' +
      '<div style="max-height:55vh;overflow-y:auto;">' + listHtml + '</div></div>';

    document.body.appendChild(overlay);

    // Click handlers for history items (delegation)
    overlay.addEventListener('click', function (e) {
      var item = e.target.closest('.oc-history-item');
      if (item) {
        var idx = parseInt(item.dataset.idx, 10);
        var entry = history[idx];
        if (entry) {
          overlay.remove();
          onSelect(entry);
        }
      }
    });

    document.getElementById('oc-history-clear').onclick = function () {
      if (window.confirm('Clear all chat history?')) {
        clearHistory();
        overlay.remove();
      }
    };

    document.getElementById('oc-history-close').onclick = function () {
      overlay.remove();
    };
  }

  /**
   * Show a single history entry in detail.
   */
  function showHistoryDetail(entry, onReAsk) {
    const overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    var date = new Date(entry.timestamp);
    var timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    var promptHtml = escapeHtml(entry.prompt || '(no prompt)');
    var responseHtml = escapeHtml(entry.response || '(no response)');

    overlay.innerHTML =
      '<div style="max-width:92%;max-height:85vh;width:550px;' +
      'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
      'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">' +
      '<h3 style="margin:0;font-size:15px;color:var(--text-primary,#c9d1d9);">Conversation</h3>' +
      '<span style="font-size:11px;color:var(--text-secondary,#888);">' + timeStr + '</span></div>' +
      '<div style="margin-bottom:10px;padding:8px 10px;border-radius:6px;' +
      'background:var(--bg-secondary,#1a1a2e);font-size:12px;color:var(--text-secondary,#888);' +
      'word-wrap:break-word;">' +
      '<strong style="color:var(--accent-color,#2d7ff9);">Prompt:</strong> ' + promptHtml + '</div>' +
      '<div style="padding:10px;border-radius:6px;background:#0d1117;font-size:13px;' +
      'color:var(--text-primary,#c9d1d9);white-space:pre-wrap;word-wrap:break-word;' +
      'max-height:40vh;overflow-y:auto;line-height:1.5;">' + responseHtml + '</div>';

    // Show diffs if available
    if (entry.diffs && entry.diffs.length > 0) {
      overlay.innerHTML += '<div style="margin-top:8px;font-size:11px;color:var(--text-secondary,#888);">' +
        entry.diffs.length + ' change(s) were applied.</div>';
    }

    // Show filenames if multi-file
    if (entry.files && entry.files.length > 0) {
      overlay.innerHTML += '<div style="margin-top:4px;font-size:11px;color:var(--text-secondary,#888);">' +
        'Files: ' + entry.files.join(', ') + '</div>';
    }

    overlay.innerHTML +=
      '<div style="margin-top:12px;display:flex;gap:8px;justify-content:flex-end;">' +
      '<button id="oc-hist-ask" style="padding:6px 16px;border:none;' +
      'background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Re-ask</button>' +
      '<button id="oc-hist-close" style="padding:6px 16px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">Close</button></div></div>';

    document.body.appendChild(overlay);

    document.getElementById('oc-hist-ask').onclick = function () {
      overlay.remove();
      onReAsk();
    };

    document.getElementById('oc-hist-close').onclick = function () {
      overlay.remove();
    };
  }

  /**
   * Build a prompt for multi-file context.
   */
  function buildMultiFilePrompt(selectedFiles, question) {
    var context = 'You are analyzing multiple open files. ' +
      'Here are the files I have open:\n\n';

    var totalSize = 0;
    for (var i = 0; i < selectedFiles.length; i++) {
      var f = selectedFiles[i];
      var content = f.content;
      var ext = f.filename.split('.').pop();

      // Truncate very large files at 50KB
      if (content.length > 51200) {
        content = content.slice(0, 51200) + '\n// [... file truncated at 50KB ...]';
      }

      context += '--- FILE: ' + f.filename + ' ---\n';
      context += '```' + ext + '\n' + content + '\n```\n\n';
      totalSize += content.length;
    }

    if (totalSize > 500000) {
      context += '[Warning: Total context size is ' + (totalSize / 1024).toFixed(1) +
        'KB. Consider selecting fewer files.]\n\n';
    }

    context += 'When providing code changes, reference each file by its path.\n\n';
    context += 'My request: ' + question;

    return context;
  }

  // ─── Core Prompt Executor ─────────────────────

  async function executePrompt(client, ui, promptText, opts = {}) {
    const { applyEdits = false, mode = 'single', files = [] } = opts;

    // Health check first
    const ok = await client.healthCheck();
    if (!ok) {
      ui.showToast(
        'Cannot reach OpenCode server.\nRun `opencode serve --port 9876` in Termux'
      );
      return;
    }

    const progress = ui.showProgress('OpenCode is thinking...');

    try {
      // Create a session and send the prompt
      await client.createSession('build');
      const result = await client.prompt(promptText, { timeout: 120000 });

      progress.dismiss();

      if (!result.content) {
        ui.showToast('OpenCode returned an empty response');
        return;
      }

      // ── Save to history (BEFORE showing panel, in case panel render throws) ──
      saveToHistory({
        prompt: promptText,
        response: result.content,
        diffs: result.diffs || [],
        agent: 'build',
        mode: mode,
        files: files.map(function (f) { return f.filename || 'unknown'; }),
      });

      // Show the response
      const panel = ui.showPanel(result.content, promptText);

      // Build editor map for multi-file diff routing
      var editorMap = null;
      if (files.length > 0) {
        editorMap = {};
        for (var i = 0; i < files.length; i++) {
          var f = files[i];
          if (f.filename) {
            editorMap[f.filename] = f.editor;
            // Also add basename-only key for fuzzy matching
            var base = f.filename.split('/').pop().split('\\').pop();
            if (base && base !== f.filename) {
              editorMap[base] = f.editor;
            }
          }
        }
      }

      // Optionally apply edits from the response (with diff preview)
      if (applyEdits && result.diffs && result.diffs.length > 0) {
        panel.addButton('Apply Changes', function () {
          showDiffPreview(result.diffs, function () {
            applyDiffs(result.diffs, editorMap);
            ui.showToast('Applied ' + result.diffs.length + ' change(s)');
          });
        });
      }

      // Clean up the session after a delay
      setTimeout(function () { client.deleteSession().catch(function () {}); }, 5000);
    } catch (err) {
      progress.dismiss();
      ui.showToast('OpenCode error: ' + err.message);
    }
  }

  // ─── Helpers ──────────────────────────────────

  function getEditorContext(view) {
    const doc = view.state.doc;
    const text = doc.toString();
    const sel = view.state.selection.main;

    let selection = '';
    if (!sel.empty) {
      selection = text.slice(sel.from, sel.to);
    }

    return { text, selection, from: sel.from, to: sel.to };
  }

  function buildPrompt(mode, fullText, selection) {
    const context = selection
      ? `SELECTED CODE:\n\`\`\`\n${selection}\n\`\`\``
      : `FILE CONTENT:\n\`\`\`\n${fullText}\n\`\`\``;

    const instructions = {
      ask: `You are a helpful coding assistant. Analyze the following code and respond to my request.\n\n${context}`,
      fix: `Review the following code for bugs, errors, and improvements. Return ONLY the corrected code without explanations. Preserve the exact same structure and style.\n\n${context}`,
      explain: `Explain the following code in simple terms. Describe what it does, key patterns used, and any potential issues.\n\n${context}`,
    };

    return instructions[mode] || instructions.ask;
  }

  function applyDiffs(diffs, editorMap) {
    if (!diffs || diffs.length === 0) return;

    // If we have an editor map (multi-file mode), route diffs by file
    if (editorMap) {
      for (var i = 0; i < diffs.length; i++) {
        var diff = diffs[i];
        if (!diff.before || !diff.after) continue;

        // Find the right editor for this diff's file
        var targetEditor = null;
        if (diff.file && editorMap[diff.file]) {
          targetEditor = editorMap[diff.file];
        } else {
          // Try basename matching
          for (var key in editorMap) {
            if (diff.file && (diff.file.endsWith(key) || key.endsWith(diff.file))) {
              targetEditor = editorMap[key];
              break;
            }
          }
        }

        if (!targetEditor) {
          // Fallback: try the active editor
          targetEditor = editorManager.editor;
        }

        if (!targetEditor || !targetEditor.state || !targetEditor.state.doc) continue;

        var doc = targetEditor.state.doc;
        var fullText = doc.toString();
        var idx = fullText.indexOf(diff.before);
        if (idx !== -1) {
          targetEditor.dispatch({
            changes: { from: idx, to: idx + diff.before.length, insert: diff.after },
          });
        }
      }
      return;
    }

    // Legacy single-editor mode (no editorMap)
    var editor = editorManager.editor;
    if (!editor) return;
    var doc = editor.state.doc;
    var fullText = doc.toString();

    for (var j = 0; j < diffs.length; j++) {
      var d = diffs[j];
      if (d.before && d.after) {
        var pos = fullText.indexOf(d.before);
        if (pos !== -1) {
          editor.dispatch({
            changes: { from: pos, to: pos + d.before.length, insert: d.after },
          });
        }
      }
    }
  }

  // Phase 2.3: Show a diff preview before applying changes
  function showDiffPreview(diffs, onApply) {
    if (!diffs || diffs.length === 0) {
      onApply();
      return;
    }

    const overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    let html = '<div style="max-width:92%;max-height:85vh;width:550px;' +
      'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
      'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
      '<h3 style="margin:0 0 8px;font-size:15px;color:var(--text-primary,#c9d1d9);">' +
      'Diff Preview (' + diffs.length + ' change(s))</h3>';

    for (const diff of diffs) {
      if (!diff.before && !diff.after) continue;

      var fileLabel = '';
      if (diff.file) {
        fileLabel = '<span style="color:var(--accent-color,#2d7ff9);margin-left:8px;">' +
          escapeHtml(diff.file) + '</span>';
      }

      html += '<div style="margin-bottom:10px;border:1px solid #333;border-radius:4px;overflow:hidden;">';

      if (diff.before) {
        html += '<div style="background:#3d1f1f;padding:4px 8px;font-size:11px;color:#f88;display:flex;justify-content:space-between;">' +
          '<span>− Before</span>' + fileLabel + '</div>' +
          '<pre style="margin:0;padding:6px 8px;font-size:12px;background:#2d1515;' +
          'color:#faa;white-space:pre-wrap;word-wrap:break-word;max-height:120px;overflow-y:auto;">' +
          escapeHtml(diff.before) + '</pre>';
      }

      if (diff.after) {
        html += '<div style="background:#1f3d1f;padding:4px 8px;font-size:11px;color:#8f8;display:flex;justify-content:space-between;">' +
          '<span>+ After</span>' + fileLabel + '</div>' +
          '<pre style="margin:0;padding:6px 8px;font-size:12px;background:#152d15;' +
          'color:#afa;white-space:pre-wrap;word-wrap:break-word;max-height:120px;overflow-y:auto;">' +
          escapeHtml(diff.after) + '</pre>';
      }

      html += '</div>';
    }

    html += '<div style="margin-top:12px;display:flex;gap:8px;">' +
      '<button id="oc-diff-apply" style="padding:6px 16px;border:none;' +
      'background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Apply Changes</button>' +
      '<button id="oc-diff-cancel" style="padding:6px 16px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Cancel</button></div></div>';

    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    document.getElementById('oc-diff-apply').onclick = () => {
      overlay.remove();
      onApply();
    };

    document.getElementById('oc-diff-cancel').onclick = () => {
      overlay.remove();
    };
  }

  // ─── Public API ────────────────────────────────

  window.__OpencodeCommands = {
    register: registerCommands,
    unregister: unregisterCommands,
  };
})();
