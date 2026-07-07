"""
High-level web automation workflows.
Includes flight booking, search, form workflows, and more.
"""

import json
import re
import time
from typing import Optional

from .browser import Browser


# ---------------------------------------------------------------------------
# Generic workflow helpers
# ---------------------------------------------------------------------------


def fill_form(browser: Browser, fields: list[dict]) -> dict:
    """
    Fill a series of form fields.

    Each field dict supports:
        - selector: CSS selector (required)
        - value: text value to fill, or option value for selects
        - type: 'text' | 'select' | 'checkbox' | 'file' | 'textarea'
        - wait_before: ms to wait before interacting
        - wait_after: ms to wait after interacting
    """
    results = []
    for field in fields:
        sel = field.get("selector")
        val = field.get("value", "")
        ftype = field.get("type", "text")
        wait_before = field.get("wait_before", 0)
        wait_after = field.get("wait_after", 0)

        if wait_before:
            browser.wait(timeout=wait_before)

        try:
            if ftype == "select":
                browser.select_option(sel, val)
            elif ftype == "checkbox":
                browser.check(sel, checked=field.get("checked", True))
            elif ftype == "file":
                browser.upload_file(sel, val)
            else:
                browser.fill(sel, val)

            results.append({"selector": sel, "status": "ok"})
        except Exception as e:
            results.append({"selector": sel, "status": "error", "error": str(e)})

        if wait_after:
            browser.wait(timeout=wait_after)

    return {"filled": len(results), "errors": sum(1 for r in results if r["status"] == "error")}


def click_links_by_text(browser: Browser, text: str, partial: bool = True) -> bool:
    """Click a link by its visible text content."""
    links = browser.get_links()
    for link in links:
        link_text = link.get("text", "")
        if (partial and text.lower() in link_text.lower()) or (text.lower() == link_text.lower()):
            browser.click(f"a:has-text('{link_text}')")
            return True
    return False


def extract_table(browser: Browser, selector: str = "table") -> list[dict]:
    """Extract data from an HTML table."""
    result = browser.evaluate(expression=f"""
        (() => {{
            const table = document.querySelector('{selector}');
            if (!table) return [];
            const headers = [...table.querySelectorAll('th')].map(th => th.textContent.trim());
            const rows = [...table.querySelectorAll('tr')];
            return rows.slice(headers.length > 0 ? 1 : 0).map(row => {{
                const cells = [...row.querySelectorAll('td')];
                if (headers.length) {{
                    const obj = {{}};
                    cells.forEach((cell, i) => {{ if (i < headers.length) obj[headers[i]] = cell.textContent.trim(); }});
                    return obj;
                }}
                return cells.map(c => c.textContent.trim());
            }});
        }})()
    """)
    return result or []


# ---------------------------------------------------------------------------
# Flight booking workflow
# ---------------------------------------------------------------------------

def search_flights(
    browser: Browser,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    passengers: int = 1,
    airline: Optional[str] = None,
    max_price: Optional[float] = None,
    site: str = "google_flights",
) -> list[dict]:
    """
    Search for flights on a booking site.

    Args:
        browser: An initialized Browser instance
        origin: Departure city/airport code (e.g., "JFK" or "New York")
        destination: Arrival city/airport code
        departure_date: Departure date (format depends on site)
        return_date: Optional return date for round trips
        passengers: Number of passengers
        airline: Optional airline filter
        max_price: Optional max price filter
        site: Which booking site to use ("google_flights", "skyscanner", "expedia", "kayak")

    Returns:
        List of flight results as dicts
    """
    results = []

    if site == "google_flights":
        results = _search_google_flights(browser, origin, destination, departure_date, return_date, passengers)
    elif site == "skyscanner":
        results = _search_skyscanner(browser, origin, destination, departure_date, return_date)
    elif site in ("expedia", "kayak"):
        results = _search_generic_ota(browser, origin, destination, departure_date, return_date, site)
    else:
        raise ValueError(f"Unknown site: {site}")

    # Apply filters
    if airline:
        results = [r for r in results if airline.lower() in r.get("airline", "").lower()]
    if max_price:
        results = [r for r in results if _parse_price(r.get("price", "0")) <= max_price]

    return results


