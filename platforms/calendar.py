#!/usr/bin/env python3
"""
Content Calendar & Scheduler
=============================
Manage scheduled posts across all platforms.
Stores posts in JSON, dispatches to platform-manager when due.
"""

import json
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import shlex

PLATFORMS_DIR = Path.home() / ".config" / "opencode" / "platforms"
CALENDAR_FILE = PLATFORMS_DIR / "calendar.json"
LOG_FILE = PLATFORMS_DIR / "calendar.log"

# ANSI colors
class C:
    R = "\033[0;31m"
    G = "\033[0;32m"
    Y = "\033[1;33m"
    B = "\033[0;34m"
    CY = "\033[0;36m"
    M = "\033[0;35m"
    N = "\033[0m"


def load_calendar() -> dict:
    """Load calendar from disk."""
    if CALENDAR_FILE.exists():
        return json.loads(CALENDAR_FILE.read_text())
    return {"posts": [], "recurring": []}


def save_calendar(cal: dict):
    """Save calendar to disk."""
    PLATFORMS_DIR.mkdir(parents=True, exist_ok=True)
    CALENDAR_FILE.write_text(json.dumps(cal, indent=2, ensure_ascii=False))


def add_post(text: str, platforms: list, schedule: str, media: str = "",
             hashtags: list = None, first_comment: str = "",
             recurring: str = None, title: str = "") -> str:
    """Add a post to the calendar."""
    cal = load_calendar()

    # Parse schedule
    if schedule.lower() in ("now", "asap"):
        when = datetime.now(timezone.utc).isoformat()
        status = "pending"
    else:
        try:
            dt = datetime.fromisoformat(schedule).replace(tzinfo=timezone.utc)
            when = dt.isoformat()
            status = "scheduled"
        except ValueError:
            print(f"{C.R}Error: Invalid schedule format. Use ISO 8601 or 'now'/{C.N}")
            sys.exit(1)

    post_id = f"cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(cal['posts']):03d}"

    post = {
        "id": post_id,
        "title": title or f"Post {len(cal['posts']) + 1}",
        "text": text,
        "platforms": platforms,
        "media": media,
        "hashtags": hashtags or [],
        "first_comment": first_comment,
        "schedule": when,
        "status": status,
        "created": datetime.now(timezone.utc).isoformat(),
        "recurring": recurring,  # daily, weekly, monthly
    }

    cal["posts"].append(post)
    save_calendar(cal)

    with LOG_FILE.open("a") as f:
        f.write(f"[{datetime.now().isoformat()}] ADD: {post_id} schedule={when}\n")

    print(f"{C.G}✓{C.N} Added: {post_id}")
    print(f"  Title: {post['title']}")
    print(f"  Schedule: {when}")
    print(f"  Platforms: {', '.join(platforms)}")
    if recurring:
        print(f"  Recurring: {recurring}")
    return post_id


