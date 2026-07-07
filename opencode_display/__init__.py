"""
OpenCode Display Module
========================
Manages a virtual display (Xvfb) with VNC remote access, so you can
see what the browser and video creator are doing in real time.

Usage:
    from opencode_display import Display
    
    # Automatic lifecycle management
    with Display() as d:
        print(f"VNC running at: {d.vnc_address}")
        # Browser will now show on the display
        # Video previews will render visibly

    # Or manual control
    d = Display()
    d.start()
    # ... do work ...
    d.stop()
"""

import os
import subprocess
import time
import atexit
from pathlib import Path
from typing import Optional


# Default display and VNC settings
DEFAULT_DISPLAY_NUM = 99
DEFAULT_RESOLUTION = "1920x1080x24"
DEFAULT_VNC_PORT = 5900
DEFAULT_VNC_PASSWORD = "opencode"

# Global display instance for atexit cleanup
_global_display = None


def get_global_display() -> "Display":
    """Get or create the global display instance."""
    global _global_display
    if _global_display is None:
        _global_display = Display()
    return _global_display


class DisplayError(Exception):
    """Raised when display operations fail."""
    pass


class Display:
    """
    Virtual display manager with VNC remote access.

    Starts Xvfb (virtual framebuffer) + x11vnc (VNC server) + fluxbox (WM).
    The DISPLAY environment variable is set so any browser or GUI app
    renders on the virtual screen viewable via VNC.

    Usage:
        with Display() as disp:
            disp.launch_browser("https://example.com")
            disp.launch_video_preview("my_video.mp4")

    Connecting via VNC:
        vncviewer localhost:5900
        # Or use any VNC client to <host-ip>:5900
    """

    def __init__(
        self,
        display_num: int = DEFAULT_DISPLAY_NUM,
        resolution: str = DEFAULT_RESOLUTION,
        vnc_port: int = DEFAULT_VNC_PORT,
        vnc_password: Optional[str] = DEFAULT_VNC_PASSWORD,
        auto_start: bool = False,
    ):
        self.display_num = display_num
        self.display = f":{display_num}"
        self.resolution = resolution
        self.vnc_port = vnc_port
        self.vnc_password = vnc_password
        self.auto_start = auto_start

        self._xvfb_proc: Optional[subprocess.Popen] = None
        self._vnc_proc: Optional[subprocess.Popen] = None
        self._wm_proc: Optional[subprocess.Popen] = None
        self._x11vnc_log: Optional[Path] = None

        self._running = False
        self._saved_display = os.environ.get("DISPLAY")

        if auto_start:
            self.start()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def xvfb_pid(self) -> Optional[int]:
        return self._xvfb_proc.pid if self._xvfb_proc else None

    @property
    def vnc_pid(self) -> Optional[int]:
        return self._vnc_proc.pid if self._vnc_proc else None

    @property
    def vnc_address(self) -> str:
        """Get the VNC connection address string."""
        return f"localhost:{self.vnc_port - 5900}"

    @property
    def vnc_url(self) -> str:
        """Get a VNC URL for connecting."""
        return f"vnc://localhost:{self.vnc_port}"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the virtual display, window manager, and VNC server."""
        if self._running:
            return

        # 1. Start Xvfb (virtual framebuffer)
        try:
            self._xvfb_proc = subprocess.Popen(
                [
                    "Xvfb", self.display,
                    "-screen", "0", self.resolution,
                    "-ac",  # Disable access control
                    "-nolisten", "tcp",  # No TCP for X itself
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise DisplayError(
                "Xvfb not found. Install: apk add xvfb xvfb-run"
            )

        # Wait for Xvfb to be ready
        self._wait_for_xvfb()

        # 2. Set DISPLAY environment variable
        os.environ["DISPLAY"] = self.display

        # 3. Start fluxbox window manager (lightweight)
        try:
            self._wm_proc = subprocess.Popen(
                ["fluxbox"],
                env={**os.environ, "DISPLAY": self.display},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass  # fluxbox is optional

        time.sleep(1)

        # 4. Start x11vnc (VNC server)
        try:
            vnc_cmd = [
                "x11vnc",
                "-display", self.display,
                "-forever",      # Stay running after client disconnects
                "-shared",       # Allow multiple clients
                "-noshm",        # Avoid System V shared memory (limited in containers)
                "-rfbport", str(self.vnc_port),
                "-quiet",
            ]
            if self.vnc_password:
                # Store password for reference and x11vnc auth
                pw_file = Path("/tmp/.opencode_vnc_pass")
                pw_file.write_text(self.vnc_password)
                vnc_cmd.extend(["-passwd", self.vnc_password])

            self._vnc_proc = subprocess.Popen(
                vnc_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            raise DisplayError(
                "x11vnc not found. Install: apk add x11vnc"
            )

        time.sleep(1)
        self._running = True

        # Register cleanup
        atexit.register(self.stop)

    def stop(self):
        """Stop the display, VNC, and window manager."""
        self._running = False

        # Restore original DISPLAY
        if self._saved_display:
            os.environ["DISPLAY"] = self._saved_display
        elif "DISPLAY" in os.environ:
            del os.environ["DISPLAY"]

        # Terminate processes (in reverse order)
        for proc in [self._vnc_proc, self._wm_proc, self._xvfb_proc]:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass

        self._xvfb_proc = None
        self._vnc_proc = None
        self._wm_proc = None

    def restart(self):
        """Restart the display."""
        self.stop()
        time.sleep(1)
        self.start()

    def __enter__(self):
        if not self._running:
            self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wait_for_xvfb(self, timeout: float = 5.0):
        """Wait for Xvfb to be ready to accept connections."""
        start = time.time()
        while time.time() - start < timeout:
            # Check for the X11 socket
            sock_path = Path(f"/tmp/.X11-unix/X{self.display_num}")
            if sock_path.exists():
                # Verify Xvfb responds via xdpyinfo
                try:
                    subprocess.run(
                        ["xdpyinfo", "-display", self.display],
                        capture_output=True,
                        timeout=2,
                    )
                    return
                except Exception:
                    pass

            # Also check lock file
            lock_file = Path(f"/tmp/.X{self.display_num}-lock")
            if lock_file.exists():
                time.sleep(0.5)
                if sock_path.exists():
                    return

            time.sleep(0.3)

        raise DisplayError(f"Xvfb failed to start on display {self.display} within {timeout}s")

    # ------------------------------------------------------------------
    # Integration with browser
    # ------------------------------------------------------------------

    def launch_browser(self, url: Optional[str] = None) -> dict:
        """
        Launch Chromium in headed mode on the virtual display.
        Returns process info so it can be managed/killed later.
        Uses a fresh temp user data dir to avoid stale profile issues.
        """
        if not self._running:
            self.start()

        import tempfile
        user_data_dir = tempfile.mkdtemp(prefix="chromium_display_")

        cmd = [
            "/usr/bin/chromium",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data_dir}",
        ]
        if url:
            cmd.append(url)
        # Wait a moment for browser to start rendering
        time.sleep(1)

        proc = subprocess.Popen(
            cmd,
            env={**os.environ, "DISPLAY": self.display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return {
            "pid": proc.pid,
            "process": proc,
            "display": self.display,
            "vnc": self.vnc_address,
        }

    def launch_video_preview(self, video_path: str) -> dict:
        """
        Launch a video player (ffplay) on the virtual display
        to preview a video file.
        """
        if not self._running:
            self.start()

        cmd = [
            "ffplay",
            "-window_title", f"OpenCode Video Preview: {Path(video_path).name}",
            video_path,
            "-autoexit",
        ]

        proc = subprocess.Popen(
            cmd,
            env={**os.environ, "DISPLAY": self.display},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return {
            "pid": proc.pid,
            "process": proc,
            "display": self.display,
            "vnc": self.vnc_address,
        }

    def take_screenshot(self, output_path: str = "/tmp/display_screenshot.png") -> str:
        """Take a screenshot of the virtual display using import (ImageMagick)."""
        if not self._running:
            self.start()

        try:
            subprocess.run(
                ["import", "-window", "root", output_path],
                env={**os.environ, "DISPLAY": self.display},
                capture_output=True,
                timeout=10,
            )
            return output_path
        except FileNotFoundError:
            # Fallback: use xwd + convert
            try:
                xwd_path = output_path.replace(".png", ".xwd")
                subprocess.run(
                    ["xwd", "-root", "-display", self.display, "-out", xwd_path],
                    capture_output=True, timeout=10,
                )
                subprocess.run(
                    ["convert", xwd_path, output_path],
                    capture_output=True, timeout=10,
                )
                Path(xwd_path).unlink(missing_ok=True)
                return output_path
            except Exception as e:
                raise DisplayError(f"Cannot take screenshot: {e}")

    def get_info(self) -> dict:
        """Get full status info about the display."""
        return {
            "running": self._running,
            "display": self.display,
            "resolution": self.resolution,
            "vnc_port": self.vnc_port,
            "vnc_address": self.vnc_address if self._running else None,
            "vnc_url": self.vnc_url if self._running else None,
            "xvfb_pid": self.xvfb_pid,
            "vnc_pid": self.vnc_pid,
            "password": self.vnc_password,
        }


def ensure_display() -> Display:
    """Ensure the global display is running and return it."""
    d = get_global_display()
    if not d.is_running:
        d.start()
    return d