def _parse_price(price_str: str) -> float:
    """Extract a numeric price from a string like '$299.99'."""
    match = re.search(r"[\d,.]+", price_str.replace(",", ""))
    if match:
        return float(match.group())
    return 0.0


def _search_google_flights(
    browser, origin, destination, dep_date, ret_date, passengers
) -> list[dict]:
    """Search flights on Google Flights."""
    url = "https://www.google.com/travel/flights"
    browser.navigate(url)
    browser.wait(3000)

    try:
        # Try to fill origin
        origin_input = "input[aria-label*='Where from'], input[placeholder*='Departure'], input[aria-label*='origin']"
        if browser.is_visible(origin_input, timeout=3000):
            browser.fill(origin_input, origin)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Fill destination
        dest_input = "input[aria-label*='Where to'], input[placeholder*='Destination'], input[aria-label*='destination']"
        if browser.is_visible(dest_input, timeout=3000):
            browser.fill(dest_input, destination)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Fill departure date
        date_input = "input[aria-label*='Departure'], input[aria-label*='Date']"
        if browser.is_visible(date_input, timeout=3000):
            browser.fill(date_input, dep_date)
            browser.press_key("Enter")
            browser.wait(1000)

        # Click search / explore
        search_btn = "button[aria-label*='Search'], button:has-text('Explore'), button:has-text('Search')"
        if browser.is_visible(search_btn, timeout=2000):
            browser.click(search_btn)
        else:
            browser.press_key("Enter")

        browser.wait(5000)

        # Extract flight results
        result = browser.evaluate(expression="""
            () => {
                const flights = [];
                const cards = document.querySelectorAll('[role="listitem"], .Rk10dc, .yVPjMd');
                cards.forEach(card => {
                    const texts = card.textContent.trim();
                    flights.push({ text: texts.substring(0, 500) });
                });
                return flights.length > 0 ? flights : [{ text: document.body.innerText.substring(0, 2000) }];
            }
        """)
        return result or []

    except Exception as e:
        return [{"error": str(e), "page_content": browser.get_text()[:2000]}]


def _search_skyscanner(browser, origin, destination, dep_date, ret_date):
    """Search flights on Skyscanner."""
    url = "https://www.skyscanner.com/"
    browser.navigate(url)
    browser.wait(3000)

    try:
        # Accept cookies if prompted
        try:
            accept_btn = "button:has-text('Accept'), button:has-text('Accept all')"
            if browser.is_visible(accept_btn, timeout=2000):
                browser.click(accept_btn)
                browser.wait(1000)
        except Exception:
            pass

        # Fill origin
        origin_inputs = "input[placeholder*='From'], input[placeholder*='Origin'], input[aria-label*='origin']"
        if browser.is_visible(origin_inputs, timeout=3000):
            browser.fill(origin_inputs, origin)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Fill destination
        dest_inputs = "input[placeholder*='To'], input[placeholder*='Destination'], input[aria-label*='destination']"
        if browser.is_visible(dest_inputs, timeout=3000):
            browser.fill(dest_inputs, destination)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Click search
        search_btn = "button[type='submit'], button:has-text('Search')"
        if browser.is_visible(search_btn, timeout=2000):
            browser.click(search_btn)
            browser.wait(5000)

        # Extract results
        content = browser.get_text()[:5000]
        return [{"page_content": content}]

    except Exception as e:
        return [{"error": str(e), "page_content": browser.get_text()[:2000]}]