def list_posts(show_all: bool = False, days: int = 7) -> None:
    """List upcoming posts."""
    cal = load_calendar()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)

    if not cal["posts"]:
        print(f"{C.Y}No posts scheduled.{C.N}")
        return

    # Filter
    if show_all:
        posts = cal["posts"]
        title = f"All Posts ({len(posts)})"
    else:
        posts = [
            p for p in cal["posts"]
            if p["status"] in ("scheduled", "pending")
            and datetime.fromisoformat(p["schedule"]) <= horizon
        ]
        title = f"Next {days} Days ({len(posts)})"

    print(f"\n{C.CY}{'═' * 70}{C.N}")
    print(f"{C.CY}  {title}{C.N}")
    print(f"{C.CY}{'═' * 70}{C.N}\n")

    for p in posts:
        when = datetime.fromisoformat(p["schedule"])
        delta = when - now
        status_color = {
            "scheduled": C.B,
            "pending": C.Y,
            "posted": C.G,
            "failed": C.R,
        }.get(p["status"], C.N)

        print(f"{status_color}●{C.N} {p['id']}  {p['title']}")
        print(f"  When:    {when.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"  Status:  {p['status']}")
        print(f"  Delay:   {delta}")
        print(f"  Where:   {', '.join(p['platforms'])}")
        if p.get("media"):
            print(f"  Media:   {p['media']}")
        if p.get("hashtags"):
            print(f"  Tags:    {' '.join('#' + h for h in p['hashtags'])}")
        if p.get("recurring"):
            print(f"  Repeat:  {p['recurring']}")
        text_preview = p["text"][:80] + "..." if len(p["text"]) > 80 else p["text"]
        print(f"  Text:    {text_preview}")
        print()


def remove_post(post_id: str) -> None:
    """Remove a post from the calendar."""
    cal = load_calendar()
    original = len(cal["posts"])
    cal["posts"] = [p for p in cal["posts"] if p["id"] != post_id]
    if len(cal["posts"]) < original:
        save_calendar(cal)
        with LOG_FILE.open("a") as f:
            f.write(f"[{datetime.now().isoformat()}] REMOVE: {post_id}\n")
        print(f"{C.G}✓{C.N} Removed: {post_id}")
    else:
        print(f"{C.R}✗{C.N} Not found: {post_id}")


def process_due_posts(dry_run: bool = False) -> None:
    """Process posts that are due and post them."""
    cal = load_calendar()
    now = datetime.now(timezone.utc)
    posted = 0
    failed = 0

    for post in cal["posts"]:
        if post["status"] not in ("scheduled", "pending"):
            continue
        when = datetime.fromisoformat(post["schedule"])
        if when > now:
            continue

        print(f"{C.CY}Processing {post['id']}...{C.N}")

        # Build command to invoke post.sh
        cmd = [
            str(PLATFORMS_DIR / "post.sh"),
            "--text", post["text"],
            "--platforms", ",".join(post["platforms"]),
        ]
        if post.get("media"):
            cmd.extend(["--media", post["media"]])
        if post.get("hashtags"):
            cmd.extend(["--hashtags", ",".join(post["hashtags"])])
        if post.get("first_comment"):
            cmd.extend(["--first-comment", post["first_comment"]])
        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                post["status"] = "posted"
                post["posted_at"] = datetime.now(timezone.utc).isoformat()
                posted += 1
                with LOG_FILE.open("a") as f:
                    f.write(f"[{datetime.now().isoformat()}] POSTED: {post['id']}\n")
                print(f"{C.G}✓{C.N} Posted: {post['id']}")
            else:
                post["status"] = "failed"
                post["error"] = result.stderr[:200]
                failed += 1
                with LOG_FILE.open("a") as f:
                    f.write(f"[{datetime.now().isoformat()}] FAILED: {post['id']} - {result.stderr[:100]}\n")
                print(f"{C.R}✗{C.N} Failed: {post['id']}")
        except subprocess.TimeoutExpired:
            post["status"] = "failed"
            post["error"] = "timeout"
            failed += 1
            print(f"{C.R}✗{C.N} Timeout: {post['id']}")
        except Exception as e:
            post["status"] = "failed"
            post["error"] = str(e)
            failed += 1
            print(f"{C.R}✗{C.N} Error: {post['id']}: {e}")

    # Handle recurring posts: re-schedule them
    for post in cal["posts"]:
        if not post.get("recurring") or post["status"] != "posted":
            continue
        # Create next occurrence
        last = datetime.fromisoformat(post["posted_at"])
        if post["recurring"] == "daily":
            nxt = last + timedelta(days=1)
        elif post["recurring"] == "weekly":
            nxt = last + timedelta(weeks=1)
        elif post["recurring"] == "monthly":
            nxt = last + timedelta(days=30)
        else:
            continue
        new_post = dict(post)
        new_post["id"] = f"cal_{nxt.strftime('%Y%m%d_%H%M%S')}_{len(cal['posts']):03d}"
        new_post["schedule"] = nxt.isoformat()
        new_post["status"] = "scheduled"
        new_post["created"] = datetime.now(timezone.utc).isoformat()
        new_post.pop("posted_at", None)
        new_post.pop("error", None)
        cal["posts"].append(new_post)
        with LOG_FILE.open("a") as f:
            f.write(f"[{datetime.now().isoformat()}] RECUR: {new_post['id']} next={nxt.isoformat()}\n")

    save_calendar(cal)

    print(f"\n{C.CY}{'═' * 40}{C.N}")
    print(f"{C.G}Posted:{C.N} {posted}  {C.R}Failed:{C.N} {failed}")


def view_calendar(days: int = 30) -> None:
    """View calendar in month/week grid format."""
    cal = load_calendar()
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)

    print(f"\n{C.CY}{'═' * 70}{C.N}")
    print(f"{C.CY}  Content Calendar — Next {days} days{C.N}")
    print(f"{C.CY}{'═' * 70}{C.N}\n")

    # Group by date
    by_date = {}
    for p in cal["posts"]:
        if p["status"] not in ("scheduled", "pending"):
            continue
        when = datetime.fromisoformat(p["schedule"])
        if when > horizon:
            continue
        date_key = when.strftime("%Y-%m-%d")
        by_date.setdefault(date_key, []).append((when, p))

    if not by_date:
        print(f"{C.Y}No posts scheduled in the next {days} days.{C.N}")
        return

    for date_key in sorted(by_date.keys()):
        print(f"{C.B}━━━ {date_key} ━━━{C.N}")
        for when, p in sorted(by_date[date_key]):
            time_str = when.strftime("%H:%M")
            platforms = ", ".join(p["platforms"][:3])
            if len(p["platforms"]) > 3:
                platforms += f" +{len(p['platforms']) - 3} more"
            print(f"  {C.Y}{time_str}{C.N}  {p['title'][:40]}")
            print(f"         → {platforms}")
        print()


