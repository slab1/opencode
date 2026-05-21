"""
Browser manager — Python wrapper around the Node.js Playwright backend.

Communicates with the Playwright backend via subprocess (stdin/stdout JSON).
Provides a clean, Pythonic API for browser automation.
"""

import json
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from typing import Any, Optional

BACKEND_SCRIPT = Path(__file__).parent / "backend" / "browser.js"
NODE_PATH = "/usr/local/lib/node_modules"
BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/home/.cache/ms-playwright")


class BrowserError(Exception):
    """Raised when a browser action fails."""
    pass


class Browser:
    """
    Chromium browser controller (headless or headed on virtual display).

    When `headless=False`, requires a running Display (opencode_display).
    The display will be started automatically if `auto_display=True`.
    """

    def __init__(
        self,
        headless: bool = True,
        viewport: Optional[dict] = None,
        executable_path: str = "/usr/bin/chromium",
        timeout: int = 30000,
        verbose: bool = False,
        auto_display: bool = True,
    ):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.executable_path = executable_path
        self.timeout = timeout
        self.verbose = verbose
        self.auto_display = auto_display
        self._display = None
        self._process: Optional[subprocess.Popen] = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _start_backend(self):
        """Launch the Node.js Playwright backend process."""
        env = os.environ.copy()
        env["NODE_PATH"] = NODE_PATH
        env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_PATH

        self._process = subprocess.Popen(
            ["node", str(BACKEND_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

        ready_line = self._process.stdout.readline()
        if not ready_line:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            raise BrowserError(f"Backend failed to start. Stderr: {stderr[:500]}")
        ready = json.loads(ready_line.strip())
        if ready.get("status") == "error":
            raise BrowserError(ready.get("error", "Backend initialization failed"))

    def _read_response(self) -> dict:
        """Read a single JSON response line from the backend."""
        response_line = self._process.stdout.readline()
        if not response_line:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            raise BrowserError(f"No response from backend. Stderr: {stderr[:500]}")

        try:
            response = json.loads(response_line.strip())
        except json.JSONDecodeError as e:
            raise BrowserError(f"Invalid JSON response: {response_line.strip()[:200]} - {e}")

        if response.get("status") == "error":
            raise BrowserError(response.get("error", "Unknown error"))

        if self.verbose:
            resp_str = json.dumps(response.get("data", {}))[:200]
            print(f"  << {resp_str}", file=sys.stderr)

        return response.get("data", {})

    def _send_command(self, command: dict) -> dict:
        """
        Send a JSON command to the backend and return the parsed response.
        """
        if not self._process or self._process.stdin.closed:
            raise BrowserError("Browser backend is not running. Call .start() first.")

        payload = json.dumps(command)
        if self.verbose:
            print(f"  >> {payload[:200]}", file=sys.stderr)

        try:
            self._process.stdin.write(payload + "\n")
            self._process.stdin.flush()
        except BrokenPipeError:
            stderr = self._process.stderr.read() if self._process.stderr else ""
            raise BrowserError(f"Browser process crashed. Stderr: {stderr[:500]}")

        return self._read_response()

    def _exec(self, action: str, **kwargs) -> dict:
        """Execute a single action and return its data."""
        cmd = {"action": action}
        cmd.update(kwargs)
        return self._send_command(cmd)

    def start(self):
        """Initialize the browser (launch Chromium)."""
        if self._initialized:
            return

        if not self.headless and self.auto_display:
            try:
                from opencode_display import ensure_display
                self._display = ensure_display()
            except ImportError:
                raise BrowserError(
                    "Cannot start headed browser: opencode_display module not found. "
                    "Install it or use headless=True."
                )

        self._start_backend()

        extra_args = []

        result = self._exec(
            "init",
            headless=self.headless,
            viewport=self.viewport,
            executable_path=self.executable_path,
            args=extra_args,
        )
        self._initialized = True
        return result

    def close(self):
        """Close the browser and clean up."""
        if not self._process:
            return

        try:
            self._exec("close")
        except Exception:
            pass

        try:
            self._process.stdin.close()
        except Exception:
            pass

        try:
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception:
            self._process.kill()

        self._process = None
        self._initialized = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate(self, url: str, wait_until: str = "load", timeout: Optional[int] = None) -> dict:
        """Navigate to a URL."""
        return self._exec("navigate", url=url, wait_until=wait_until, timeout=timeout or self.timeout)

    def back(self) -> dict:
        """Navigate back in history."""
        return self._exec("back")

    def forward(self) -> dict:
        """Navigate forward in history."""
        return self._exec("forward")

    def reload(self) -> dict:
        """Reload the current page."""
        return self._exec("reload")

    def wait_for_navigation(self, wait_until: str = "load", timeout: Optional[int] = None) -> dict:
        """Wait for a navigation to complete."""
        return self._exec("wait_for_navigation", wait_until=wait_until, timeout=timeout or self.timeout)

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------

    def click(self, selector: str, **kwargs) -> dict:
        """Click an element identified by CSS selector."""
        return self._exec("click", selector=selector, **kwargs)

    def fill(self, selector: str, value: str, **kwargs) -> dict:
        """Fill a form field (clears existing content first)."""
        return self._exec("fill", selector=selector, value=value, **kwargs)

    def type(self, selector: str, value: str, delay: int = 0) -> dict:
        """Type into a field character by character (slower, more human-like)."""
        return self._exec("type", selector=selector, value=value, delay=delay)

    def select_option(self, selector: str, value: str) -> dict:
        """Select an option in a <select> dropdown."""
        return self._exec("select_option", selector=selector, value=value)

    def check(self, selector: str, checked: bool = True) -> dict:
        """Check or uncheck a checkbox/radio."""
        return self._exec("check", selector=selector, checked=checked)

    def press_key(self, key: str, selector: Optional[str] = None) -> dict:
        """Press a keyboard key (e.g., 'Enter', 'Tab', 'Escape')."""
        return self._exec("press", key=key, selector=selector)

    def hover(self, selector: str) -> dict:
        """Hover over an element."""
        return self._exec("hover", selector=selector)

    def focus(self, selector: str) -> dict:
        """Focus on an element."""
        return self._exec("focus", selector=selector)

    def scroll(self, x: int = 0, y: int = 0, selector: Optional[str] = None) -> dict:
        """Scroll the page or a specific element."""
        return self._exec("scroll", x=x, y=y, selector=selector)

    def upload_file(self, selector: str, path: str) -> dict:
        """Upload a file via a file input."""
        return self._exec("upload_file", selector=selector, path=path)

    def submit_form(self, selector: str = "form") -> dict:
        """Submit a form."""
        return self._exec("submit_form", selector=selector)

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------

    def get_text(self, selector: Optional[str] = None) -> str:
        """Get text content. Returns body text if no selector given."""
        result = self._exec("get_text", selector=selector)
        if selector:
            return result.get("texts", [])
        return result.get("text", "")

    def get_title(self) -> str:
        """Get the page title."""
        return self._exec("get_title").get("title", "")

    def get_url(self) -> str:
        """Get the current page URL."""
        return self._exec("get_url").get("url", "")

    def get_html(self, selector: Optional[str] = None) -> str:
        """Get HTML content of the page or a specific element."""
        return self._exec("get_html", selector=selector).get("html", "")

    def get_attribute(self, selector: str, attribute: str) -> Optional[str]:
        """Get an attribute value from an element."""
        return self._exec("get_attribute", selector=selector, attribute=attribute).get("attribute")

    def get_value(self, selector: str) -> str:
        """Get the current value of a form field."""
        return self._exec("get_value", selector=selector).get("value", "")

    def get_links(self) -> list[dict]:
        """Get all links on the current page."""
        result = self._exec("get_links")
        return result.get("links", [])

    def get_form_data(self, selector: str = "form") -> list[dict]:
        """Get all form fields and their current values."""
        return self._exec("form_data", selector=selector).get("fields", [])

    def is_visible(self, selector: str, timeout: int = 5000) -> bool:
        """Check if an element is visible."""
        return self._exec("is_visible", selector=selector, timeout=timeout).get("visible", False)

    # ------------------------------------------------------------------
    # Screenshots
    # ------------------------------------------------------------------

    def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> str:
        """Take a screenshot. Returns the file path."""
        if path is None:
            path = f"/tmp/screenshot_{int(time.time())}.png"
        result = self._exec("screenshot", path=path, full_page=full_page)
        return result.get("path", path)

    # ------------------------------------------------------------------
    # JavaScript execution
    # ------------------------------------------------------------------

    def evaluate(self, expression: Optional[str] = None, function: Optional[str] = None, arg: Any = None) -> Any:
        """Execute JavaScript in the page context."""
        kwargs = {}
        if expression:
            kwargs["expression"] = expression
        if function:
            kwargs["function"] = function
        if arg is not None:
            kwargs["arg"] = arg
        return self._exec("evaluate", **kwargs).get("result")

    # ------------------------------------------------------------------
    # Waiting
    # ------------------------------------------------------------------

    def wait(self, timeout: Optional[int] = None, selector: Optional[str] = None, state: str = "visible") -> dict:
        """Wait for a condition (time in ms, or for a selector)."""
        return self._exec("wait", timeout=timeout, selector=selector, state=state)

    def wait_for_selector(self, selector: str, state: str = "visible", timeout: Optional[int] = None) -> dict:
        """Wait for a selector to appear."""
        return self._exec("wait", selector=selector, state=state, timeout=timeout or self.timeout)

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    def new_page(self, url: Optional[str] = None) -> dict:
        """Open a new tab."""
        return self._exec("new_page", url=url)

    def switch_page(self, index: int) -> dict:
        """Switch to a tab by index."""
        return self._exec("switch_page", index=index)

    def get_pages(self) -> list[dict]:
        """List all open tabs."""
        return self._exec("pages").get("pages", [])

    def close_page(self, index: Optional[int] = None) -> dict:
        """Close a tab (default: current tab)."""
        kwargs = {}
        if index is not None:
            kwargs["index"] = index
        return self._exec("close_page", **kwargs)

    # ------------------------------------------------------------------
    # Cookies & Storage
    # ------------------------------------------------------------------

    def get_cookies(self) -> list[dict]:
        """Get all browser cookies."""
        return self._exec("get_cookies").get("cookies", [])

    def set_cookies(self, cookies: list[dict]) -> dict:
        """Set browser cookies."""
        return self._exec("set_cookies", cookies=cookies)

    def clear_cookies(self) -> dict:
        """Clear all browser cookies."""
        return self._exec("clear_cookies")

    def get_local_storage(self, key: Optional[str] = None) -> Any:
        """Get localStorage data."""
        kwargs = {}
        if key:
            kwargs["key"] = key
        return self._exec("get_local_storage", **kwargs)

    # ------------------------------------------------------------------
    # Convenience / high-level
    # ------------------------------------------------------------------

    def search(self, query: str, url: str = "https://www.google.com") -> list[dict]:
        """
        Convenience: navigate to a search engine, type query, and get results.

        Works with Google as default.
        """
        self.navigate(url)
        self.fill("input[name='q']", query)
        self.press_key("Enter")
        self.wait(2000)
        return self.get_links()

    def extract_page_data(self) -> dict:
        """Extract all useful data from the current page at once."""
        return {
            "url": self.get_url(),
            "title": self.get_title(),
            "text": self.get_text()[:5000],
            "links": self.get_links(),
            "cookies": self.get_cookies(),
        }

    def display_info(self) -> Optional[dict]:
        """Get display/VNC info if running in headed mode."""
        if self._display:
            return self._display.get_info()
        try:
            from opencode_display import get_global_display
            gd = get_global_display()
            if gd.is_running:
                return gd.get_info()
        except ImportError:
            pass
        return {"headless": True}

    def status(self) -> dict:
        """Get browser status."""
        info = self._exec("status")
        if self._display:
            info["display"] = self._display.get_info()
        return info
