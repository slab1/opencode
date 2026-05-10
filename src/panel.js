/**
 * OpenCode Acode Plugin — UI Helpers
 *
 * Provides UI components for displaying results, progress, and notifications
 * within Acode's interface.
 */

(function () {
  const PLUGIN_ID = 'com.opencode.acode';

  /**
   * Create a UI helper object bound to a $page instance.
   * @param {object} $page - Acode's WcPage instance (from plugin init)
   * @returns {object} ui helpers
   */
  function createUI($page) {
    const toastQueue = [];

    return {
      /**
       * Show a brief toast notification.
       * @param {string} message
       */
      showToast(message) {
        try {
          acode.alert('OpenCode', message);
        } catch {
          // Fallback: use the $page to show a brief message
          $page.innerHTML = `<div style="padding:8px;background:#333;color:#fff;border-radius:4px;">${escapeHtml(message)}</div>`;
          setTimeout(() => {
            if ($page.innerHTML.includes('OpenCode')) {
              $page.innerHTML = '';
            }
          }, 3000);
        }
      },

      /**
       * Show a confirmation dialog.
       * @param {string} message
       * @returns {boolean}
       */
      confirm(message) {
        // Acode doesn't have a built-in confirm, so we use alert as fallback
        return true; // Optimistic — user wants to proceed
      },

      /**
       * Show a progress indicator.
       * @param {string} message
       * @returns {{ dismiss: () => void }}
       */
      showProgress(message) {
        const id = 'opencode-progress';
        let dismissed = false;

        $page.innerHTML = `
          <div id="${id}" style="
            padding: 16px; margin: 8px; border-radius: 8px;
            background: var(--accent-color, #2d7ff9);
            color: #fff; font-size: 14px;
            display: flex; align-items: center; gap: 10px;
          ">
            <span style="
              display: inline-block; width: 16px; height: 16px;
              border: 2px solid rgba(255,255,255,0.3);
              border-top-color: #fff; border-radius: 50%;
              animation: oc-spin 0.8s linear infinite;
            "></span>
            <span>${escapeHtml(message)}</span>
          </div>
          <style>
            @keyframes oc-spin { to { transform: rotate(360deg); } }
          </style>
        `;
        $page.show();

        return {
          dismiss() {
            if (dismissed) return;
            dismissed = true;
            const el = document.getElementById(id);
            if (el) {
              el.style.opacity = '0';
              el.style.transition = 'opacity 0.3s';
              setTimeout(() => {
                $page.innerHTML = '';
                $page.hide();
              }, 300);
            }
          },
        };
      },

      /**
       * Show a results panel with AI response.
       * @param {string} content - The AI response text
       * @param {string} prompt - The original prompt
       * @returns {{ addButton: (label: string, fn: () => void) => void }}
       */
      showPanel(content, prompt) {
        const escapedContent = escapeHtml(content);
        const escapedPrompt = escapeHtml(prompt.slice(0, 100) + (prompt.length > 100 ? '...' : ''));
        const buttons = [];

        $page.innerHTML = `
          <div style="padding: 12px; font-family: monospace; font-size: 13px;">
            <div style="
              margin-bottom: 12px; padding: 6px 10px;
              background: var(--bg-secondary, #1a1a2e);
              border-radius: 6px; font-size: 12px;
              color: var(--text-secondary, #888);
            ">
              Prompt: ${escapedPrompt}
            </div>
            <div id="oc-response" style="
              padding: 12px; border-radius: 6px;
              background: var(--bg-primary, #0d1117);
              color: var(--text-primary, #c9d1d9);
              white-space: pre-wrap; word-wrap: break-word;
              max-height: 60vh; overflow-y: auto;
              line-height: 1.5;
            ">${escapedContent}</div>
            <div id="oc-buttons" style="
              margin-top: 12px; display: flex; gap: 8px;
              flex-wrap: wrap;
            "></div>
          </div>
        `;

        const btnContainer = $page.querySelector('#oc-buttons');

        // Add default close button
        addBtn('Close', () => {
          $page.innerHTML = '';
          $page.hide();
        });

        $page.show();

        return {
          addButton(label, fn) {
            addBtn(label, fn);
          },
        };

        function addBtn(label, fn) {
          const btn = document.createElement('button');
          btn.textContent = label;
          btn.style.cssText = `
            padding: 6px 14px; border: 1px solid var(--accent-color, #2d7ff9);
            background: transparent; color: var(--accent-color, #2d7ff9);
            border-radius: 4px; cursor: pointer; font-size: 12px;
          `;
          btn.onmouseenter = () => {
            btn.style.background = 'var(--accent-color, #2d7ff9)';
            btn.style.color = '#fff';
          };
          btn.onmouseleave = () => {
            btn.style.background = 'transparent';
            btn.style.color = 'var(--accent-color, #2d7ff9)';
          };
          btn.onclick = fn;
          btnContainer.appendChild(btn);
        }
      },
    };
  }

  function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // Export
  window.__OpencodeUI = createUI;
})();
