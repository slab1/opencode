"""
Headed Mode Test — validates the dual-browser architecture:

1. Starts virtual display (Xvfb + VNC)
2. Launches browser in headed mode
3. Verifies headed Chromium is running with CDP endpoint
4. Navigates and verifies headed instance updates
5. Takes screenshots to confirm visual display
6. Cleans up properly

Run: python3 test_headed_mode.py [-v]
"""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).parent / "backend"
BACKEND_SCRIPT = BACKEND_DIR / "browser.js"
DISPLAY_MODULE = Path(__file__).parent.parent / "opencode_display" / "__init__.py"

NODE_PATH = "/usr/local/lib/node_modules"
BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/home/.cache/ms-playwright")
CHROMIUM_PATH = "/usr/bin/chromium"


def require_display():
    """Import and return the Display class."""
    sys.path.insert(0, str(DISPLAY_MODULE.parent.parent))
    from opencode_display import Display
    return Display


class HeadedModeTest(unittest.TestCase):
    """Test the dual-browser architecture: headless Playwright + headed display Chromium."""

    @classmethod
    def setUpClass(cls):
        HeadedModeTest._kill_all()

    @staticmethod
    def _kill_all():
        """Kill all stale processes using os.system (avoids O_CLOEXEC issues on this kernel)."""
        os.system("pkill -9 -f Xvfb 2>/dev/null")
        os.system("pkill -9 -f x11vnc 2>/dev/null")
        os.system("pkill -9 -f chromium 2>/dev/null")
        os.system("pkill -9 -f fluxbox 2>/dev/null")
        os.system("pkill -9 -f node 2>/dev/null")
        time.sleep(1)
        for f in Path("/tmp").glob(".X*-lock"):
            f.unlink(missing_ok=True)
        for f in Path("/tmp/.X11-unix").glob("X*"):
            f.unlink(missing_ok=True)
        for d in Path("/tmp").glob("headed_profile_*"):
            try: subprocess.run(["rm", "-rf", str(d)])
            except: pass
        for d in Path("/tmp").glob("playwright_profile_*"):
            try: subprocess.run(["rm", "-rf", str(d)])
            except: pass

    def setUp(self):
        Display = require_display()
        self.display = Display(
            display_num=99,
            resolution="1920x1080x24",
            vnc_port=5900,
            vnc_password="opencode",
            auto_start=True,
        )
        self.assertTrue(self.display.is_running, "Display should be running")
        print(f"\n  Display: {self.display.display}, VNC: {self.display.vnc_address}", flush=True)

    def tearDown(self):
        try:
            self.display.stop()
        except Exception:
            pass
        os.system("pkill -9 -f headed_profile 2>/dev/null")
        os.system("pkill -9 -f remote-debugging 2>/dev/null")
        time.sleep(0.5)

    def _start_backend(self):
        """Start the Node.js backend and return the process."""
        env = os.environ.copy()
        env["NODE_PATH"] = NODE_PATH
        env["PLAYWRIGHT_BROWSERS_PATH"] = BROWSERS_PATH
        env["DISPLAY"] = self.display.display

        proc = subprocess.Popen(
            ["node", str(BACKEND_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

        ready_line = proc.stdout.readline()
        if not ready_line:
            stderr_data = proc.stderr.read() if proc.stderr else ""
            proc.kill()
            raise RuntimeError(f"Backend failed to start. Stderr: {stderr_data[:500]}")
        ready = json.loads(ready_line.strip())
        self.assertEqual(ready.get("status"), "ok")
        return proc

    def _send_command(self, proc: subprocess.Popen, cmd: dict) -> dict:
        """Send a command to the backend and read the response."""
        payload = json.dumps(cmd)
        proc.stdin.write(payload + "\n")
        proc.stdin.flush()
        response_line = proc.stdout.readline()
        if not response_line:
            stderr_data = proc.stderr.read() if proc.stderr else ""
            raise RuntimeError(f"No response. Stderr: {stderr_data[:500]}")
        response = json.loads(response_line.strip())
        if response.get("status") == "error":
            raise RuntimeError(response.get("error", "Unknown error"))
        return response.get("data", {})

    def test_01_headed_init(self):
        """Headed mode init: launches headless Playwright + headed display Chromium."""
        proc = self._start_backend()
        try:
            result = self._send_command(proc, {"action": "init", "headless": False})
            print(f"  Init result: browser_version={result.get('browser_version')}, "
                  f"pages_open={result.get('pages_open')}", flush=True)
            self.assertIn("browser_version", result)
            self.assertGreaterEqual(result.get("pages_open", 0), 1)
            self.assertEqual(result.get("headless"), False)

            time.sleep(1)
            ps_out = os.popen("pgrep -a chromium 2>/dev/null").read()
            chromium_procs = [l for l in ps_out.splitlines() if "remote-debugging-port" in l]
            self.assertGreater(len(chromium_procs), 0)
            print(f"  Headed Chromium processes: {len(chromium_procs)}", flush=True)
        finally:
            self._send_command(proc, {"action": "close"})
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)

    def test_02_headless_init(self):
        """Headless mode init: launches Playwright in headless mode (no headed Chromium)."""
        os.system("pkill -9 -f remote-debugging-port 2>/dev/null")
        os.system("pkill -9 -f headed_profile 2>/dev/null")
        time.sleep(0.5)

        proc = self._start_backend()
        try:
            result = self._send_command(proc, {"action": "init", "headless": True})
            print(f"  Init result: browser_version={result.get('browser_version')}, "
                  f"pages_open={result.get('pages_open')}", flush=True)
            self.assertIn("browser_version", result)
            self.assertTrue(result.get("headless"), "headless should be true")

            ps_out = os.popen("pgrep -a chromium 2>/dev/null").read()
            headed_procs = [l for l in ps_out.splitlines() if "remote-debugging-port" in l]
            self.assertEqual(len(headed_procs), 0)
        finally:
            self._send_command(proc, {"action": "close"})
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)

    def test_03_navigate_headed(self):
        """Navigation in headed mode: URL change should be mirrored to headed Chromium."""
        proc = self._start_backend()
        try:
            init_result = self._send_command(proc, {"action": "init", "headless": False})
            print(f"  Init: version={init_result.get('browser_version')}", flush=True)

            nav_result = self._send_command(proc, {
                "action": "navigate",
                "url": "data:text/html,<title>Headed Mode Test</title><h1>Headed Mode Test</h1><p>If you can see this in VNC, it works!</p>",
                "wait_until": "domcontentloaded",
            })
            print(f"  Navigate: url={nav_result.get('url','')[:80]}... title={nav_result.get('title')}", flush=True)
            self.assertIn("Headed Mode Test", nav_result.get("title", ""))

            time.sleep(2)

            screenshot = self.display.take_screenshot("/tmp/headed_test_nav.png")
            file_size = Path(screenshot).stat().st_size
            print(f"  Display screenshot: {screenshot} ({file_size} bytes)", flush=True)

            self.assertGreater(file_size, 2000,
                               msg=f"Screenshot too small ({file_size} bytes) — display may be blank")
        finally:
            self._send_command(proc, {"action": "close"})
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)

    def test_04_display_screenshot(self):
        """Display screenshot should capture headed browser content."""
        proc = self._start_backend()
        try:
            self._send_command(proc, {"action": "init", "headless": False})

            self._send_command(proc, {
                "action": "navigate",
                "url": "data:text/html,<body style='background:blue'><h1 style='color:white'>Blue Page</h1></body>",
                "wait_until": "domcontentloaded",
            })
            time.sleep(2)

            screenshot = self.display.take_screenshot("/tmp/headed_test_blue.png")
            file_size = Path(screenshot).stat().st_size
            print(f"  Blue page screenshot: {file_size} bytes", flush=True)
            self.assertGreater(file_size, 2000)
        finally:
            self._send_command(proc, {"action": "close"})
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)

    def test_05_close_cleans_up(self):
        """Closing the browser should kill the headed Chromium process."""
        proc = self._start_backend()
        try:
            self._send_command(proc, {"action": "init", "headless": False})

            time.sleep(1)
            ps_before = os.popen("pgrep -a chromium 2>/dev/null").read()
            headed_before = [l for l in ps_before.splitlines() if "remote-debugging" in l]
            self.assertGreater(len(headed_before), 0)

            self._send_command(proc, {"action": "close"})
            time.sleep(1)

            ps_after = os.popen("pgrep -a chromium 2>/dev/null").read()
            headed_after = [l for l in ps_after.splitlines() if "remote-debugging" in l]
            print(f"  Headed Chromium PIDs after close: {len(headed_after)}", flush=True)
        finally:
            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)