def _search_generic_ota(browser, origin, destination, dep_date, ret_date, site):
    """Generic OTA (Expedia/Kayak) flight search."""
    urls = {
        "expedia": "https://www.expedia.com/Flights",
        "kayak": "https://www.kayak.com/flights",
    }
    url = urls.get(site, urls["expedia"])
    browser.navigate(url)
    browser.wait(3000)

    try:
        # Fill origin
        origin_sel = "input[aria-label*='origin'], input[aria-label*='from'], input[placeholder*='origin']"
        if browser.is_visible(origin_sel, timeout=3000):
            browser.fill(origin_sel, origin)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Fill destination
        dest_sel = "input[aria-label*='destination'], input[aria-label*='to'], input[placeholder*='destination']"
        if browser.is_visible(dest_sel, timeout=3000):
            browser.fill(dest_sel, destination)
            browser.wait(1500)
            browser.press_key("Enter")
            browser.wait(1000)

        # Click search
        search_btn = "button:has-text('Search'), button[type='submit']"
        if browser.is_visible(search_btn, timeout=2000):
            browser.click(search_btn)
            browser.wait(5000)

        content = browser.get_text()[:5000]
        return [{"page_content": content}]

    except Exception as e:
        return [{"error": str(e), "page_content": browser.get_text()[:2000]}]


# ---------------------------------------------------------------------------
# Generic "browse and do" workflow
# ---------------------------------------------------------------------------


def browse_and_extract(
    url: str,
    actions: list[dict],
    headless: bool = True,
    screenshot: bool = False,
) -> dict:
    """
    Execute a series of browser actions on a URL and return results.

    Each action:
        {"action": "navigate|click|fill|wait|extract|screenshot", ...}

    Example:
        browse_and_extract("https://example.com", [
            {"action": "wait", "timeout": 2000},
            {"action": "extract", "type": "text"},
        ])
    """
    result = {"url": url, "steps": []}

    with Browser(headless=headless) as browser:
        browser.navigate(url)

        for i, action in enumerate(actions):
            step = {"step": i, "action": action.get("action")}
            try:
                act = action["action"]

                if act == "wait":
                    browser.wait(timeout=action.get("timeout", 2000))
                    step["status"] = "ok"

                elif act == "click":
                    browser.click(action["selector"])
                    step["status"] = "ok"

                elif act == "fill":
                    browser.fill(action["selector"], action["value"])
                    step["status"] = "ok"

                elif act == "extract":
                    etype = action.get("type", "text")
                    if etype == "text":
                        step["data"] = browser.get_text()[:action.get("max_length", 5000)]
                    elif etype == "links":
                        step["data"] = browser.get_links()
                    elif etype == "html":
                        step["data"] = browser.get_html()[:action.get("max_length", 10000)]
                    elif etype == "title":
                        step["data"] = browser.get_title()
                    elif etype == "screenshot":
                        step["data"] = browser.screenshot(
                            path=action.get("path"),
                            full_page=action.get("full_page", False),
                        )
                    elif etype == "table":
                        step["data"] = extract_table(browser, action.get("selector", "table"))
                    elif etype == "all":
                        step["data"] = browser.extract_page_data()
                    step["status"] = "ok"

                elif act == "screenshot":
                    step["data"] = browser.screenshot(
                        path=action.get("path"),
                        full_page=action.get("full_page", False),
                    )
                    step["status"] = "ok"

                elif act == "evaluate":
                    step["data"] = browser.evaluate(expression=action["expression"])
                    step["status"] = "ok"

                elif act == "select":
                    browser.select_option(action["selector"], action["value"])
                    step["status"] = "ok"

                elif act == "type":
                    browser.type(action["selector"], action["value"])
                    step["status"] = "ok"

                else:
                    step["status"] = "error"
                    step["error"] = f"Unknown action: {act}"

            except Exception as e:
                step["status"] = "error"
                step["error"] = str(e)

            result["steps"].append(step)

        if screenshot:
            result["final_screenshot"] = browser.screenshot()

    return result
