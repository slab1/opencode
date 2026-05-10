/**
 * OpenCode HTTP API Client
 *
 * Thin client for OpenCode's headless server REST API.
 * Connects to `opencode serve` running in Termux.
 *
 * API Reference:
 *   POST /session          → Create a new session
 *   GET  /session/{id}     → Get session info
 *   POST /session/{id}/message  → Send a prompt
 *   GET  /session/{id}/message  → List messages
 *   GET  /session/{id}/message/{messageID} → Get specific message
 *   GET  /event            → SSE event stream
 *   GET  /agent            → List available agents
 */

class OpencodeClient {
  /**
   * @param {string} baseUrl - Server URL (e.g. "http://127.0.0.1:9876")
   */
  constructor(baseUrl) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this._sessionId = null;
  }

  /**
   * Check if the OpenCode server is reachable.
   * @returns {Promise<boolean>}
   */
  async healthCheck() {
    try {
      const res = await fetch(`${this.baseUrl}/session/status`, {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  /**
   * List available AI agents.
   * @returns {Promise<Array<{id: string, name: string}>>}
   */
  async listAgents() {
    const res = await this._fetch('/agent');
    if (!res.ok) throw new Error(`Failed to list agents: ${res.status}`);
    return res.json();
  }

  /**
   * Create a new session with a specified agent.
   * @param {string} agent - Agent ID (e.g. "build", "debug", "orchestrator")
   * @returns {Promise<string>} Session ID
   */
  async createSession(agent = 'build') {
    const res = await this._fetch('/session', {
      method: 'POST',
      body: JSON.stringify({ agent }),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Failed to create session: ${res.status} — ${err}`);
    }
    const data = await res.json();
    this._sessionId = data.id;
    return data.id;
  }

  /**
   * Get the current session ID.
   */
  get sessionId() {
    return this._sessionId;
  }

  /**
   * Send a prompt to the current session and wait for the AI response.
   *
   * Flow:
   *   1. POST a message (prompt) to the session
   *   2. Poll for the assistant's response message
   *   3. Return the completed message
   *
   * @param {string} text - The prompt text
   * @param {object} [options]
   * @param {number} [options.timeout=120000] - Max wait time in ms
   * @param {number} [options.pollInterval=500] - Poll interval in ms
   * @returns {Promise<{content: string, diffs: Array}>}
   */
  async prompt(text, options = {}) {
    const { timeout = 120000, pollInterval = 500 } = options;
    const sessionId = this._sessionId;
    if (!sessionId) throw new Error('No active session. Call createSession() first.');

    // Step 1: Send the prompt as a user message
    const msgRes = await this._fetch(`/session/${sessionId}/message`, {
      method: 'POST',
      body: JSON.stringify({
        role: 'user',
        parts: [{ type: 'text', text }],
      }),
    });
    if (!msgRes.ok) {
      const err = await msgRes.text();
      throw new Error(`Failed to send prompt: ${msgRes.status} — ${err}`);
    }

    // Step 2: Poll for the assistant response
    const startTime = Date.now();
    let lastMessageCount = 0;

    while (Date.now() - startTime < timeout) {
      // List all messages in the session
      const listRes = await this._fetch(`/session/${sessionId}/message`);
      if (!listRes.ok) {
        await this._sleep(pollInterval);
        continue;
      }

      const messages = await listRes.json();
      const assistantMessages = (messages || []).filter(
        (m) => m.role === 'assistant'
      );

      if (assistantMessages.length > lastMessageCount) {
        // New assistant message found — get the latest one
        const latest = assistantMessages[assistantMessages.length - 1];
        const full = await this._fetch(
          `/session/${sessionId}/message/${latest.id}`
        );
        if (full.ok) {
          const detail = await full.json();
          const content = this._extractText(detail);
          const diffs = detail.summary?.diffs || [];
          return { content, diffs, messageId: latest.id };
        }
      }

      lastMessageCount = assistantMessages.length;
      await this._sleep(pollInterval);
    }

    throw new Error('Timed out waiting for AI response');
  }

  /**
   * Get the diff (file changes) for a session.
   * @returns {Promise<Array<{file: string, before: string, after: string}>>}
   */
  async getDiff() {
    const sessionId = this._sessionId;
    if (!sessionId) return [];
    const res = await this._fetch(`/session/${sessionId}/diff`);
    if (!res.ok) return [];
    const data = await res.json();
    return data || [];
  }

  /**
   * Delete the current session.
   */
  async deleteSession() {
    if (!this._sessionId) return;
    await this._fetch(`/session/${this._sessionId}`, { method: 'DELETE' });
    this._sessionId = null;
  }

  // ─── Internal ────────────────────────────

  async _fetch(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });
  }

  _extractText(message) {
    if (!message || !message.parts) return '';
    return message.parts
      .filter((p) => p.type === 'text')
      .map((p) => p.text)
      .join('\n');
  }

  _sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }
}

// Export for use by the plugin
window.__OpencodeClient = OpencodeClient;
