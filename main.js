/**
 * ─────────────────────────────────────────────────────────
 *  OpenCode AI for Acode  v3.3.0
 *  Plugin ID: com.opencode.acode
 * ─────────────────────────────────────────────────────────
 *  Full-featured Acode plugin: chat panel, inline chat,
 *  response capture, diff apply, agent selection, settings.
 *  Reliable terminal-based server startup for Android.
 *
 *  Keyboard:
 *    Ctrl+Shift+K(Chat) I(Inline) A(Ask) F(Fix)
 *            E(Explain) G(Generate) S(Status)
 *            O(Settings) D(Debug)
 * ─────────────────────────────────────────────────────────
 */
(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════
  //  Constants
  // ═══════════════════════════════════════════════════════

  var PLUGIN_ID = 'com.opencode.acode';
  var PROXY_PORT = 9878;
  var SERVER_PORT = 4096;
  var PROXY_URL = 'http://127.0.0.1:' + PROXY_PORT;
  var SERVER_URL = 'http://127.0.0.1:' + SERVER_PORT;
  var STORAGE_KEY = 'opencode-chat-history';
  var SETTINGS_KEY = 'opencode-settings';
  var HEALTH_ENDPOINTS = ['/api/session', '/api/health', '/health', '/'];

  var ALL_AGENTS = [
    'build', 'debug', 'plan', 'architect', 'orchestrator',
    'explore', 'general', 'docs', 'refactor', 'review',
    'security', 'test', 'video-creator', 'web-browser',
    'display-agent'
  ];

  // Known Node.js paths (Termux, Alpine, or PATH fallback)
  var _nodePaths = [
    '/usr/bin/node',
    '/usr/local/bin/node',
    '/data/data/com.termux/files/usr/bin/node',
    '/data/data/com.termux/files/usr/bin/nodejs',
    'node',
  ];
  var _nodeExe = _nodePaths[0];

  // ═══════════════════════════════════════════════════════
  //  State
  // ═══════════════════════════════════════════════════════

  var _activeUrl = PROXY_URL;
  var _sessionId = null;
  var _serverReady = false;
  var _agent = 'build';
  var _chatMsgs = [];
  var _pluginDir = '';
  var _chatOpen = false;
  var _chatSending = false;
  var _cmds = [];
  var _fabCloseHandler = null;

  // ═══════════════════════════════════════════════════════
  //  Polyfills
  // ═══════════════════════════════════════════════════════

  if (typeof AbortSignal !== 'undefined' && !AbortSignal.timeout) {
    AbortSignal.timeout = function (ms) {
      var ctrl = new AbortController();
      setTimeout(function () { ctrl.abort(); }, ms);
      return ctrl.signal;
    };
  }

  // ═══════════════════════════════════════════════════════
  //  Persistence (localStorage)
  // ═══════════════════════════════════════════════════════

  function loadSettings() {
    try {
      var raw = localStorage.getItem(SETTINGS_KEY);
      if (raw) {
        var s = JSON.parse(raw);
        if (s.agent) _agent = s.agent;
      }
    } catch (e) { /* ignore */ }
  }

  function saveSettings() {
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify({ agent: _agent }));
    } catch (e) { /* ignore */ }
  }

  function loadChatHistory() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        _chatMsgs = JSON.parse(raw);
      }
    } catch (e) { _chatMsgs = []; }
  }

  function saveChatHistory() {
    try {
      // Keep only last 100 messages
      if (_chatMsgs.length > 100) {
        _chatMsgs = _chatMsgs.slice(-100);
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(_chatMsgs));
    } catch (e) { /* ignore */ }
  }

  // ═══════════════════════════════════════════════════════
  //  Inline Proxy Scripts (embedded for self-containment)
  // ═══════════════════════════════════════════════════════

  var _proxyInlineNode = [
    'var h=require("http");',
    'h.createServer(function(q,r){',
      'if(q.method=="OPTIONS"){r.writeHead(204,{"Access-Control-Allow-Origin":"*"});return r.end()}',
      'var o={hostname:"127.0.0.1",port:' + SERVER_PORT + ',path:q.url,method:q.method,headers:q.headers||{}};',
      'var p=h.request(o,function(x){',
        'var hd={};',
        'Object.keys(x.headers).forEach(function(k){hd[k]=x.headers[k]});',
        'hd["Access-Control-Allow-Origin"]="*";',
        'r.writeHead(x.statusCode,hd);x.pipe(r)',
      '});',
      'p.on("error",function(e){r.writeHead(502);r.end("Proxy error: "+e.message)});',
      'q.pipe(p)',
    '}).listen(' + PROXY_PORT + ');',
    'console.log("OC proxy ready on ' + PROXY_PORT + '")',
  ].join('');

  var _proxyInlinePython = [
    'import http.server,urllib.request,sys',
    'class P(http.server.BaseHTTPRequestHandler):',
      'def do_OPTIONS(self):',
        'self.send_response(204)',
        'self.send_header("Access-Control-Allow-Origin","*")',
        'self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")',
        'self.send_header("Access-Control-Allow-Headers","Content-Type")',
        'self.end_headers()',
      'def do_GET(self):',
        'self._proxy()',
      'def do_POST(self):',
        'self._proxy()',
      'def _proxy(self):',
        'try:',
          'body=self.rfile.read(int(self.headers.get("Content-Length",0))) if self.command=="POST" else None',
          'req=urllib.request.Request("http://127.0.0.1:' + SERVER_PORT + '"+self.path,data=body,headers=dict(self.headers),method=self.command)',
          'with urllib.request.urlopen(req,timeout=30) as r:',
            'self.send_response(r.status)',
            'for k,v in r.headers.items(): self.send_header(k,v)',
            'self.send_header("Access-Control-Allow-Origin","*")',
            'self.end_headers()',
            'self.wfile.write(r.read())',
        'except Exception as e:',
          'self.send_response(502)',
          'self.send_header("Access-Control-Allow-Origin","*")',
          'self.end_headers()',
          'self.wfile.write(("Proxy error: "+str(e)).encode())',
    'http.server.HTTPServer(("127.0.0.1",' + PROXY_PORT + '),P).serve_forever()',
  ].join('\n');

  // ═══════════════════════════════════════════════════════
  //  Server Management
  // ═══════════════════════════════════════════════════════

  function tryServerCors(callback) {
    showToast('Checking server CORS support...');
    fetch(SERVER_URL + '/global/health', { signal: AbortSignal.timeout(3000), mode: 'no-cors' })
      .then(function () {
        fetch(SERVER_URL + '/global/health', { signal: AbortSignal.timeout(3000), mode: 'cors' })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d) {
              _activeUrl = SERVER_URL;
              _serverReady = true;
              showToast('Connected directly!');
              if (callback) callback(true);
              return;
            }
            if (callback) callback(false);
          })
          .catch(function () {
            if (callback) callback(false);
          });
      })
      .catch(function () {
        if (callback) callback(false);
      });
  }

  function getProxyScriptPath() {
    if (_pluginDir) {
      return _pluginDir + '/scripts/cors-proxy.js';
    }
    return null;
  }

  function startProxy(callback) {
    showToast('Starting CORS proxy...');
    try {
      var terminal = acode.require('terminal');
      var pathPrefix = 'export PATH=/data/data/com.termux/files/usr/bin:/data/data/com.termux/files/usr/local/bin:$PATH && ';
      var cmd = '';

      var proxyScript = getProxyScriptPath();
      if (proxyScript) {
        cmd = pathPrefix + '"' + _nodeExe + '" "' + proxyScript + '" --target-port ' + SERVER_PORT + ' --proxy-port ' + PROXY_PORT;
      } else {
        var escapedCode = _proxyInlineNode;
        cmd = pathPrefix + '"' + _nodeExe + '" -e "' + escapedCode.replace(/"/g, '\\"') + '"';
      }

      terminal.exec(cmd);

      var att = 0;
      var maxAtt = 30;
      function poll() {
        att++;
        fetch(PROXY_URL + '/global/health', { signal: AbortSignal.timeout(3000), mode: 'cors' })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d && d.healthy) { _activeUrl = PROXY_URL; showToast('Proxy ready!'); if (callback) callback(true); }
            else if (att < maxAtt) setTimeout(poll, 2000);
            else { showToast('Proxy start failed'); if (callback) callback(false); }
          })
          .catch(function () {
            if (att < maxAtt) setTimeout(poll, 2000);
            else { showToast('Proxy start failed'); if (callback) callback(false); }
          });
      }
      setTimeout(poll, 3000);
    } catch (e) {
      console.warn('[OC] startProxy:', e);
      if (callback) callback(false);
    }
  }

  // Resilient health check — tries multiple endpoints
  function healthCheck(cb) {
    fetch(PROXY_URL + '/global/health', { signal: AbortSignal.timeout(4000), mode: 'cors' })
      .then(function (r) {
        if (!r.ok) throw new Error('status ' + r.status);
        return r.json();
      })
      .then(function (d) {
        if (d && d.healthy === true) { _activeUrl = PROXY_URL; cb('proxy'); }
        else cb(false);
      })
      .catch(function () {
        fetch(SERVER_URL + '/global/health', { signal: AbortSignal.timeout(4000), mode: 'no-cors' })
          .then(function () { cb('server_up'); })
          .catch(function () { cb(false); });
      });
  }

  function startServer(callback) {
    showToast('Starting OpenCode server...');
    try {
      var terminal = acode.require('terminal');
      terminal.exec('opencode serve --port ' + SERVER_PORT + ' --cors "*" --hostname 0.0.0.0 --log-level ERROR');
    } catch (e) {
      console.warn('[OC] Terminal unavailable:', e);
    }

    var attempts = 0;
    function poll() {
      attempts++;
      fetch(SERVER_URL + '/global/health', { signal: AbortSignal.timeout(4000), mode: 'no-cors' })
        .then(function () {
          showToast('Server detected!');
          tryServerCors(function (corsOk) {
            if (corsOk) {
              if (callback) callback(true);
            } else {
              showToast('Starting CORS proxy...');
              startProxy(function (proxyOk) {
                if (proxyOk) {
                  _serverReady = true;
                  showToast('Ready!');
                  if (callback) callback(true);
                } else {
                  showToast('CORS proxy failed — manual setup needed');
                  if (callback) callback(false);
                }
              });
            }
          });
        })
        .catch(function () {
          if (attempts < 30) { setTimeout(poll, 3000); }
          else {
            showToast('Server start timed out');
            if (callback) callback(false);
          }
        });
    }
    setTimeout(poll, 5000);
  }

  function ensureServer(cb) {
    // Quick check: prefer proxy, fall through if stale
    if (_serverReady) {
      fetch(PROXY_URL + '/global/health', { signal: AbortSignal.timeout(2000), mode: 'cors' })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d && d.healthy === true) { cb(true); return; } _serverReady = false; doHealthCb(); })
        .catch(function () { _serverReady = false; doHealthCb(); });
      return;
    }
    function doHealthCb() { healthCheck(doEnsure); }
    function doEnsure(status) {
      if (status === 'proxy') {
        _serverReady = true;
        _activeUrl = PROXY_URL;
        cb(true);
      } else if (status === 'server_up') {
        _activeUrl = SERVER_URL;
        tryServerCors(function (corsOk) {
          if (corsOk) {
            _serverReady = true;
            cb(true);
          } else {
            startProxy(function (ok) {
              if (ok) { _serverReady = true; cb(true); }
              else {
                showToast('CORS proxy unavailable');
                cb(false);
              }
            });
          }
        });
      } else {
        startServer(cb);
      }
    }
  }

  // ═══════════════════════════════════════════════════════
  //  API Client
  // ═══════════════════════════════════════════════════════

  function api(method, path, body, cb) {
    var opts = {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(body && method === 'POST' ? 180000 : 10000),
    };
    if (body) opts.body = JSON.stringify(body);
    fetch(_activeUrl + path, opts)
      .then(function (r) { if (!r.ok) throw new Error(method + ' ' + path + ' ' + r.status); return r.json(); })
      .then(function (d) { if (cb) cb(null, d); })
      .catch(function (e) { if (cb) cb(e); });
  }

  function createSession(cb) {
    api('POST', '/session', {}, function (err, d) {
      if (err) { if (cb) cb(err); return; }
      _sessionId = d.id;
      if (cb) cb(null, d.id);
    });
  }

  function sendMsg(text, cb) {
    if (!_sessionId) { if (cb) cb(new Error('No session')); return; }
    var body = { parts: [{ type: 'text', text: text }] };
    if (_agent) body.agent = _agent;
    api('POST', '/session/' + _sessionId + '/message', body, function (err, d) {
      if (err) { if (cb) cb(err); return; }
      var result = parseResponse(d);
      if (result && result.content) { if (cb) cb(null, result); return; }
      pollResponse(cb);
    });
  }

  function pollResponse(cb) {
    if (!_sessionId) { if (cb) cb(new Error('No session')); return; }
    var start = Date.now();
    var lastCount = 0;
    function poll() {
      if (Date.now() - start > 180000) { if (cb) cb(new Error('Timeout')); return; }
      api('GET', '/session/' + _sessionId + '/message', null, function (err, d) {
        if (err) { setTimeout(poll, 1000); return; }
        var msgs = parseMessages(d);
        var assistantMsgs = [];
        for (var i = 0; i < msgs.length; i++) {
          if (msgs[i].info && msgs[i].info.role === 'assistant') assistantMsgs.push(msgs[i]);
        }
        if (assistantMsgs.length > lastCount) {
          var latest = assistantMsgs[assistantMsgs.length - 1];
          var content = extractText(latest);
          if (content) { if (cb) cb(null, { content: content, diffs: extractDiffs(latest) }); return; }
        }
        lastCount = assistantMsgs.length;
        setTimeout(poll, 1000);
      });
    }
    setTimeout(poll, 1500);
  }

  function deleteSession(cb) {
    if (!_sessionId) { if (cb) cb(); return; }
    var sid = _sessionId;
    _sessionId = null;
    api('DELETE', '/session/' + sid, null, function () { if (cb) cb(); });
  }

  function parseResponse(d) {
    if (!d) return null;
    if (d.info && d.info.role === 'assistant') return { content: extractText(d), diffs: extractDiffs(d) };
    var msgs = parseMessages(d);
    for (var i = 0; i < msgs.length; i++) {
      if (msgs[i].info && msgs[i].info.role === 'assistant') return { content: extractText(msgs[i]), diffs: extractDiffs(msgs[i]) };
    }
    return null;
  }

  function parseMessages(d) {
    if (!d) return [];
    if (Array.isArray(d)) return d;
    if (d.messages && Array.isArray(d.messages)) return d.messages;
    if (d.data && Array.isArray(d.data)) return d.data;
    if (d.role) return [d];
    if (d.info && d.info.role) return [d];
    return [];
  }

  function extractText(d) {
    if (!d) return '';
    if (d.parts && Array.isArray(d.parts)) {
      var t = '';
      for (var i = 0; i < d.parts.length; i++) {
        if (d.parts[i].type === 'text') t += d.parts[i].text;
      }
      return t;
    }
    if (d.content) return d.content;
    if (d.text) return d.text;
    if (d.info && d.info.text) return d.info.text;
    return '';
  }

  function extractDiffs(d) {
    try {
      if (d.summary && d.summary.diffs) return d.summary.diffs;
      if (d.info && d.info.summary && d.info.summary.diffs) return d.info.summary.diffs;
      if (d.diffs) return d.diffs;
    } catch (e) {}
    return [];
  }

  // ═══════════════════════════════════════════════════════
  //  Editor Helpers
  // ═══════════════════════════════════════════════════════

  function getEditorCtx() {
    try {
      var ed = editorManager.editor;
      if (!ed || !ed.state) return { text: '', sel: '' };
      var text = ed.state.doc.toString();
      var sel = '';
      var m = ed.state.selection.main;
      if (m && !m.empty) sel = text.slice(m.from, m.to);
      return { text: text, sel: sel };
    } catch (e) { return { text: '', sel: '' }; }
  }

  function applyDiff(before, after) {
    try {
      var ed = editorManager.editor;
      if (!ed || !before) return false;
      var full = ed.state ? ed.state.doc.toString() : '';
      var idx = full.indexOf(before);
      if (idx === -1) return false;
      if (ed.dispatch) {
        ed.dispatch({ changes: { from: idx, to: idx + before.length, insert: after } });
        return true;
      }
      return false;
    } catch (e) { return false; }
  }

  // ═══════════════════════════════════════════════════════
  //  Toast
  // ═══════════════════════════════════════════════════════

  function showToast(msg) {
    try {
      window.toast(msg, 5000);
    } catch (e) { console.warn('[OC] toast error:', e); }
  }

  // ═══════════════════════════════════════════════════════
  //  UI Helpers
  // ═══════════════════════════════════════════════════════

  function escapeHtml(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  function makeOverlay(id, zIndex) {
    var el = document.getElementById(id);
    if (!el) {
      el = document.createElement('div');
      el.id = id;
      el.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:' + (zIndex || 9999) + ';' +
        'background:rgba(0,0,0,0.6);display:none;align-items:center;justify-content:center;';
      document.body.appendChild(el);
    }
    return el;
  }

  function showOverlay(overlay) {
    overlay.style.display = 'flex';
  }

  function hideOverlay(overlay) {
    overlay.style.display = 'none';
  }

  // ═══════════════════════════════════════════════════════
  //  Response Display
  // ═══════════════════════════════════════════════════════

  function showResult(content, promptText) {
    try {
      var overlay = makeOverlay('oc-overlay');
      var esc = escapeHtml(content);
      var escP = escapeHtml((promptText || '').slice(0, 100));
      overlay.innerHTML =
        '<div style="max-width:92%;max-height:80vh;width:520px;background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;overflow-y:auto;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
        '<div style="margin-bottom:8px;font-size:11px;color:#888;">Prompt: ' + escP + '</div>' +
        '<div style="font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;color:var(--text-primary,#c9d1d9);font-family:monospace;">' + esc + '</div>' +
        '<div style="margin-top:12px;display:flex;gap:8px;">' +
        '<button id="oc-close" style="padding:6px 16px;border:1px solid var(--accent-color,#2d7ff9);background:transparent;color:var(--accent-color,#2d7ff9);border-radius:4px;cursor:pointer;font-size:12px;">Close</button>' +
        '</div></div>';
      showOverlay(overlay);
      document.getElementById('oc-close').onclick = function () { hideOverlay(overlay); };
    } catch (e) { (acode.require('alert'))('OC', content.slice(0, 2000)); }
  }

  // ═══════════════════════════════════════════════════════
  //  Diff UI
  // ═══════════════════════════════════════════════════════

  function showDiffs(diffs) {
    if (!diffs || diffs.length === 0) return;
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
    var html = '<div style="max-width:92%;max-height:85vh;width:520px;background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;overflow-y:auto;">' +
      '<h3 style="margin:0 0 8px;font-size:15px;color:var(--text-primary,#c9d1d9);">Changes (' + diffs.length + ')</h3>';
    for (var i = 0; i < diffs.length; i++) {
      var d = diffs[i];
      if (!d.before && !d.after) continue;
      html += '<div style="margin-bottom:8px;border:1px solid #333;border-radius:4px;overflow:hidden;">';
      if (d.before) html += '<div style="background:#3d1f1f;padding:4px 8px;font-size:11px;color:#f88;">− Before</div><pre style="margin:0;padding:6px 8px;font-size:12px;background:#2d1515;color:#faa;white-space:pre-wrap;">' + escapeHtml(d.before) + '</pre>';
      if (d.after) html += '<div style="background:#1f3d1f;padding:4px 8px;font-size:11px;color:#8f8;">+ After</div><pre style="margin:0;padding:6px 8px;font-size:12px;background:#152d15;color:#afa;white-space:pre-wrap;">' + escapeHtml(d.after) + '</pre>';
      html += '</div>';
    }
    html += '<div style="margin-top:12px;display:flex;gap:8px;">' +
      '<button id="oc-diff-apply" style="padding:6px 16px;border:none;background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">Apply All</button>' +
      '<button id="oc-diff-skip" style="padding:6px 16px;border:1px solid #666;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">Skip</button>' +
      '<button id="oc-diff-cancel" style="padding:6px 16px;border:1px solid #666;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">Cancel</button></div></div>';
    overlay.innerHTML = html;
    document.body.appendChild(overlay);
    document.getElementById('oc-diff-apply').onclick = function () {
      overlay.remove();
      var applied = 0;
      for (var i = 0; i < diffs.length; i++) {
        if (diffs[i].before && diffs[i].after && applyDiff(diffs[i].before, diffs[i].after)) applied++;
      }
      showToast('Applied ' + applied + ' change(s)');
    };
    document.getElementById('oc-diff-cancel').onclick = function () { overlay.remove(); };
    document.getElementById('oc-diff-skip').onclick = function () { overlay.remove(); };
  }

  // ═══════════════════════════════════════════════════════
  //  Prompt Execution
  // ═══════════════════════════════════════════════════════

  function execPrompt(prompt, apply) {
    showToast('Connecting to server...');
    ensureServer(function (ready) {
      if (!ready) {
        (acode.require('alert'))('OpenCode Setup',
          'Option A (auto, preferred):\n' +
          '  opencode serve --port ' + SERVER_PORT + ' --cors "*"\n\n' +
          'Option B (manual proxy):\n' +
          '  1. opencode serve --port ' + SERVER_PORT + '\n' +
          '  2. node ' + (_pluginDir || '/path/to/plugin') + '/scripts/cors-proxy.js \\\n' +
          '     --target-port ' + SERVER_PORT + ' --proxy-port ' + PROXY_PORT + '\n\n' +
          'Then try again.');
        return;
      }
      showToast('OpenCode is thinking...');
      createSession(function (err) {
        if (err) {
          showToast('Session error: ' + err.message);
          return;
        }
        sendMsg(prompt, function (err2, result) {
          if (err2 || !result) {
            showToast('Error: ' + (err2 ? err2.message : 'empty response'));
            deleteSession();
            return;
          }
          _chatMsgs.push({ role: 'user', text: prompt });
          _chatMsgs.push({ role: 'assistant', content: result.content, diffs: result.diffs || [] });
          saveChatHistory();
          showResult(result.content, prompt);
          if (apply && result.diffs && result.diffs.length > 0) {
            showDiffs(result.diffs);
          }
          setTimeout(function () { deleteSession(); }, 3000);
        });
      });
    });
  }

  // ═══════════════════════════════════════════════════════
  //  Action Handlers
  // ═══════════════════════════════════════════════════════

  function handleAsk() {
    var ctx = getEditorCtx();
    if (!ctx.sel) { (acode.require('alert'))('OC', 'Select some code first'); return; }
    execPrompt('Analyze this code and help me:\n```\n' + ctx.sel + '\n```', false);
  }

  function handleFix() {
    var ctx = getEditorCtx();
    if (!ctx.sel) { (acode.require('alert'))('OC', 'Select some code first'); return; }
    execPrompt('Fix bugs and improve this code:\n```\n' + ctx.sel + '\n```', true);
  }

  function handleExplain() {
    var ctx = getEditorCtx();
    if (!ctx.sel) { (acode.require('alert'))('OC', 'Select some code first'); return; }
    execPrompt('Explain this code:\n```\n' + ctx.sel + '\n```', false);
  }

  function handleGenerate() {
    (acode.require('prompt'))('Describe the code to generate:', '', { placeholder: 'e.g. a function to sort an array' }).then(function (desc) {
      if (!desc) return;
      execPrompt('Generate code: ' + desc, false);
    });
  }

  function handleStatus() {
    healthCheck(function (status) {
      if (status === 'proxy') {
        showToast('Proxy OK (via http://127.0.0.1:' + PROXY_PORT + ')');
      } else if (status === 'server_up') {
        fetch(SERVER_URL + '/global/health', { signal: AbortSignal.timeout(3000), mode: 'cors' })
          .then(function (r) { return r.json(); })
          .then(function () { showToast('Server OK with CORS'); })
          .catch(function () { showToast('Server OK but no CORS'); });
      } else {
        (acode.require('alert'))('OC',
          'Server not running.\n\nStart it in Termux:\n' +
          'opencode serve --port ' + SERVER_PORT + ' --cors "*"\n\n' +
          'The plugin will auto-start the CORS proxy.'
        );
      }
    });
  }

  function handleDebug() {
    var lines = [
      '=== OpenCode v3.3.0 ===',
      'Agent: ' + _agent,
      'Server: http://127.0.0.1:' + SERVER_PORT + ' (--cors "*")',
      'Proxy: http://127.0.0.1:' + PROXY_PORT,
      'Active: ' + _activeUrl,
      'Ready: ' + _serverReady,
      'Session: ' + (_sessionId || 'none'),
      'Node: ' + _nodeExe,
      'PluginDir: ' + (_pluginDir || '(not detected)'),
      'Chat history: ' + _chatMsgs.length + ' messages',
      '',
      'Available agents (' + ALL_AGENTS.length + '):',
      '  ' + ALL_AGENTS.join(', '),
      '',
      'Troubleshooting:',
      '1. opencode serve --port ' + SERVER_PORT + ' --cors "*" (in Termux)',
      '2. Plugin auto-starts proxy on port ' + PROXY_PORT,
      '3. Check: node -e "require(\'http\').createServer((q,r)=>{r.end(\'ok\')}).listen(' + PROXY_PORT + ')"',
      '',
      '=== Shortcuts ===',
      'K: Chat   I: Inline   A: Ask   F: Fix   E: Explain',
      'G: Generate   S: Status   O: Settings   D: Debug',
    ];
    showResult(lines.join('\n'), 'Debug');
  }

  // ═══════════════════════════════════════════════════════
  //  Chat Panel
  // ═══════════════════════════════════════════════════════

  function handleChat() {
    showChatPanel();
  }

  function handleInlineChat() {
    var ctx = getEditorCtx();
    (acode.require('prompt'))('Inline Chat:', '', { placeholder: 'e.g. refactor this function' }).then(function (q) {
      if (!q) return;
      var msg = q;
      if (ctx.sel) msg += '\n\nContext:\n```\n' + ctx.sel + '\n```';
      showToast('Sending inline query...');
      ensureServer(function (ready) {
        if (!ready) { showToast('Server not ready'); return; }
        createSession(function (err) {
          if (err) { showToast('Session error'); return; }
          sendMsg(msg, function (err2, result) {
            if (err2 || !result) { showToast('Error: ' + (err2 ? err2.message : 'empty')); deleteSession(); return; }
            showResult(result.content, q);
            if (result.diffs && result.diffs.length > 0) showDiffs(result.diffs);
            setTimeout(function () { deleteSession(); }, 3000);
          });
        });
      });
    });
  }

  function showChatPanel() {
    if (_chatOpen) { hideChatPanel(); return; }
    _chatOpen = true;

    var overlay = document.createElement('div');
    overlay.id = 'oc-chat';
    overlay.style.cssText =
      'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;' +
      'background:rgba(0,0,0,0.75);display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML =
      '<div id="oc-chat-box" style="display:flex;flex-direction:column;width:94%;max-width:560px;height:88vh;background:var(--bg-primary,#0d1117);border-radius:10px;overflow:hidden;box-shadow:0 6px 30px rgba(0,0,0,0.7);">' +
      '  <div style="display:flex;align-items:center;padding:10px 14px;border-bottom:1px solid #333;flex-shrink:0;">' +
      '    <span style="font-size:14px;font-weight:bold;color:var(--text-primary,#c9d1d9);flex:1;">OpenCode Chat' +
      '      <span id="oc-chat-agent" style="margin-left:8px;font-size:10px;color:#888;font-weight:normal;">(' + _agent + ')</span></span>' +
      '    <button id="oc-chat-new" style="padding:4px 10px;border:1px solid #555;background:transparent;color:#aaa;border-radius:4px;cursor:pointer;font-size:11px;margin-right:6px;">New</button>' +
      '    <button id="oc-chat-agent-btn" style="padding:4px 10px;border:1px solid #555;background:transparent;color:#aaa;border-radius:4px;cursor:pointer;font-size:11px;margin-right:6px;">Agent</button>' +
      '    <button id="oc-chat-close" style="padding:4px 10px;border:none;background:transparent;color:#aaa;cursor:pointer;font-size:16px;">X</button>' +
      '  </div>' +
      '  <div id="oc-chat-msgs" style="flex:1;overflow-y:auto;padding:10px 14px;"></div>' +
      '  <div id="oc-chat-input-bar" style="display:flex;padding:8px 10px;border-top:1px solid #333;flex-shrink:0;">' +
      '    <input id="oc-chat-input" type="text" placeholder="Type a message..." ' +
      '      style="flex:1;padding:8px 10px;border:1px solid #444;border-radius:6px;background:#161b22;color:var(--text-primary,#c9d1d9);font-size:13px;outline:none;">' +
      '    <button id="oc-chat-send" style="margin-left:6px;padding:8px 16px;border:none;background:#2d7ff9;color:#fff;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold;">Send</button>' +
      '  </div>' +
      '</div>';
    document.body.appendChild(overlay);

    renderChatMsgs();
    document.getElementById('oc-chat-input').focus();

    document.getElementById('oc-chat-close').onclick = hideChatPanel;
    document.getElementById('oc-chat-new').onclick = function () {
      _chatMsgs = [];
      _sessionId = null;
      saveChatHistory();
      renderChatMsgs();
      showToast('New chat started');
    };
    document.getElementById('oc-chat-agent-btn').onclick = function () {
      showQuickAgentSelect();
    };
    document.getElementById('oc-chat-send').onclick = chatSend;
    document.getElementById('oc-chat-input').onkeydown = function (e) {
      if (e.key === 'Enter') chatSend();
    };
    overlay.onclick = function (e) {
      if (e.target === overlay) hideChatPanel();
    };
  }

  function hideChatPanel() {
    _chatOpen = false;
    var overlay = document.getElementById('oc-chat');
    if (overlay) overlay.remove();
  }

  function renderChatMsgs() {
    var container = document.getElementById('oc-chat-msgs');
    if (!container) return;
    if (_chatMsgs.length === 0) {
      container.innerHTML = '<div style="text-align:center;padding:40px 16px;color:#555;font-size:13px;">Send a message to start chatting.<br>Selected code is automatically included as context.</div>';
      return;
    }
    var html = '';
    for (var i = 0; i < _chatMsgs.length; i++) {
      var m = _chatMsgs[i];
      var isUser = m.role === 'user';
      html +=
        '<div style="margin-bottom:10px;">' +
        '  <div style="font-size:10px;color:#888;margin-bottom:2px;">' + (isUser ? 'You' : 'OpenCode') + '</div>' +
        '  <div style="font-size:13px;line-height:1.5;white-space:pre-wrap;word-wrap:break-word;color:var(--text-primary,#c9d1d9);padding:8px 10px;border-radius:6px;background:' + (isUser ? '#1a2a4a' : '#161b22') + ';">' +
             escapeHtml(m.content || m.text || '') +
        '  </div>' +
        '</div>';
    }
    container.innerHTML = html;
    container.scrollTop = container.scrollHeight;
  }

  function chatSend() {
    if (_chatSending) return;
    var input = document.getElementById('oc-chat-input');
    if (!input) return;
    var text = input.value.trim();
    if (!text) return;

    var ctx = getEditorCtx();
    var fullMsg = text;
    if (ctx.sel) fullMsg += '\n\n```\n' + ctx.sel + '\n```';

    _chatMsgs.push({ role: 'user', text: text });
    input.value = '';
    renderChatMsgs();
    _chatSending = true;
    saveChatHistory();

    ensureServer(function (ready) {
      if (!ready) {
        _chatMsgs.push({ role: 'assistant', text: 'Server not running. Start it in Termux.' });
        renderChatMsgs();
        _chatSending = false;
        saveChatHistory();
        return;
      }
      function doSend() {
        sendMsg(fullMsg, function (err, result) {
          if (err || !result) {
            _chatMsgs.push({ role: 'assistant', text: err ? err.message : 'No response' });
            renderChatMsgs();
            _chatSending = false;
            saveChatHistory();
            if (err) { _sessionId = null; }
            return;
          }
          _chatMsgs.push({ role: 'assistant', text: result.content, diffs: result.diffs || [] });
          renderChatMsgs();
          _chatSending = false;
          saveChatHistory();
        });
      }
      if (_sessionId) { doSend(); }
      else {
        createSession(function (err) {
          if (err) {
            _chatMsgs.push({ role: 'assistant', text: 'Session error: ' + err.message });
            renderChatMsgs();
            _chatSending = false;
            saveChatHistory();
          } else { doSend(); }
        });
      }
    });
  }

  // ═══════════════════════════════════════════════════════
  //  Quick Agent Select (in-chat)
  // ═══════════════════════════════════════════════════════

  function showQuickAgentSelect() {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:999999;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;';
    var html = '<div style="max-width:280px;background:var(--bg-primary,#0d1117);border-radius:8px;padding:12px;box-shadow:0 4px 20px rgba(0,0,0,0.5);">' +
      '<div style="font-size:13px;color:var(--text-primary,#c9d1d9);margin-bottom:8px;font-weight:bold;">Change Agent</div>';
    for (var i = 0; i < ALL_AGENTS.length; i++) {
      var a = ALL_AGENTS[i];
      var sel = a === _agent ? ' style="background:#2d7ff9;color:#fff;"' : '';
      html += '<div class="oc-agent-opt"' + sel + ' data-agent="' + a + '" ' +
        'style="padding:6px 10px;margin:2px 0;border-radius:4px;cursor:pointer;font-size:12px;color:var(--text-primary,#c9d1d9);">' +
        a + '</div>';
    }
    html += '<div style="margin-top:8px;text-align:center;"><button id="oc-agent-close" ' +
      'style="padding:4px 12px;border:1px solid #666;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:11px;">Close</button></div></div>';
    overlay.innerHTML = html;
    document.body.appendChild(overlay);

    var opts = overlay.querySelectorAll('.oc-agent-opt');
    for (var j = 0; j < opts.length; j++) {
      opts[j].onclick = function () {
        _agent = this.getAttribute('data-agent');
        showToast('Agent: ' + _agent);
        saveSettings();
        var agentLabel = document.getElementById('oc-chat-agent');
        if (agentLabel) agentLabel.textContent = '(' + _agent + ')';
        overlay.remove();
      };
    }
    document.getElementById('oc-agent-close').onclick = function () { overlay.remove(); };
    overlay.onclick = function (e) { if (e.target === overlay) overlay.remove(); };
  }

  // ═══════════════════════════════════════════════════════
  //  Settings
  // ═══════════════════════════════════════════════════════

  function showSettings() {
    var overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99999;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;';
    var agentOpts = '';
    for (var i = 0; i < ALL_AGENTS.length; i++) {
      var a = ALL_AGENTS[i];
      var selected = a === _agent ? ' selected' : '';
      agentOpts += '<option value="' + a + '"' + selected + '>' + a + '</option>';
    }
    overlay.innerHTML =
      '<div style="max-width:90%;width:380px;background:var(--bg-primary,#0d1117);border-radius:8px;padding:16px;">' +
      '<h3 style="margin:0 0 12px;font-size:15px;color:var(--text-primary,#c9d1d9);">OpenCode Settings</h3>' +
      '<div style="margin-bottom:10px;">' +
      '<label style="display:block;margin-bottom:4px;color:#888;font-size:12px;">Default Agent</label>' +
      '<select id="oc-agent-sel" style="width:100%;padding:6px 8px;border:1px solid #444;border-radius:4px;background:var(--bg-secondary,#1a1a2e);color:var(--text-primary,#c9d1d9);font-size:13px;">' +
      agentOpts +
      '</select></div>' +
      '<div style="margin-bottom:10px;">' +
      '<label style="display:block;margin-bottom:4px;color:#888;font-size:12px;">Chat History</label>' +
      '<div style="font-size:12px;color:#aaa;">' + _chatMsgs.length + ' messages stored</div>' +
      '<button id="oc-clear-history" style="margin-top:4px;padding:4px 10px;border:1px solid #f55;background:transparent;color:#f55;border-radius:4px;cursor:pointer;font-size:11px;">Clear History</button>' +
      '</div>' +
      '<div style="display:flex;gap:8px;">' +
      '<button id="oc-save-settings" style="padding:6px 16px;border:none;background:var(--accent-color,#2d7ff9);color:#fff;border-radius:4px;cursor:pointer;font-size:12px;">Save</button>' +
      '<button id="oc-close-settings" style="padding:6px 16px;border:1px solid #666;background:transparent;color:#ccc;border-radius:4px;cursor:pointer;font-size:12px;">Close</button></div></div>';
    document.body.appendChild(overlay);

    document.getElementById('oc-save-settings').onclick = function () {
      _agent = document.getElementById('oc-agent-sel').value;
      saveSettings();
      overlay.remove();
      showToast('Agent: ' + _agent);
    };
    document.getElementById('oc-clear-history').onclick = function () {
      _chatMsgs = [];
      saveChatHistory();
      document.getElementById('oc-clear-history').textContent = 'History cleared';
      showToast('Chat history cleared');
    };
    document.getElementById('oc-close-settings').onclick = function () { overlay.remove(); };
  }

  // ═══════════════════════════════════════════════════════
  //  Floating Action Button
  // ═══════════════════════════════════════════════════════

  function createFAB() {
    try {
      var fab = document.createElement('div');
      fab.id = 'oc-fab';
      fab.textContent = 'OC';
      fab.style.cssText =
        'position:fixed;bottom:80px;right:16px;z-index:99998;' +
        'width:48px;height:48px;border-radius:24px;' +
        'background:#2d7ff9;color:#fff;' +
        'display:flex;align-items:center;justify-content:center;' +
        'font-size:13px;font-weight:bold;cursor:pointer;' +
        'box-shadow:0 2px 8px rgba(0,0,0,0.4);' +
        'user-select:none;-webkit-user-select:none;';
      fab.setAttribute('role', 'button');
      fab.setAttribute('aria-label', 'OpenCode AI');

      var menu = document.createElement('div');
      menu.id = 'oc-fab-menu';
      menu.style.cssText =
        'position:fixed;bottom:140px;right:16px;z-index:99999;' +
        'background:#0d1117;border:1px solid #333;border-radius:8px;' +
        'padding:6px 0;min-width:170px;' +
        'box-shadow:0 4px 16px rgba(0,0,0,0.5);display:none;';

      var items = [
        { label: 'Chat', fn: handleChat },
        { label: 'Inline Chat', fn: handleInlineChat },
        { label: 'Ask about code', fn: handleAsk },
        { label: 'Fix code', fn: handleFix },
        { label: 'Explain code', fn: handleExplain },
        { label: 'Generate code', fn: handleGenerate },
        { label: 'Server Status', fn: handleStatus },
        { label: 'Settings', fn: showSettings },
      ];

      items.forEach(function (item) {
        var btn = document.createElement('div');
        btn.textContent = item.label;
        btn.style.cssText =
          'padding:10px 16px;font-size:13px;' +
          'color:#c9d1d9;cursor:pointer;white-space:nowrap;';
        btn.onmouseover = function () { btn.style.background = 'rgba(255,255,255,0.08)'; };
        btn.onmouseout = function () { btn.style.background = 'transparent'; };
        btn.onclick = function () { menu.style.display = 'none'; item.fn(); };
        menu.appendChild(btn);
      });

      fab.onclick = function (e) {
        e.stopPropagation();
        menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
      };

      _fabCloseHandler = function (e) {
        if (menu.style.display !== 'none' && !menu.contains(e.target) && e.target !== fab) {
          menu.style.display = 'none';
        }
      };
      document.addEventListener('click', _fabCloseHandler);

      document.body.appendChild(fab);
      document.body.appendChild(menu);
    } catch (e) { console.error('[OC] FAB error:', e); }
  }

  function removeFAB() {
    try {
      var fab = document.getElementById('oc-fab');
      if (fab) fab.remove();
      var menu = document.getElementById('oc-fab-menu');
      if (menu) menu.remove();
      if (_fabCloseHandler) {
        document.removeEventListener('click', _fabCloseHandler);
        _fabCloseHandler = null;
      }
    } catch (e) { console.error('[OC] removeFAB error:', e); }
  }

  // ═══════════════════════════════════════════════════════
  //  Plugin Page & Commands
  // ═══════════════════════════════════════════════════════

  function buildPageHTML() {
    return (
      '<div style="padding:20px;font-family:sans-serif;color:#c9d1d9;">' +
      '<h2 style="margin:0 0 4px;font-size:18px;">OpenCode AI v3.3.0</h2>' +
      '<p style="margin:0 0 12px;font-size:12px;color:#888;">AI-powered coding in Acode</p>' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">' +
      '  <button class="oc-btn" data-act="chat" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Chat</button>' +
      '  <button class="oc-btn" data-act="inline" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Inline</button>' +
      '  <button class="oc-btn" data-act="ask" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Ask</button>' +
      '  <button class="oc-btn" data-act="fix" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Fix</button>' +
      '  <button class="oc-btn" data-act="explain" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Explain</button>' +
      '  <button class="oc-btn" data-act="generate" style="flex:1;min-width:80px;padding:10px;border:none;border-radius:6px;background:#2d7ff9;color:#fff;font-size:13px;font-weight:bold;cursor:pointer;">Generate</button>' +
      '</div>' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">' +
      '  <button class="oc-btn" data-act="status" style="flex:1;min-width:80px;padding:8px 10px;border:1px solid #888;border-radius:6px;background:transparent;color:#c9d1d9;font-size:12px;cursor:pointer;">Status</button>' +
      '  <button class="oc-btn" data-act="settings" style="flex:1;min-width:80px;padding:8px 10px;border:1px solid #888;border-radius:6px;background:transparent;color:#c9d1d9;font-size:12px;cursor:pointer;">Settings</button>' +
      '  <button class="oc-btn" data-act="debug" style="flex:1;min-width:80px;padding:8px 10px;border:1px solid #888;border-radius:6px;background:transparent;color:#c9d1d9;font-size:12px;cursor:pointer;">Debug</button>' +
      '</div>' +
      '<div style="padding:12px;border-radius:6px;background:#161b22;font-size:12px;line-height:1.7;color:#888;">' +
      '<strong style="color:#c9d1d9;">Quick tip:</strong> Tap the blue <strong style="color:#2d7ff9;">OC</strong> button at bottom-right for the action menu.<br>' +
      '<strong style="color:#c9d1d9;">Keyboard:</strong> Ctrl+Shift+K(Chat) I(Inline) A(Ask) F(Fix) E(Explain) G(Generate) S(Status) O(Settings) D(Debug)' +
      '</div></div>'
    );
  }

  function registerAll() {
    var commands = acode.require('commands');
    var defs = [
      { n: PLUGIN_ID + '.chat', d: 'Open chat panel', k: 'K', fn: handleChat },
      { n: PLUGIN_ID + '.inline', d: 'Inline chat', k: 'I', fn: handleInlineChat },
      { n: PLUGIN_ID + '.ask', d: 'Ask OpenCode', k: 'A', fn: handleAsk },
      { n: PLUGIN_ID + '.fix', d: 'Fix with OpenCode', k: 'F', fn: handleFix },
      { n: PLUGIN_ID + '.explain', d: 'Explain code', k: 'E', fn: handleExplain },
      { n: PLUGIN_ID + '.generate', d: 'Generate code', k: 'G', fn: handleGenerate },
      { n: PLUGIN_ID + '.status', d: 'Server status', k: 'S', fn: handleStatus },
      { n: PLUGIN_ID + '.debug', d: 'Debug info', k: 'D', fn: handleDebug },
      { n: PLUGIN_ID + '.settings', d: 'OpenCode settings', k: 'O', fn: showSettings },
    ];
    defs.forEach(function (c) {
      commands.addCommand({
        name: c.n,
        description: c.d,
        bindKey: { win: 'Ctrl-Shift-' + c.k, mac: 'Cmd-Shift-' + c.k },
        exec: c.fn,
      });
      _cmds.push(c.n);
    });
  }

  function unregisterAll() {
    var commands = acode.require('commands');
    _cmds.forEach(function (name) {
      try { commands.removeCommand(name); } catch (e) {}
    });
    _cmds = [];
  }

  // ═══════════════════════════════════════════════════════
  //  Init / Destroy
  // ═══════════════════════════════════════════════════════

  function init(baseUrl, $page, cache) {
    try {
      // 0. Load persisted settings
      loadSettings();
      loadChatHistory();

      // 1. Detect plugin directory
      _pluginDir = '';
      try {
        if (baseUrl && baseUrl.indexOf('file://') === 0) {
          var p = decodeURIComponent(baseUrl.replace(/^file:\/\//, ''));
          if (p.indexOf('/') !== -1) p = p.substring(0, p.lastIndexOf('/'));
          _pluginDir = p;
        }
      } catch (_) {}

      // 2. FAB
      createFAB();

      // 3. Commands
      try { registerAll(); } catch (e) { console.warn('[OC] registerAll:', e); }

      // 4. Plugin page
      var html = buildPageHTML();
      try { $page.innerHTML = html; } catch (_) {}
      try { if (typeof $page.html === 'function') $page.html(html); } catch (_) {}
      try { $page.show(); } catch (_) {}

      var actionMap = {
        chat: handleChat, inline: handleInlineChat, ask: handleAsk,
        fix: handleFix, explain: handleExplain, generate: handleGenerate,
        status: handleStatus, settings: showSettings, debug: handleDebug
      };
      try {
        $page.addEventListener('click', function (e) {
          var btn = e.target;
          if (btn && btn.classList && btn.classList.contains('oc-btn')) {
            var act = btn.getAttribute('data-act');
            if (actionMap[act]) actionMap[act]();
          }
        });
      } catch (_) {}

      // 5. Background health check — only mark ready if proxy is confirmed
      healthCheck(function (status) { if (status === 'proxy') { _serverReady = true; _activeUrl = PROXY_URL; } });
    } catch (e) {
      try { (acode.require('alert'))('OC Error', 'Init failed: ' + e.message); } catch (_) {}
      console.error('[OC] init error:', e);
    }
  }

  function destroy() {
    unregisterAll();
    removeFAB();
    hideChatPanel();
    saveChatHistory();
    saveSettings();
  }

  // ═══════════════════════════════════════════════════════
  //  Plugin Registration
  // ═══════════════════════════════════════════════════════

  acode.setPluginInit(PLUGIN_ID, init, {
    list: [
      {
        key: 'agent',
        text: 'Default Agent',
        value: 'build',
        prompt: 'Change agent (build, debug, plan, etc.)',
        promptType: 'text',
        cb: function (k, v) {
          _agent = v || 'build';
          saveSettings();
          showToast('Agent: ' + _agent);
        },
      },
      {
        key: 'server_port',
        text: 'Server Port',
        value: String(SERVER_PORT),
        prompt: 'Server port number',
        promptType: 'number',
        cb: function (k, v) { if (v) { SERVER_PORT = parseInt(v, 10); } },
      },
    ],
  });
  acode.setPluginUnmount(PLUGIN_ID, destroy);
})();
