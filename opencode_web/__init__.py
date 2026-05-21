"""
OpenCode Web Automation Module
===============================
Full browser automation using Playwright (Node.js) + Chromium.
Supports: browsing, clicking, form filling, flight booking, data extraction.

Usage:
    from opencode_web import Browser

    with Browser() as b:
        b.navigate("https://example.com")
        b.fill("#search", "flights")
        b.click("#search-btn")
        links = b.get_links()
        print(links)
"""

from .browser import Browser
from . import workflows

__version__ = "1.0.0"
__all__ = ["Browser", "workflows"]
