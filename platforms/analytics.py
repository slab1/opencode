#!/usr/bin/env python3
"""
Cross-Platform Analytics Tracker
=================================
Fetches engagement metrics from all connected platforms
and reports on performance, best times, and growth.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request
import urllib.error

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
TOKENS_DIR = PLATFORMS_DIR / "tokens"
BACKEND_CONFIG = PLATFORMS_DIR / "backend.json"
ANALYTICS_DIR = PLATFORMS_DIR / "analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
ANALYTICS_FILE = ANALYTICS_DIR / "metrics.jsonl"
LEARNING_FILE = ANALYTICS_DIR / "learning.json"

# ANSI
class C:
    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    CY = "\033[0;36m"
    M = "\033[0;35m"
    N = "\033[0m"


def get_backend() -> str:
    """Get configured backend."""
    if not BACKEND_CONFIG.exists():
        return ""
    return json.loads(BACKEND_CONFIG.read_text()).get("backend", "")


def get_token(name: str) -> str:
    """Get token by name (chmod 600 file)."""
    p = TOKENS_DIR / name
    if p.exists():
        return p.read_text().strip()
    return ""


def fetch_bulkpublish_metrics(days: int = 7) -> list:
    """Fetch metrics from BulkPublish API."""
    api_key = get_token("bulkpublish_api.key")
    if not api_key:
        return []
    try:
        req = urllib.request.Request(
            "https://app.bulkpublish.com/api/analytics",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as e:
        print(f"{C.Y}BulkPublish: {e}{C.N}", file=sys.stderr)
        return []


def fetch_trypost_metrics(server_url: str, token: str, days: int = 7) -> list:
    """Fetch metrics from TryPost instance."""
    try:
        req = urllib.request.Request(
            f"{server_url}/api/analytics?days={days}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as e:
        print(f"{C.Y}TryPost: {e}{C.N}", file=sys.stderr)
        return []


def fetch_metrics(platform: str = "all", days: int = 7) -> list:
    """Fetch metrics for a platform (or all)."""
    backend = get_backend()
    if backend == "bulkpublish":
        return fetch_bulkpublish_metrics(days)
    elif backend in ("trypost", "brightbean", "mixpost"):
        cfg_path = PLATFORMS_DIR / f"{backend}_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            url = cfg.get("url", "")
            tok_path = cfg.get("token_file", "")
            token = Path(tok_path).read_text().strip() if tok_path else ""
            return fetch_trypost_metrics(url, token, days)
    return []


def save_metrics(metrics: list):
    """Append metrics to log."""
    with ANALYTICS_FILE.open("a") as f:
        for m in metrics:
            m["_fetched"] = datetime.now(timezone.utc).isoformat()
            f.write(json.dumps(m) + "\n")


def print_report(metrics: list, days: int = 7):
    """Print formatted analytics report."""
    if not metrics:
        print(f"{C.Y}No metrics available. Has the backend collected data?{C.N}")
        return

    print(f"\n{C.CY}{'═' * 70}{C.N}")
    print(f"{C.CY}  Analytics Report — Last {days} days{C.N}")
    print(f"{C.CY}{'═' * 70}{C.N}")

    # Aggregate
    by_platform = {}
    for m in metrics:
        plat = m.get("platform", "unknown")
        by_platform.setdefault(plat, []).append(m)

    print(f"{C.B}{'Platform':<15} {'Posts':>6} {'Reach':>10} {'Likes':>8} {'Comments':>10} {'Shares':>8} {'Eng%':>7}{C.N}")
    print(f"{C.B}{'─' * 70}{C.N}")

    for plat, items in sorted(by_platform.items()):
        posts = len(items)
        reach = sum(i.get("reach", 0) or i.get("impressions", 0) for i in items)
        likes = sum(i.get("likes", 0) for i in items)
        comments = sum(i.get("comments", 0) for i in items)
        shares = sum(i.get("shares", 0) for i in items)
        eng_rate = ((likes + comments + shares) / reach * 100) if reach > 0 else 0
        print(f"{plat:<15} {posts:>6} {reach:>10,} {likes:>8,} {comments:>10,} {shares:>8,} {eng_rate:>6.2f}%")

    # Top performing posts
    print(f"\n{C.M}━━━ Top Performing Posts ━━━{C.N}\n")
    sorted_metrics = sorted(
        metrics,
        key=lambda m: (m.get("likes", 0) + m.get("comments", 0) * 2 + m.get("shares", 0) * 3),
        reverse=True,
    )
    for i, m in enumerate(sorted_metrics[:5], 1):
        engagement = m.get("likes", 0) + m.get("comments", 0) + m.get("shares", 0)
        print(f"  {i}. {m.get('platform', '?')} — {engagement:,} engagements")
        if m.get("text"):
            preview = m["text"][:60] + "..." if len(m["text"]) > 60 else m["text"]
            print(f"     \"{preview}\"")
        if m.get("posted_at"):
            print(f"     Posted: {m['posted_at']}")
        print()


def best_times(platform: str = None) -> None:
    """Analyze best posting times from history."""
    if not ANALYTICS_FILE.exists():
        print(f"{C.Y}No analytics history yet.{C.N}")
        return

    metrics = []
    for line in ANALYTICS_FILE.read_text().splitlines():
        if line.strip():
            try:
                metrics.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if platform:
        metrics = [m for m in metrics if m.get("platform") == platform]

    if not metrics:
        print(f"{C.Y}No data to analyze.{C.N}")
        return

    # Bucket by hour
    by_hour = {}
    for m in metrics:
        ts = m.get("posted_at") or m.get("created") or m.get("_fetched")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            hour = dt.hour
            day = dt.strftime("%A")
            bucket_key = (day, hour)
            engagement = m.get("likes", 0) + m.get("comments", 0) * 2 + m.get("shares", 0) * 3
            by_hour.setdefault(bucket_key, []).append(engagement)
        except Exception:
            continue

    if not by_hour:
        print(f"{C.Y}Could not parse posting times.{C.N}")
        return

    # Compute averages
    avg_by_hour = {k: sum(v) / len(v) for k, v in by_hour.items()}

    print(f"\n{C.CY}{'═' * 70}{C.N}")
    print(f"{C.CY}  Best Times to Post{C.N}")
    print(f"{C.CY}{'═' * 70}{C.N}")
    print(f"{C.B}{'Day':<10} {'Hour':>6} {'Avg Engagement':>15} {'Posts':>7}{C.N}")
    print(f"{C.B}{'─' * 40}{C.N}")

    sorted_times = sorted(avg_by_hour.items(), key=lambda x: x[1], reverse=True)
    for (day, hour), avg in sorted_times[:15]:
        count = len(by_hour[(day, hour)])
        print(f"{day:<10} {hour:>4}:00 {avg:>15.1f} {count:>7}")

    print(f"\n{C.G}💡 Tip:{C.N} Schedule your most important posts at the top times above.")


def growth_report(days: int = 30) -> None:
    """Show follower/subscriber growth over time."""
    if not ANALYTICS_FILE.exists():
        print(f"{C.Y}No analytics history yet.{C.N}")
        return

    metrics = []
    for line in ANALYTICS_FILE.read_text().splitlines():
        if line.strip():
            try:
                metrics.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Get latest followers per platform
    by_platform = {}
    for m in sorted(metrics, key=lambda x: x.get("_fetched", "")):
        plat = m.get("platform")
        if not plat or "followers" not in m:
            continue
        by_platform[plat] = m["followers"]

    if not by_platform:
        print(f"{C.Y}No follower data available.{C.N}")
        print(f"{C.Y}(Some platforms report followers separately — check your backend){C.N}")
        return

    print(f"\n{C.CY}{'═' * 50}{C.N}")
    print(f"{C.CY}  Current Follower Counts{C.N}")
    print(f"{C.CY}{'═' * 50}{C.N}")

    for plat, count in sorted(by_platform.items(), key=lambda x: x[1], reverse=True):
        bar_len = min(40, count // 100)
        bar = "█" * bar_len
        print(f"  {plat:<15} {count:>10,}  {C.G}{bar}{C.N}")


def learn(force: bool = False) -> dict:
    """Self-improving learning loop — analyzes historical engagement data
    to find patterns and save recommendations.

    This is Pattern 5 from Hermes Agent: a closed learning loop that
    continuously improves posting strategy based on real performance data.

    Returns:
        dict with keys: best_times, best_platforms, recommendations
    """
    print(f"\n{C.CY}{'═' * 70}{C.N}")
    print(f"{C.CY}  🧠 Learning Loop — Analyzing Engagement Patterns{C.N}")
    print(f"{C.CY}{'═' * 70}{C.N}")

    # Load historical metrics
    if not ANALYTICS_FILE.exists():
        print(f"{C.Y}No analytics history yet. Run 'fetch' first to collect data.{C.N}")
        return {}

    metrics = []
    for line in ANALYTICS_FILE.read_text().splitlines():
        if line.strip():
            try:
                metrics.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if len(metrics) < 3:
        print(f"{C.Y}Need at least 3 data points to learn. Have {len(metrics)}.{C.N}")
        return {}

    print(f"  Analyzing {len(metrics)} data points...")

    # ─── Learn best posting times ───
    by_day_hour = {}
    for m in metrics:
        ts = m.get("posted_at") or m.get("created") or m.get("_fetched")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            day = dt.strftime("%A")
            hour = dt.hour
            engagement = m.get("likes", 0) + m.get("comments", 0) * 2 + m.get("shares", 0) * 3
            by_day_hour.setdefault((day, hour), []).append(engagement)
        except Exception:
            continue

    best_times_learned = []
    if by_day_hour:
        avg_by_hour = {k: sum(v) / len(v) for k, v in by_day_hour.items()}
        sorted_times = sorted(avg_by_hour.items(), key=lambda x: x[1], reverse=True)
        best_times_learned = [
            {"day": day, "hour": hour, "avg_engagement": round(avg, 1), "samples": len(by_day_hour[(day, hour)])}
            for (day, hour), avg in sorted_times[:10]
        ]

    # ─── Learn best platforms ───
    by_platform_eng = {}
    for m in metrics:
        plat = m.get("platform", "unknown")
        engagement = m.get("likes", 0) + m.get("comments", 0) + m.get("shares", 0)
        by_platform_eng.setdefault(plat, []).append(engagement)

    platform_performance = []
    for plat, engagements in by_platform_eng.items():
        avg_eng = sum(engagements) / len(engagements)
        platform_performance.append({
            "platform": plat,
            "avg_engagement": round(avg_eng, 1),
            "total_posts": len(engagements),
        })
    platform_performance.sort(key=lambda x: x["avg_engagement"], reverse=True)

    # ─── Build recommendations ───
    recommendations = []
    if best_times_learned:
        top = best_times_learned[0]
        recommendations.append(
            f"Best time to post: {top['day']} at {top['hour']}:00 "
            f"(avg {top['avg_engagement']} engagement across {top['samples']} posts)"
        )

    if platform_performance:
        top_plat = platform_performance[0]
        recommendations.append(
            f"Best performing platform: {top_plat['platform']} "
            f"(avg {top_plat['avg_engagement']} engagement per post)"
        )

    if len(metrics) > 10:
        # Parse content type if we have text data
        text_lengths = []
        for m in metrics:
            text = m.get("text", "")
            if text:
                text_lengths.append(len(text))

        if text_lengths:
            avg_len = sum(text_lengths) / len(text_lengths)
            recommendations.append(
                f"Optimal post length: ~{int(avg_len)} characters "
                f"(based on {len(text_lengths)} posts)"
            )

    # ─── Save learned patterns ───
    learned = {
        "last_learned": datetime.now(timezone.utc).isoformat(),
        "total_samples": len(metrics),
        "best_times": best_times_learned,
        "best_platforms": platform_performance,
        "recommendations": recommendations,
    }
    LEARNING_FILE.write_text(json.dumps(learned, indent=2))

    # ─── Display results ───
    print(f"\n{C.G}✓ Learning complete — saved to {LEARNING_FILE}{C.N}\n")

    if best_times_learned:
        print(f"{C.B}Top 5 Posting Times:{C.N}")
        for t in best_times_learned[:5]:
            bar = "█" * min(20, int(t["avg_engagement"]))
            print(f"  {t['day']:<10} {t['hour']:>2}:00  {bar} {t['avg_engagement']}")
        print()

    if platform_performance:
        print(f"{C.B}Platform Performance (avg engagement):{C.N}")
        for p in platform_performance:
            bar = "█" * min(20, int(p["avg_engagement"]))
            print(f"  {p['platform']:<15} {bar} {p['avg_engagement']} ({p['total_posts']} posts)")
        print()

    if recommendations:
        print(f"{C.M}📋 Recommendations:{C.N}")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        print()

    return learned


def main():
    parser = argparse.ArgumentParser(
        description="Cross-Platform Analytics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd")

    # report
    r = sub.add_parser("report", help="Show analytics report")
    r.add_argument("--days", type=int, default=7)
    r.add_argument("--platform", default="all")

    # best-times
    bt = sub.add_parser("best-times", help="Best times to post")
    bt.add_argument("--platform", default=None)

    # growth
    g = sub.add_parser("growth", help="Follower growth")
    g.add_argument("--days", type=int, default=30)

    # fetch (manual)
    f = sub.add_parser("fetch", help="Fetch latest metrics from backend")
    f.add_argument("--days", type=int, default=7)

    # learn (self-improving loop — Pattern 5)
    l = sub.add_parser("learn", help="Learning loop — analyze patterns and recommend")
    l.add_argument("--force", action="store_true", help="Force re-learn even with few data points")

    args = parser.parse_args()

    if not args.cmd or args.cmd == "report":
        days = getattr(args, "days", 7) or 7
        metrics = fetch_metrics(days=days)
        if metrics:
            save_metrics(metrics)
        print_report(metrics, days=days)
    elif args.cmd == "best-times":
        best_times(args.platform)
    elif args.cmd == "growth":
        growth_report(args.days)
    elif args.cmd == "fetch":
        metrics = fetch_metrics(days=args.days)
        if metrics:
            save_metrics(metrics)
            print(f"{C.G}✓{C.N} Fetched and saved {len(metrics)} metric entries")
        else:
            print(f"{C.Y}No metrics returned from backend{C.N}")
    elif args.cmd == "learn":
        learn(force=args.force)


if __name__ == "__main__":
    main()