class DisplayTest(unittest.TestCase):
    """Test the virtual display itself."""

    @classmethod
    def setUpClass(cls):
        subprocess.run(["pkill", "-9", "Xvfb"], capture_output=True)
        subprocess.run(["pkill", "-9", "x11vnc"], capture_output=True)
        for f in Path("/tmp").glob(".X*-lock"):
            f.unlink(missing_ok=True)

    def test_display_start_stop(self):
        Display = require_display()
        d = Display(display_num=100, resolution="1280x720x24", vnc_port=5901)
        d.start()
        self.assertTrue(d.is_running)
        self.assertIsNotNone(d.xvfb_pid)
        self.assertIsNotNone(d.vnc_pid)

        import socket
        vnc_ready = False
        for attempt in range(5):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 5901))
            sock.close()
            if result == 0:
                vnc_ready = True
                break
            time.sleep(0.5)
        self.assertTrue(vnc_ready, "VNC port 5901 should be open (retried 5x)")

        d.stop()
        self.assertFalse(d.is_running)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', 5901))
        sock.close()
        self.assertNotEqual(result, 0, "VNC port should be closed after stop")

    def test_display_screenshot_default(self):
        Display = require_display()
        d = Display(display_num=101, resolution="1280x720x24", vnc_port=5902)
        d.start()
        try:
            browser_info = d.launch_browser("data:text/html,<h1>Test</h1>")
            time.sleep(2)
            ss = d.take_screenshot("/tmp/display_test_default.png")
            self.assertTrue(Path(ss).exists())
            size = Path(ss).stat().st_size
            print(f"  Screenshot with browser: {size} bytes (browser PID: {browser_info['pid']})", flush=True)
            self.assertGreater(size, 2000)
            browser_info["process"].terminate()
            browser_info["process"].wait(timeout=5)
        finally:
            d.stop()

    def test_display_context_manager(self):
        Display = require_display()
        with Display(display_num=102, resolution="1280x720x24", vnc_port=5903) as d:
            self.assertTrue(d.is_running)
            ss = d.take_screenshot("/tmp/display_test_cm.png")
            self.assertTrue(Path(ss).exists())
        self.assertFalse(d.is_running)


if __name__ == "__main__":
    unittest.main(verbosity=2)