def export_csv() -> None:
    """Export calendar to CSV."""
    import csv
    cal = load_calendar()
    output = PLATFORMS_DIR / "calendar.csv"
    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "title", "schedule", "status", "platforms", "text", "media", "hashtags"])
        for p in cal["posts"]:
            writer.writerow([
                p["id"],
                p["title"],
                p["schedule"],
                p["status"],
                ",".join(p["platforms"]),
                p["text"],
                p.get("media", ""),
                " ".join("#" + h for h in p.get("hashtags", [])),
            ])
    print(f"{C.G}✓{C.N} Exported to: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Content Calendar & Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", help="Command")

    # add
    add_p = sub.add_parser("add", help="Add a post")
    add_p.add_argument("--text", required=True)
    add_p.add_argument("--platforms", required=True, help="Comma-separated")
    add_p.add_argument("--schedule", default="now", help="ISO 8601 or 'now'")
    add_p.add_argument("--media", default="")
    add_p.add_argument("--hashtags", default="", help="Comma-separated")
    add_p.add_argument("--first-comment", default="")
    add_p.add_argument("--title", default="")
    add_p.add_argument("--recurring", choices=["daily", "weekly", "monthly"])

    # list
    list_p = sub.add_parser("list", help="List posts")
    list_p.add_argument("--all", action="store_true")
    list_p.add_argument("--days", type=int, default=7)

    # view (calendar grid)
    view_p = sub.add_parser("view", help="View calendar grid")
    view_p.add_argument("--days", type=int, default=30)

    # remove
    rm_p = sub.add_parser("remove", help="Remove a post")
    rm_p.add_argument("post_id")

    # process (run due posts)
    proc_p = sub.add_parser("process", help="Process due posts")
    proc_p.add_argument("--dry-run", action="store_true")

    # export
    sub.add_parser("export", help="Export to CSV")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    if args.cmd == "add":
        hashtags = [h.strip() for h in args.hashtags.split(",") if h.strip()] if args.hashtags else []
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
        add_post(
            text=args.text,
            platforms=platforms,
            schedule=args.schedule,
            media=args.media,
            hashtags=hashtags,
            first_comment=args.first_comment,
            recurring=args.recurring,
            title=args.title,
        )
    elif args.cmd == "list":
        list_posts(show_all=args.all, days=args.days)
    elif args.cmd == "view":
        view_calendar(days=args.days)
    elif args.cmd == "remove":
        remove_post(args.post_id)
    elif args.cmd == "process":
        process_due_posts(dry_run=args.dry_run)
    elif args.cmd == "export":
        export_csv()


if __name__ == "__main__":
    main()
