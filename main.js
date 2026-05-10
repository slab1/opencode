/**
 * ─────────────────────────────────────────────────────────
 *  OpenCode AI for Acode  v1.2.0
 *  Plugin ID: com.opencode.acode
 * ─────────────────────────────────────────────────────────
 *  Self-contained Acode plugin connecting to a running
 *  OpenCode server (opencode serve) for AI-powered coding.
 *
 *  Keyboard: Ctrl+Shift+A(Ask) F(Fix) E(Explain) G(Generate)
 *            M(Multi-file) H(History) S(Status) D(Debug)
 *  Floating: OC button (bottom-right) → submenu
 * ─────────────────────────────────────────────────────────
 */

(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════
  //  BUGFIX 1: Polyfill helpers for old Android WebViews
  // ═══════════════════════════════════════════════════════

  // AbortSignal.timeout() polyfill for Android WebView < Chrome 103
  if (typeof AbortSignal !== 'undefined' && !AbortSignal.timeout) {
    AbortSignal.timeout = function (ms) {
      var ctrl = new AbortController();
      setTimeout(function () { ctrl.abort(); }, ms);
      return ctrl.signal;
    };
  }

  // Object.assign polyfill for very old WebViews (ES5)
  var _assign = typeof Object.assign === 'function'
    ? Object.assign
    : function (target) {
        target = Object(target);
        for (var i = 1; i < arguments.length; i++) {
          var src = arguments[i];
          if (src != null) {
            for (var key in src) {
              if (Object.prototype.hasOwnProperty.call(src, key)) {
                target[key] = src[key];
              }
            }
          }
        }
        return target;
      };

  // ═══════════════════════════════════════════════════════
  //  SECTION 1: OpenCode API Client
  // ═══════════════════════════════════════════════════════

  function OpencodeClient(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this._sessionId = null;
  }

  OpencodeClient.prototype = {
    healthCheck: function () {
      var self = this;
      return fetchWithTimeout(self.baseUrl + '/session/status', 3000)
        .then(function (res) { return res.ok; })
        .catch(function () { return false; });
    },

    listAgents: function () {
      return this._fetch('/agent')
        .then(function (res) {
          if (!res.ok) throw new Error('Failed to list agents: ' + res.status);
          return res.json();
        });
    },

    createSession: function (agent) {
      var self = this;
      return self._fetch('/session', {
        method: 'POST',
        body: JSON.stringify({ agent: agent || 'build' }),
      }).then(function (res) {
        if (!res.ok) {
          return res.text().then(function (errText) {
            throw new Error('Failed to create session: ' + res.status + ' - ' + errText);
          });
        }
        return res.json();
      }).then(function (data) {
        self._sessionId = data.id;
        return data.id;
      });
    },

    // Phase 2.1: Polling-based prompt (more robust for long-running prompts)
    prompt: function (text, options) {
      var self = this;
      var opts = options || {};
      var timeout = opts.timeout || 120000;
      var sessionId = self._sessionId;

      if (!sessionId) {
        return Promise.reject(new Error('No active session. Call createSession() first.'));
      }

      // Step 1: Send the user message
      return self._fetch('/session/' + sessionId + '/message', {
        method: 'POST',
        body: JSON.stringify({
          role: 'user',
          parts: [{ type: 'text', text: text }],
        }),
      }).then(function (msgRes) {
        if (!msgRes.ok) {
          return msgRes.text().then(function (errText) {
            throw new Error('Failed to send prompt: ' + msgRes.status + ' - ' + errText);
          });
        }
        // Step 2: Poll for the assistant response
        return self._pollForResponse(sessionId, timeout);
      });
    },

    // Phase 2.1: Poll until an assistant message appears
    _pollForResponse: function (sessionId, timeout) {
      var self = this;
      var startTime = Date.now();
      var lastCount = 0;
      var pollInterval = 800;

      function poll() {
        var elapsed = Date.now() - startTime;
        if (elapsed >= timeout) {
          return Promise.reject(new Error('Timed out waiting for AI response'));
        }

        return self._fetch('/session/' + sessionId + '/message')
          .then(function (listRes) {
            if (!listRes.ok) {
              return sleep(pollInterval).then(poll);
            }
            return listRes.json();
          })
          .then(function (messages) {
            var assistantMsgs = [];
            if (messages && messages.length) {
              for (var i = 0; i < messages.length; i++) {
                if (messages[i].role === 'assistant') {
                  assistantMsgs.push(messages[i]);
                }
              }
            }

            if (assistantMsgs.length > lastCount) {
              // New assistant message found — fetch its detail
              var latest = assistantMsgs[assistantMsgs.length - 1];
              return self._fetch('/session/' + sessionId + '/message/' + latest.id)
                .then(function (fullRes) {
                  if (!fullRes.ok) {
                    return sleep(pollInterval).then(poll);
                  }
                  return fullRes.json();
                })
                .then(function (detail) {
                  var textContent = '';
                  var diffs = [];

                  if (detail && detail.parts) {
                    for (var i = 0; i < detail.parts.length; i++) {
                      if (detail.parts[i].type === 'text') {
                        textContent += detail.parts[i].text;
                      }
                    }
                  }

                  if (detail.summary && detail.summary.diffs) {
                    diffs = detail.summary.diffs;
                  }

                  return {
                    content: textContent,
                    diffs: diffs,
                    messageId: detail.id || (detail.info && detail.info.id),
                  };
                });
            }

            lastCount = assistantMsgs.length;
            return sleep(pollInterval).then(poll);
          })
          .catch(function () {
            // Network error during poll — retry
            return sleep(pollInterval).then(poll);
          });
      }

      return poll();
    },

    deleteSession: function () {
      if (!this._sessionId) return Promise.resolve();
      var self = this;
      return self._fetch('/session/' + self._sessionId, { method: 'DELETE' })
        .then(function () { self._sessionId = null; });
    },

    // BUGFIX 4: No spread operator, uses _assign helper
    _fetch: function (path, options) {
      var url = this.baseUrl + path;
      var init = _assign({}, options, {
        headers: _assign(
          { 'Content-Type': 'application/json', Accept: 'application/json' },
          (options && options.headers) || {}
        ),
      });
      // Need to carefully merge: options may have method, body, signal
      // _assign(target, ...) - first {} then options then headers override
      // But _assign already set headers in the third arg, which would clobber
      // any headers from options. We need to pass method, body, signal etc.
      // Let's redo properly:
      // Actually _assign({}, options, { headers: ... }) copies options' keys
      // then overwrites headers. That's correct.
      return fetch(url, init);
    },
  };

  // Helper: fetch with timeout (works on old Android WebViews)
  function fetchWithTimeout(url, ms) {
    var controller = new AbortController();
    var timer = setTimeout(function () { controller.abort(); }, ms);
    return fetch(url, { signal: controller.signal }).then(function (res) {
      clearTimeout(timer);
      return res;
    }).catch(function (err) {
      clearTimeout(timer);
      throw err;
    });
  }

  // Helper: promise-based sleep
  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 2: UI Helpers
  // ═══════════════════════════════════════════════════════

  function escapeHtml(str) {
    if (!str) return '';
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 3: Floating Action Buttons
  // ═══════════════════════════════════════════════════════

  function createActionBar(handlers) {
    var bar = document.createElement('div');
    bar.id = 'oc-action-bar';
    bar.style.cssText =
      'position:fixed;bottom:72px;right:12px;z-index:9998;display:flex;flex-direction:column;gap:6px;';

    // BUGFIX 5: Use text-only label, no emoji in special chars
    var isExpanded = false;
    var mainBtn = document.createElement('button');
    mainBtn.textContent = 'OC'; // Emoji-free for compatibility
    mainBtn.title = 'OpenCode Commands';
    mainBtn.style.cssText =
      'width:44px;height:44px;border-radius:50%;border:none;background:var(--accent-color,#2d7ff9);color:#fff;font-size:16px;font-weight:bold;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,0.3);';

    var actions = handlers || {};

    var btnConfig = [
      { id: 'ask', label: 'Ask [^+A]', key: 'A' },
      { id: 'fix', label: 'Fix [^+F]', key: 'F' },
      { id: 'explain', label: 'Explain [^+E]', key: 'E' },
      { id: 'generate', label: 'Generate [^+G]', key: 'G' },
      { id: 'multi', label: 'Multi [^+M]', key: 'M' },
      { id: 'history', label: 'History [^+H]', key: 'H' },
      { id: 'status', label: 'Status [^+S]', key: 'S' },
      { id: 'debug', label: 'Debug [^+D]', key: 'D' },
    ];

    var _subButtons = [];

    btnConfig.forEach(function (cfg) {
      var btn = document.createElement('button');
      btn.textContent = cfg.label;
      btn.title = 'Ctrl+Shift+' + cfg.key;
      btn.style.cssText =
        'padding:6px 12px;border-radius:4px;border:1px solid var(--accent-color,#2d7ff9);background:var(--bg-primary,#0d1117);color:var(--accent-color,#2d7ff9);font-size:12px;cursor:pointer;display:none;white-space:nowrap;';
      btn.onmouseenter = function () {
        btn.style.background = 'var(--accent-color,#2d7ff9)';
        btn.style.color = '#fff';
      };
      btn.onmouseleave = function () {
        btn.style.background = 'var(--bg-primary,#0d1117)';
        btn.style.color = 'var(--accent-color,#2d7ff9)';
      };
      btn.onclick = function () {
        if (actions[cfg.id]) actions[cfg.id]();
        collapse();
      };
      _subButtons.push(btn);
      bar.appendChild(btn);
    });

    bar.appendChild(mainBtn);

    function expand() {
      isExpanded = true;
      mainBtn.textContent = 'X';
      mainBtn.style.background = '#e44';
      _subButtons.forEach(function (b) { b.style.display = 'block'; });
    }

    function collapse() {
      isExpanded = false;
      mainBtn.textContent = 'OC';
      mainBtn.style.background = 'var(--accent-color,#2d7ff9)';
      _subButtons.forEach(function (b) { b.style.display = 'none'; });
    }

    mainBtn.onclick = function () {
      if (isExpanded) collapse();
      else expand();
    };

    var _clickHandler = function (e) {
      if (isExpanded && !bar.contains(e.target)) collapse();
    };
    document.addEventListener('click', _clickHandler);

    return {
      element: bar,
      expand: expand,
      collapse: collapse,
      remove: function () {
        document.removeEventListener('click', _clickHandler);
        if (bar.parentNode) bar.parentNode.removeChild(bar);
      },
    };
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 4: Editor Helpers
  // ═══════════════════════════════════════════════════════

  function getEditorContext() {
    try {
      var editor = editorManager.editor;
      if (!editor) {
        return { text: '', selection: '', from: 0, to: 0, error: 'No active editor' };
      }

      // Try CM6 API first (Acode uses CodeMirror 6)
      if (typeof editor.state !== 'undefined' && editor.state && editor.state.doc) {
        var text = editor.state.doc.toString();
        var sel = '';
        var from = 0;
        var to = 0;
        var mainSel = editor.state.selection.main;
        if (mainSel && !mainSel.empty) {
          from = mainSel.from;
          to = mainSel.to;
          sel = text.slice(from, to);
        }
        return { text: text, selection: sel, from: from, to: to };
      }

      // Fall back to CM5 API
      if (typeof editor.getValue === 'function') {
        var text = editor.getValue();
        var sel = '';
        var from = 0;
        var to = 0;
        if (typeof editor.getSelection === 'function') {
          sel = editor.getSelection() || '';
        }
        if (typeof editor.getCursor === 'function') {
          var cursor = editor.getCursor();
          from = (cursor && cursor.ch) || 0;
        }
        return { text: text, selection: sel, from: from, to: from };
      }

      return { text: '', selection: '', from: 0, to: 0, error: 'No compatible editor API found' };
    } catch (e) {
      return { text: '', selection: '', from: 0, to: 0, error: e.message };
    }
  }

  function buildPrompt(mode, fullText, selection) {
    var context = selection
      ? 'SELECTED CODE:\n```\n' + selection + '\n```'
      : 'FILE CONTENT:\n```\n' + fullText + '\n```';

    var instructions = {
      ask:
        'You are a helpful coding assistant. Analyze the following code and respond to the request.\n\n' +
        context,
      fix:
        'Review the following code for bugs, errors, and improvements. Return ONLY the corrected code without explanations. Preserve the exact same structure and style.\n\n' +
        context,
      explain:
        'Explain the following code in simple terms. Describe what it does, key patterns used, and any potential issues.\n\n' +
        context,
    };

    return instructions[mode] || instructions.ask;
  }

  function applyDiff(editor, before, after) {
    try {
      // Get full text via whichever API is available
      var fullText = '';
      if (typeof editor.state !== 'undefined' && editor.state && editor.state.doc) {
        fullText = editor.state.doc.toString();
      } else if (typeof editor.getValue === 'function') {
        fullText = editor.getValue();
      } else {
        return false;
      }

      var idx = fullText.indexOf(before);
      if (idx === -1) return false;

      // CM6 path: use editor.dispatch()
      if (typeof editor.state !== 'undefined' && editor.state && editor.state.doc && typeof editor.dispatch === 'function') {
        editor.dispatch({
          changes: { from: idx, to: idx + before.length, insert: after },
        });
        return true;
      }

      // CM5 path with posFromIndex
      if (typeof editor.posFromIndex === 'function') {
        var startPos = editor.posFromIndex(idx);
        var endPos = editor.posFromIndex(idx + before.length);
        if (startPos && endPos) {
          editor.setSelection(startPos, endPos);
          editor.replaceSelection(after);
          return true;
        }
      }

      // Fallback: replace via full text
      if (typeof editor.setValue === 'function') {
        var newText = fullText.slice(0, idx) + after + fullText.slice(idx + before.length);
        editor.setValue(newText);
        return true;
      }

      return false;
    } catch (e) {
      return false;
    }
  }

  function showResult(content, promptText) {
    try {
      var page = document.getElementById('oc-result-overlay');
      if (!page) {
        page = document.createElement('div');
        page.id = 'oc-result-overlay';
        page.style.cssText =
          'position:fixed;top:0;left:0;right:0;bottom:0;z-index:9999;' +
          'background:rgba(0,0,0,0.6);display:none;align-items:center;justify-content:center;';
        document.body.appendChild(page);
      }
      var esc = escapeHtml(content);
      var escP = escapeHtml((promptText || '').slice(0, 120));
      page.innerHTML =
        '<div style="max-width:90%;max-height:80vh;width:500px;' +
        'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
        'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
        '<div style="margin-bottom:8px;font-size:11px;color:var(--text-secondary,#888);">' +
        'Prompt: ' + escP + '</div>' +
        '<div style="font-size:13px;line-height:1.6;white-space:pre-wrap;' +
        'word-wrap:break-word;color:var(--text-primary,#c9d1d9);font-family:monospace;">' +
        esc + '</div>' +
        '<div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">' +
        '<button id="oc-close-btn" style="padding:6px 16px;border:1px solid ' +
        'var(--accent-color,#2d7ff9);background:transparent;color:var(--accent-color,#2d7ff9);' +
        'border-radius:4px;cursor:pointer;font-size:12px;">Close</button>' +
        '</div></div>';
      page.style.display = 'flex';
      var closeBtn = document.getElementById('oc-close-btn');
      if (closeBtn) {
        closeBtn.onclick = function () { page.style.display = 'none'; };
      }
    } catch (e) {
      // Last resort
      alert(content);
    }
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 5: Toast (multi-method, robust)
  // ═══════════════════════════════════════════════════════

  function showToast(msg, duration) {
    var dur = duration || 4000;
    // Method 1: DOM toast (non-blocking, preferred for "thinking" messages)
    try {
      var div = document.createElement('div');
      div.textContent = msg;
      div.style.cssText =
        'position:fixed;bottom:130px;left:10px;right:10px;z-index:99999;' +
        'padding:12px;background:#333;color:#fff;border-radius:6px;' +
        'font-size:13px;text-align:center;pointer-events:none;';
      document.body.appendChild(div);
      setTimeout(function () { if (div.parentNode) div.remove(); }, dur);
      return;
    } catch (e) {}
    // Method 2: acode.alert (blocking, only for short messages)
    try {
      if (typeof acode.alert === 'function' && dur <= 4000) { acode.alert('OpenCode', msg); return; }
    } catch (e) {}
    // Method 3: acode.toast
    try {
      if (typeof acode.toast === 'function') { acode.toast(msg, dur); return; }
    } catch (e) {}
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 5b: History & Multi-file Helpers
  // ═══════════════════════════════════════════════════════

  var HISTORY_KEY = 'opencode:history';
  var MAX_HISTORY = 50;

  function saveToHistory(entry) {
    var history = getHistory();
    entry.id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    entry.timestamp = Date.now();
    history.unshift(entry);
    if (history.length > MAX_HISTORY) {
      history = history.slice(0, MAX_HISTORY);
    }
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch (e) {
      if (e.name === 'QuotaExceededError') {
        history = history.slice(0, 20);
        try { localStorage.setItem(HISTORY_KEY, JSON.stringify(history)); } catch (_) {}
      }
      console.error('[OpenCode] Failed to save history:', e);
    }
  }

  function getHistory() {
    try {
      var data = localStorage.getItem(HISTORY_KEY);
      return data ? JSON.parse(data) : [];
    } catch (e) {
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

  /**
   * Get all open editors from Acode's editor manager.
   */
  function getAllOpenEditors() {
    var result = [];
    try {
      var editors = [];
      if (editorManager && typeof editorManager.editors !== 'undefined') {
        editors = editorManager.editors;
      }
      if (!Array.isArray(editors)) {
        var vals = Object.values(editors);
        if (Array.isArray(vals)) editors = vals;
      }
      if (editors.length === 0 && editorManager && editorManager.editor) {
        editors = [editorManager.editor];
      }
      for (var i = 0; i < editors.length; i++) {
        var ed = editors[i];
        if (!ed || !ed.state || !ed.state.doc) continue;
        try {
          var filename = (ed.getOption && ed.getOption('filename')) || 'untitled-' + (i + 1);
          var content = ed.state.doc.toString();
          if (content) {
            result.push({ editor: ed, filename: filename, content: content });
          }
        } catch (e) {
          console.warn('[OpenCode] Skipping editor ' + i + ': ' + (e.message || e));
        }
      }
    } catch (e) {
      console.error('[OpenCode] Failed to list editors:', e);
    }
    return result;
  }

  /**
   * Show a file picker overlay for multi-file selection.
   */
  function showFilePicker(editors, onSelect) {
    var overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    var listHtml = '';
    for (var i = 0; i < editors.length; i++) {
      var f = editors[i].filename;
      var size = editors[i].content.length;
      var sizeLabel = size > 1024 ? (size / 1024).toFixed(1) + 'KB' : size + 'B';
      var checked = i < 10 ? 'checked' : '';
      listHtml +=
        '<label style="display:flex;align-items:center;gap:8px;padding:6px 4px;' +
        'border-bottom:1px solid #333;cursor:pointer;font-size:12px;">' +
        '<input type="checkbox" id="oc-file-' + i + '" ' + checked +
        ' style="width:16px;height:16px;accent-color:#2d7ff9;">' +
        '<span style="flex:1;color:var(--text-primary,#c9d1d9);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' +
        escapeHtml(f) + '</span>' +
        '<span style="color:var(--text-secondary,#888);font-size:11px;">' + sizeLabel + '</span></label>';
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
      'Ask with files</button>' +
      '<button id="oc-pick-cancel" style="padding:6px 16px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Cancel</button></div></div>';

    document.body.appendChild(overlay);

    function updatePickLabel() {
      var count = overlay.querySelectorAll('input[type=checkbox]:checked').length;
      document.getElementById('oc-pick-ask').textContent = 'Ask with ' + count + ' file(s)';
    }
    var cbs = overlay.querySelectorAll('input[type=checkbox]');
    for (var j = 0; j < cbs.length; j++) {
      cbs[j].onchange = updatePickLabel;
    }

    document.getElementById('oc-pick-ask').onclick = function () {
      var selected = [];
      var checked = overlay.querySelectorAll('input[type=checkbox]:checked');
      for (var k = 0; k < checked.length; k++) {
        var idx = parseInt(checked[k].id.replace('oc-file-', ''), 10);
        if (editors[idx]) selected.push(editors[idx]);
      }
      overlay.remove();
      if (selected.length > 0) onSelect(selected);
    };

    document.getElementById('oc-pick-cancel').onclick = function () {
      overlay.remove();
    };
  }

  function buildMultiFilePrompt(selectedFiles, question) {
    var context = 'You are analyzing multiple open files. ' +
      'Here are the files I have open:\n\n';
    var totalSize = 0;

    for (var i = 0; i < selectedFiles.length; i++) {
      var f = selectedFiles[i];
      var content = f.content;
      var ext = f.filename.split('.').pop();

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

  // ── History UI ──────────────────────────────────

  function showHistoryList(history, onSelect) {
    var overlay = document.createElement('div');
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
        'transition:background 0.15s;border-radius:4px;">' +
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

  function showHistoryDetail(entry, onReAsk) {
    var overlay = document.createElement('div');
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

    var date = new Date(entry.timestamp);
    var timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    var promptHtml = escapeHtml(entry.prompt || '(no prompt)');
    var responseHtml = escapeHtml(entry.response || '(no response)');

    var html =
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

    if (entry.diffs && entry.diffs.length > 0) {
      html += '<div style="margin-top:8px;font-size:11px;color:var(--text-secondary,#888);">' +
        entry.diffs.length + ' change(s) were applied.</div>';
    }

    if (entry.files && entry.files.length > 0) {
      html += '<div style="margin-top:4px;font-size:11px;color:var(--text-secondary,#888);">' +
        'Files: ' + entry.files.join(', ') + '</div>';
    }

    html +=
      '<div style="margin-top:12px;display:flex;gap:8px;justify-content:flex-end;">' +
      '<button id="oc-hist-ask" style="padding:6px 16px;border:none;' +
      'background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">' +
      'Re-ask</button>' +
      '<button id="oc-hist-close" style="padding:6px 16px;border:1px solid #666;' +
      'background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">Close</button></div></div>';

    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    document.getElementById('oc-hist-ask').onclick = function () {
      overlay.remove();
      onReAsk();
    };

    document.getElementById('oc-hist-close').onclick = function () {
      overlay.remove();
    };
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 6: Plugin Lifecycle
  // ═══════════════════════════════════════════════════════

  var PLUGIN_ID = 'com.opencode.acode';
  var DEFAULT_PORT = 9878; // CORS proxy port (server.sh runs proxy on +2 from server)
  var SERVER_PORT = 9876;  // Direct OpenCode server port (if not using proxy)
  var _inited = false;

  // Store references for cleanup
  var _cleanup = {
    actionBar: null,
    keydownHandler: null,
    keydownTarget: null,
    pageInstance: null,
  };

  // Phase 2.2: Live client reference for settings changes
  var _activeClient = null;

  function startPlugin(config) {
    // Guard: prevent double-run
    if (_inited) return;

    // Don't run if no editor available yet - handlers check dynamically
    // NOTE: _inited is set to true at the END (not here) so that if
    // something throws, a retry can fully initialize. (The init callback
    // is wrapped in try/catch and calls destroyPlugin + self-init on error.)
    var serverUrl = 'http://127.0.0.1:' + (config.port || DEFAULT_PORT);
    var client = new OpencodeClient(serverUrl);
    _activeClient = client; // Phase 2.2: track for live settings

    // ── Handlers ─────────────────────────────────
    function handleAsk() {
      var ctx = getEditorContext();
      if (!ctx.text) { showToast('No file content available'); return; }
      var prompt = buildPrompt('ask', ctx.text, ctx.selection);
      executePrompt(client, prompt, false);
    }

    function handleFix() {
      var ctx = getEditorContext();
      if (!ctx.text) { showToast('No file content available'); return; }
      var prompt = buildPrompt('fix', ctx.text, ctx.selection);
      executePrompt(client, prompt, true);
    }

    function handleExplain() {
      var ctx = getEditorContext();
      if (!ctx.text) { showToast('No file content available'); return; }
      if (!ctx.selection) { showToast('Select some code first'); return; }
      var prompt = buildPrompt('explain', ctx.text, ctx.selection);
      executePrompt(client, prompt, false);
    }

    function handleStatus() {
      client.healthCheck().then(function (ok) {
        if (ok) {
          client.listAgents().then(function (agents) {
            var list = (agents || []).map(function (a) { return a.id || a.name; }).join(', ');
            showToast('Server is running\nAgents: ' + (list || 'unknown'));
          }).catch(function () {
            showToast('Server is running');
          });
        } else {
          showToast('Cannot reach server (port ' + config.port + ').\nTry port 9876 (direct) or run `opencode serve --port 9876`.');
        }
      });
    }

    function handleDebug() {
      var lines = [];
      try { lines.push('acode keys: ' + Object.keys(acode).join(', ')); } catch (e) { lines.push('acode: ERROR'); }
      try { lines.push('editorManager keys: ' + Object.keys(editorManager).join(', ')); } catch (e) { lines.push('editorManager: ERROR'); }
      try { lines.push('editor exists: ' + (editorManager.editor != null)); } catch (e) { lines.push('editor: ERROR'); }
      try { lines.push('editor.getValue: ' + (typeof (editorManager.editor && editorManager.editor.getValue))); } catch (e) { lines.push('editor.getValue: ERROR'); }
      try { lines.push('editor.getSelection: ' + (typeof (editorManager.editor && editorManager.editor.getSelection))); } catch (e) { lines.push('editor.getSelection: ERROR'); }
      try { lines.push('editor.posFromIndex: ' + (typeof (editorManager.editor && editorManager.editor.posFromIndex))); } catch (e) { lines.push('editor.posFromIndex: ERROR'); }
      try { lines.push('fetch: ' + (typeof fetch)); } catch (e) { lines.push('fetch: ERROR'); }
      try { lines.push('AbortSignal: ' + (typeof AbortSignal)); } catch (e) { lines.push('AbortSignal: ERROR'); }
      try { lines.push('userAgent: ' + navigator.userAgent); } catch (e) { lines.push('userAgent: ERROR'); }
      try { lines.push(''); } catch(e) {}
      try { lines.push('=== Plugin Status ==='); } catch(e) {}
      try { lines.push('Active: ' + (window.__OC_PLUGIN_ACTIVE ? 'Yes' : 'No')); } catch(e) {}
      try { lines.push('Self-init: ' + (_selfInited ? 'Yes' : 'No')); } catch(e) {}
      try {
        lines.push('');
        lines.push('=== All acode methods ===');
        var allKeys = Object.keys(acode);
        allKeys.sort();
        allKeys.forEach(function(k) { lines.push('  ' + k + ': ' + typeof acode[k]); });
      } catch(e) { lines.push('acode enum: ERROR'); }
      showResult(lines.join('\n'), 'Debug Info');
    }

    // Phase 2.4: Generate code from description
    function handleGenerate() {
      // Use native prompt for user input (works everywhere)
      var description = '';
      try {
        if (typeof acode.alert === 'function') {
          // Use a simple approach: prompt via window.prompt
          description = window.prompt('Describe the code to generate:');
        } else {
          description = window.prompt('Describe the code to generate:');
        }
      } catch (e) {
        description = window.prompt('Describe the code to generate:');
      }

      if (!description || !description.trim()) {
        showToast('Generation cancelled');
        return;
      }

      var ctx = getEditorContext();
      var lang = 'code';
      // Try to detect language from file extension
      try {
        if (editorManager && editorManager.editor) {
          var ed = editorManager.editor;
          var filename = '';
          if (typeof ed.getOption === 'function') {
            filename = ed.getOption('filename') || '';
          }
          if (filename) {
            var ext = filename.split('.').pop();
            if (ext) lang = ext;
          }
        }
      } catch (e) {}

      var prompt =
        'Generate ' + lang + ' code for the following request. ' +
        'Return ONLY the code without explanations, wrapped in a code block.\n\n' +
        description;

      // Generate into a new file: create content, then show in result
      executePrompt(client, prompt, false);

      // Show a toast indicating this is generation mode
      showToast('Generating ' + lang + ' code...');
    }

    // ── Multi-file Ask ──────────────────────────
    function handleMultiFileAsk() {
      var editors = getAllOpenEditors();
      if (editors.length === 0) {
        showToast('No open files available');
        return;
      }
      if (editors.length === 1) {
        var ctx = getEditorContext();
        if (!ctx.text) { showToast('No file content available'); return; }
        var prompt = buildPrompt('ask', ctx.text, ctx.selection);
        executePrompt(client, prompt, false, editors);
        return;
      }

      showFilePicker(editors, function (selected) {
        var question = window.prompt('Ask about the selected files:');
        if (!question || !question.trim()) {
          showToast('Multi-file ask cancelled');
          return;
        }
        var prompt = buildMultiFilePrompt(selected, question);
        showToast('Asking with ' + selected.length + ' file(s)...');
        executePrompt(client, prompt, true, selected);
      });
    }

    // ── Chat History ───────────────────────────
    function handleHistoryFn() {
      var history = getHistory();
      if (history.length === 0) {
        showToast('No chat history yet');
        return;
      }
      showHistoryList(history, function (entry) {
        showHistoryDetail(entry, function () {
          showToast('Re-asking...');
          var files = [];
          if (entry.files && entry.files.length > 0) {
            var currentEditors = getAllOpenEditors();
            for (var i = 0; i < entry.files.length; i++) {
              var match = null;
              for (var j = 0; j < currentEditors.length; j++) {
                var fname = currentEditors[j].filename;
                if (fname === entry.files[i] ||
                    fname.endsWith('/' + entry.files[i]) ||
                    fname.endsWith('\\' + entry.files[i])) {
                  match = currentEditors[j];
                  break;
                }
              }
              files.push(match || { filename: entry.files[i], content: '', editor: null });
            }
          }
          executePrompt(client, entry.prompt, entry.diffs && entry.diffs.length > 0, files);
        });
      });
    }

    // Phase 2.3: Show a diff preview before applying changes
    function showDiffPreview(diffs, onApply) {
      if (!diffs || diffs.length === 0) {
        onApply();
        return;
      }

      var overlay = document.createElement('div');
      overlay.style.cssText =
        'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
        'background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';

      var html = '<div style="max-width:92%;max-height:85vh;width:550px;' +
        'background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;' +
        'overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
        '<h3 style="margin:0 0 8px;font-size:15px;color:var(--text-primary,#c9d1d9);">' +
        'Diff Preview (' + diffs.length + ' change(s))</h3>';

      for (var d = 0; d < diffs.length; d++) {
        var diff = diffs[d];
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

      document.getElementById('oc-diff-apply').onclick = function () {
        overlay.remove();
        onApply();
      };

      document.getElementById('oc-diff-cancel').onclick = function () {
        overlay.remove();
        showToast('Changes cancelled');
      };
    }

    // ── Execute prompt ───────────────────────────
    function executePrompt(client, promptText, applyEdits, files) {
      client.healthCheck().then(function (ok) {
        if (!ok) {
          // Restore OC button if it was changed
          try {
            var ocBtn0 = document.querySelector('#oc-action-bar > button:last-child');
            if (ocBtn0 && ocBtn0._origText) { ocBtn0.textContent = ocBtn0._origText; ocBtn0.style.background = ocBtn0._origBg; }
          } catch(e) {}
          showToast('Cannot reach server. Try port 9876 (direct) or run `opencode serve --port 9876` in your terminal');
          return;
        }

        // Show persistent thinking indicator on OC button
        try {
          var ocBtn = document.querySelector('#oc-action-bar > button:last-child');
          if (ocBtn) {
            ocBtn._origText = ocBtn.textContent;
            ocBtn._origBg = ocBtn.style.background;
            ocBtn.textContent = '...';
            ocBtn.style.background = '#e4a000';
          }
        } catch(e) {}

        var mode = (files && files.length > 1) ? 'multi' : 'single';

        client.createSession(config.agent).then(function () {
          return client.prompt(promptText, { timeout: 120000 });
        }).then(function (result) {
          // Restore OC button
          try {
            var ocBtn2 = document.querySelector('#oc-action-bar > button:last-child');
            if (ocBtn2 && ocBtn2._origText) { ocBtn2.textContent = ocBtn2._origText; ocBtn2.style.background = ocBtn2._origBg; }
          } catch(e) {}

          if (!result || !result.content) {
            showToast('OpenCode returned an empty response');
            return;
          }

          // ── Save to history BEFORE showing result ──
          var fileNames = [];
          if (files) {
            for (var fi = 0; fi < files.length; fi++) {
              if (files[fi].filename) fileNames.push(files[fi].filename);
            }
          }
          saveToHistory({
            prompt: promptText,
            response: result.content,
            diffs: result.diffs || [],
            agent: config.agent,
            mode: mode,
            files: fileNames,
          });

          showResult(result.content, promptText);

          // ── Build editor map for diff routing ──
          var editorMap = null;
          if (files && files.length > 0) {
            editorMap = {};
            for (var fi2 = 0; fi2 < files.length; fi2++) {
              var ff = files[fi2];
              if (ff.filename) {
                editorMap[ff.filename] = ff.editor;
                var base = ff.filename.split('/').pop().split('\\').pop();
                if (base && base !== ff.filename) {
                  editorMap[base] = ff.editor;
                }
              }
            }
          }

          // Phase 2.3: Show diff preview before applying
          if (applyEdits && result.diffs && result.diffs.length > 0) {
            showDiffPreview(result.diffs, function () {
              var applied = 0;
              if (editorMap) {
                // Multi-file: route diffs by file field
                for (var di = 0; di < result.diffs.length; di++) {
                  var diff = result.diffs[di];
                  if (!diff.before || !diff.after) continue;
                  var targetEd = null;
                  if (diff.file && editorMap[diff.file]) {
                    targetEd = editorMap[diff.file];
                  } else {
                    // Fuzzy match
                    for (var key in editorMap) {
                      if (diff.file && (diff.file.endsWith(key) || key.endsWith(diff.file))) {
                        targetEd = editorMap[key];
                        break;
                      }
                    }
                  }
                  if (!targetEd) targetEd = editorManager.editor;
                  if (targetEd && applyDiff(targetEd, diff.before, diff.after)) applied++;
                }
              } else {
                // Single-file: apply to active editor
                var editor = editorManager.editor;
                if (editor) {
                  for (var di2 = 0; di2 < result.diffs.length; di2++) {
                    var d2 = result.diffs[di2];
                    if (d2.before && d2.after && applyDiff(editor, d2.before, d2.after)) applied++;
                  }
                }
              }
              if (applied > 0) showToast('Applied ' + applied + ' change(s)');
            });
          }

          // Cleanup session after a delay
          setTimeout(function () { client.deleteSession().catch(function () {}); }, 5000);
        }).catch(function (err) {
          // Restore OC button
          try {
            var ocBtn3 = document.querySelector('#oc-action-bar > button:last-child');
            if (ocBtn3 && ocBtn3._origText) { ocBtn3.textContent = ocBtn3._origText; ocBtn3.style.background = ocBtn3._origBg; }
          } catch(e) {}
          showToast('Error: ' + (err.message || err));
          client.deleteSession().catch(function () {});
        });
      });
    }

    // ── Keyboard shortcuts ───────────────────────
    function handleKeydown(e) {
      if (!e.ctrlKey && !e.metaKey) return;
      if (!e.shiftKey) return;
      var key = e.key.toUpperCase();
      var handled = true;

      if (key === 'A') { handleAsk(); }
      else if (key === 'F') { handleFix(); }
      else if (key === 'E') { handleExplain(); }
      else if (key === 'S') { handleStatus(); }
      else if (key === 'D') { handleDebug(); }
      else if (key === 'G') { handleGenerate(); }
      else if (key === 'M') { handleMultiFileAsk(); }
      else if (key === 'H') { handleHistoryFn(); }
      else { handled = false; }

      if (handled) {
        e.preventDefault();
        e.stopPropagation();
      }
    }

    // ── Register commands (try Acode API first, fall back to CodeMirror) ──
    var cmds = [
      { name: 'opencodeAsk', desc: 'OpenCode: Ask about code', key: 'A', handler: handleAsk },
      { name: 'opencodeFix', desc: 'OpenCode: Fix selected code', key: 'F', handler: handleFix },
      { name: 'opencodeExplain', desc: 'OpenCode: Explain selected code', key: 'E', handler: handleExplain },
      { name: 'opencodeGenerate', desc: 'OpenCode: Generate code', key: 'G', handler: handleGenerate },
      { name: 'opencodeMulti', desc: 'OpenCode: Multi-file ask', key: 'M', handler: handleMultiFileAsk },
      { name: 'opencodeHistory', desc: 'OpenCode: Chat history', key: 'H', handler: handleHistoryFn },
      { name: 'opencodeStatus', desc: 'OpenCode: Check server status', key: 'S', handler: handleStatus },
      { name: 'opencodeDebug', desc: 'OpenCode: Debug info', key: 'D', handler: handleDebug },
    ];

    var _cmdMethod = 'none';

    // Method 1: acode.require("commands") — Acode's official command API
    // (may only be available after proper acode.setPluginInit registration)
    try {
      var _acCmds = acode.require('commands');
      if (_acCmds && typeof _acCmds.addCommand === 'function') {
        cmds.forEach(function (c) {
          _acCmds.addCommand({
            name: c.name,
            description: c.desc,
            bindKey: { win: 'Ctrl-Shift-' + c.key, mac: 'Cmd-Shift-' + c.key },
            exec: function () { c.handler(); },
          });
        });
        _cmdMethod = 'acode.require("commands")';
      }
    } catch (e) {}

    // Method 2: acode.addCommand convenience method (on acode object directly)
    if (_cmdMethod === 'none') {
      try {
        if (typeof acode.addCommand === 'function') {
          cmds.forEach(function (c) {
            acode.addCommand({
              name: c.name,
              description: c.desc,
              bindKey: { win: 'Ctrl-Shift-' + c.key, mac: 'Cmd-Shift-' + c.key },
              exec: function () { c.handler(); },
            });
          });
          _cmdMethod = 'acode.addCommand';
        }
      } catch (e) {}
    }

    // Method 3: editor.commands.addCommand (CodeMirror internal API) — always works
    if (_cmdMethod === 'none') {
      try {
        var ed = editorManager.editor;
        if (ed && ed.commands && typeof ed.commands.addCommand === 'function') {
          // Register without bindKey — keyboard handled by our own keydown listener
          cmds.forEach(function (c) {
            ed.commands.addCommand({
              name: c.name,
              description: c.desc,
              exec: function () { c.handler(); },
            });
          });
          _cmdMethod = 'CodeMirror editor.commands';
        }
      } catch (e) {
        console.warn('[OpenCode] CodeMirror command registration failed:', e);
      }
    }

    if (_cmdMethod !== 'none') {
      console.log('[OpenCode] Registered commands via ' + _cmdMethod);
    } else {
      console.warn('[OpenCode] No command registration method available');
    }

    // Attach keydown to editor first, fallback to document
    try {
      if (editorManager && editorManager.editor &&
          typeof editorManager.editor.getWrapperElement === 'function') {
        _cleanup.keydownTarget = editorManager.editor.getWrapperElement();
      } else if (editorManager && editorManager.editor &&
                 typeof editorManager.editor.getInputField === 'function') {
        _cleanup.keydownTarget = editorManager.editor.getInputField();
      }
    } catch (e) {}

    if (!_cleanup.keydownTarget) {
      _cleanup.keydownTarget = document;
    }

    _cleanup.keydownHandler = handleKeydown;
    _cleanup.keydownTarget.addEventListener('keydown', handleKeydown);

    // ── Floating action bar ──────────────────────
    _cleanup.actionBar = createActionBar({
      ask: handleAsk,
      fix: handleFix,
      explain: handleExplain,
      generate: handleGenerate,
      multi: handleMultiFileAsk,
      history: handleHistoryFn,
      status: handleStatus,
      debug: handleDebug,
    });
    document.body.appendChild(_cleanup.actionBar.element);

    // Mark as inited only after ALL setup is complete
    _inited = true;
    console.log('[OpenCode] Plugin started. Port: ' + config.port + ', Agent: ' + config.agent);
  }

  function destroyPlugin() {
    // Guard: prevent double-destroy (can be called from both unmount and plugin lifecycle)
    if (!_inited && !_selfInited && !_cleanup.actionBar && !_cleanup.keydownHandler) {
      return;
    }

    // Remove commands — try Acode API first, then CodeMirror
    var _cmdNames = ['opencodeAsk', 'opencodeFix', 'opencodeExplain', 'opencodeGenerate', 'opencodeMulti', 'opencodeHistory', 'opencodeStatus', 'opencodeDebug'];

    // Method 1: acode.require("commands")
    try {
      var _acCmds = acode.require('commands');
      if (_acCmds && typeof _acCmds.removeCommand === 'function') {
        _cmdNames.forEach(function(name) {
          try { _acCmds.removeCommand(name); } catch(e) {}
        });
      }
    } catch(e) {}

    // Method 2: acode.removeCommand convenience method
    try {
      if (typeof acode.removeCommand === 'function') {
        _cmdNames.forEach(function(name) {
          try { acode.removeCommand(name); } catch(e) {}
        });
      }
    } catch(e) {}

    // Method 3: editor.commands.removeCommand (CodeMirror)
    try {
      var ed = editorManager.editor;
      if (ed && ed.commands && typeof ed.commands.removeCommand === 'function') {
        _cmdNames.forEach(function(name) {
          try { ed.commands.removeCommand(name); } catch(e) {}
        });
      }
    } catch(e) {}

    // Remove keydown listener
    if (_cleanup.keydownHandler && _cleanup.keydownTarget) {
      try {
        _cleanup.keydownTarget.removeEventListener('keydown', _cleanup.keydownHandler);
      } catch (e) {}
    }

    // Remove action bar
    if (_cleanup.actionBar) {
      try { _cleanup.actionBar.remove(); } catch (e) {}
    }

    // Remove result overlay
    var overlay = document.getElementById('oc-result-overlay');
    if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);

    // Remove welcome banner
    var welcome = document.getElementById('oc-welcome');
    if (welcome && welcome.parentNode) welcome.parentNode.removeChild(welcome);

    // Hide the Acode page if we stored a reference
    if (_cleanup.pageInstance) {
      try {
        if (typeof _cleanup.pageInstance.hide === 'function') {
          _cleanup.pageInstance.hide();
        }
        _cleanup.pageInstance.innerHTML = '';
      } catch (e) {}
      _cleanup.pageInstance = null;
    }

    _inited = false;
    _selfInited = false;
    window.__OC_PLUGIN_ACTIVE = false;
    _cleanup.keydownHandler = null;
    _cleanup.keydownTarget = null;
    _cleanup.actionBar = null;
    _cleanup.pageInstance = null;

    console.log('[OpenCode] Plugin destroyed.');
  }

  // ═══════════════════════════════════════════════════════
  //  SECTION 7: Plugin Registration (Acode API + Fallback)
  // ═══════════════════════════════════════════════════════

  // First, try the official Acode registration API.
  // Uses correct format per docs: `{list: [{key, text, ...}]}`
  // (NOT `{settings: [{key, label, ...}]}` which caused earlier failures)
  // Falls back to self-init if unavailable or throws.

  var _registeredViaApi = false;

  try {
    if (typeof acode.setPluginInit === 'function') {
      acode.setPluginInit(PLUGIN_ID, function (baseUrl, $page, cache) {
        // CRITICAL: Entire init wrapped in try/catch so NO error propagates
        // to Acode. If it does, Acode marks the plugin as "broken" and
        // won't load it again. (See docs: "Failure Behavior You Should Know")
        var initError = null;
        try {
          var config = { port: DEFAULT_PORT, agent: 'build' };
      try {
        if (cache && cache.ctx) {
          if (cache.ctx.port !== undefined && cache.ctx.port !== null && cache.ctx.port !== '') {
            config.port = Number(cache.ctx.port);
          }
          if (cache.ctx.agent !== undefined && cache.ctx.agent !== null && cache.ctx.agent !== '') {
            config.agent = String(cache.ctx.agent);
          }
        }
      } catch (e) {}

          // Store $page reference for cleanup on back navigation
          _cleanup.pageInstance = $page || null;

          // Set minimal page content so Acode renders the page properly
          try {
            if ($page) {
              $page.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--text-secondary,#888);">' +
                'OpenCode AI is active. OC button (bottom-right) or Ctrl+Shift+[A/F/E/G/M/H/S/D].' +
                '</div>';
              if (typeof $page.show === 'function') {
                $page.show();
              }
            }
          } catch (e) {}

          // Start plugin (commands, floating button, keydown listener)
          startPlugin(config);
        } catch (e) {
          initError = e;
          console.error('[OpenCode] Init error (caught, plugin NOT marked broken):', e);
          // Clean up partial initialization so self-init can retry cleanly
          destroyPlugin();
        }

        // If init failed, fall back to self-init which retries until editor is ready
        if (initError) {
          setTimeout(trySelfInit, 2000);
        }
      }, {
        // CORRECT format per https://docs.acode.app/docs/global-apis/acode
        // Uses `prompt` for editable fields, `value` for default, `info` for help text
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
              var newUrl = 'http://127.0.0.1:' + value;
              _activeClient = new OpencodeClient(newUrl);
              _activeClient.healthCheck().then(function (ok) {
                if (ok) {
                  showToast('Reconnected on port ' + value);
                } else {
                  showToast('Cannot reach server on port ' + value);
                }
              });
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
              showToast('Agent will change on next prompt');
            },
          },
        ],
      });

      if (typeof acode.setPluginUnmount === 'function') {
        acode.setPluginUnmount(PLUGIN_ID, destroyPlugin);
      }

      _registeredViaApi = true;
      console.log('[OpenCode] Registered via acode.setPluginInit');
    }
  } catch (e) {
    console.warn('[OpenCode] acode.setPluginInit failed:', e.message);
  }

  // ─── Self-init: function declaration (hoisted safely, not inside block) ──

  var _selfInited = false;
  var _selfInitRetries = 0;
  var _maxSelfInitRetries = 15;

  function trySelfInit() {
    if (_selfInited) return;
    _selfInitRetries++;

    try {
      // Wait for editor to be ready
      if (!editorManager || !editorManager.editor) {
        if (_selfInitRetries < _maxSelfInitRetries) {
          setTimeout(trySelfInit, 1000);
        }
        return;
      }

      var config = { port: DEFAULT_PORT, agent: 'build' };
      startPlugin(config);
      _selfInited = true;
      console.log('[OpenCode] Plugin started (self-init)');

      // Show welcome on first run using a DOM banner
      try {
        var firstRunKey = 'oc_first_run_' + PLUGIN_ID;
        if (!localStorage.getItem(firstRunKey)) {
          localStorage.setItem(firstRunKey, '1');
          setTimeout(function () {
            var banner = document.createElement('div');
            banner.id = 'oc-welcome';
            banner.style.cssText =
              'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
              'z-index:99999;background:var(--bg-primary,#0d1117);' +
              'border:1px solid var(--accent-color,#2d7ff9);border-radius:8px;' +
              'padding:20px;max-width:320px;box-shadow:0 4px 24px rgba(0,0,0,0.6);' +
              'font-family:sans-serif;font-size:13px;color:var(--text-primary,#c9d1d9);';
            banner.innerHTML =
              '<h2 style="margin:0 0 8px;font-size:16px;">OpenCode Active</h2>' +
              '<p style="margin:0 0 12px;color:var(--text-secondary,#888);line-height:1.5;">' +
              'Plugin is running. Tap the <strong>OC</strong> button (bottom-right) or use keyboard shortcuts (requires keyboard).</p>' +
              '<p style="margin:0 0 12px;font-size:11px;color:var(--text-secondary,#888);">' +
              'Shortcuts: [A]sk [F]ix [E]xplain [G]enerate [M]ulti [H]istory [S]tatus [D]ebug</p>' +
              '<button id="oc-welcome-ok" style="padding:6px 16px;border:none;' +
              'background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;' +
              'cursor:pointer;font-size:12px;">Got it</button>';
            document.body.appendChild(banner);
            document.getElementById('oc-welcome-ok').onclick = function () {
              banner.remove();
            };
          }, 2000);
        }
      } catch (e) {
        // localStorage might not be available
      }
    } catch (e) {
      console.error('[OpenCode] Self-init attempt ' + _selfInitRetries + ' failed:', e);
      if (_selfInitRetries < _maxSelfInitRetries) {
        setTimeout(trySelfInit, 1000);
      }
    }
  }

  // ─── Decide path: API vs self-init ──────────────────

  if (_registeredViaApi) {
    window.__OC_PLUGIN_ACTIVE = true;
    console.log('[OpenCode] Registered via API. Waiting for Acode to call init...');
  } else {
    window.__OC_PLUGIN_ACTIVE = true;
    // Start after a short delay to let the DOM settle
    setTimeout(trySelfInit, 800);
  }

  // Store destroy for manual cleanup
  window.__OC_DESTROY = destroyPlugin;

  console.log('[OpenCode] Script loaded.');
})();
