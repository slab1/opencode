#!/usr/bin/env python3
"""
oc-monitor — Live Terminal Dashboard (like htop for OpenCode)
─────────────────────────────────────────────────────────────
Displays real-time system metrics, OpenCode server status,
agent pool health, and shared context info.
Ref: TOOLS_MANIFEST.md, ULTIMATE_PLAN.md
"""

import os
import sys
import time
import json
import signal
import subprocess
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────────

REFRESH_INTERVAL = 2.0  # seconds
CONFIG_DIR = Path(os.path.expanduser("~/.config/opencode"))
SHARED_CONTEXT = CONFIG_DIR / "shared" / "context.json"
OPCODE_BIN = Path(os.path.expanduser("~/.opencode/bin/opencode"))

# ── ANSI helpers ────────────────────────────────────────────────────────

class Style:
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    REVERSE  = "\033[7m"
    # Foreground
    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    # Background
    BG_BLUE  = "\033[44m"
    BG_GRAY  = "\033[100m"
    # Clear
    CLS      = "\033[2J\033[H"
    CLEAR_LINE = "\033[2K\r"

# ── Data collectors ─────────────────────────────────────────────────────

def get_cpu_percent():
    """Read CPU usage from /proc/stat (differential)."""
    try:
        with open("/proc/stat") as f:
            line = f.readline()
        parts = line.split()
        # user nice system idle iowait irq softirq steal guest guest_nice
        vals = [int(v) for v in parts[1:]]
        return vals  # raw ticks
    except Exception:
        return None

def format_cpu(old, new):
    """Compute delta CPU usage percentage."""
    if not old or not new:
        return "N/A"
    old_idle = old[3] + old[4]  # idle + iowait
    new_idle = new[3] + new[4]
    old_total = sum(old[:8])
    new_total = sum(new[:8])
    delta_idle = new_idle - old_idle
    delta_total = new_total - old_total
    if delta_total == 0:
        return "0%"
    usage = 100.0 * (1.0 - delta_idle / delta_total)
    return f"{usage:.1f}%"

def get_memory():
    """Read memory info from /proc/meminfo."""
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                mem[k.strip()] = int(v.strip().split()[0])  # kB
        total = mem.get("MemTotal", 0)
        avail = mem.get("MemAvailable", 0)
        used = total - avail
        pct = (used / total * 100) if total else 0
        return {
            "total_gb": total / 1024 / 1024,
            "used_gb": used / 1024 / 1024,
            "pct": pct,
        }
    except Exception:
        return None

def get_uptime():
    """Read system uptime."""
    try:
        with open("/proc/uptime") as f:
            secs = float(f.readline().split()[0])
        days = int(secs // 86400)
        hours = int((secs % 86400) // 3600)
        mins = int((secs % 3600) // 60)
        return f"{days}d {hours}h {mins}m"
    except Exception:
        return "N/A"

def get_load_avg():
    """Read load averages."""
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().strip().split()
        return f"{parts[0]} {parts[1]} {parts[2]}"
    except Exception:
        return "N/A"

def get_opencode_process():
    """Check if opencode server process is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "opencode serve"],
            capture_output=True, text=True, timeout=3
        )
        pids = result.stdout.strip().split("\n")
        pids = [p for p in pids if p]
        return pids if pids else []
    except Exception:
        return []

def get_shared_context():
    """Read shared context.json for key metrics."""
    try:
        with open(SHARED_CONTEXT) as f:
            ctx = json.load(f)
        return ctx
    except Exception:
        return None

def get_disk_usage():
    """Get disk usage for home partition."""
    try:
        st = os.statvfs("/home")
        total = st.f_frsize * st.f_blocks
        free = st.f_frsize * st.f_bfree
        used = total - free
        pct = (used / total * 100) if total else 0
        return {
            "total_gb": total / (1024**3),
            "used_gb": used / (1024**3),
            "pct": pct,
        }
    except Exception:
        return None

def get_agent_pool(ctx):
    """Extract agent info from shared context."""
    if not ctx:
        return {}
    findings = ctx.get("findings", {})
    agents = {}
    for key in findings:
        agent_name = key.split(".")[-1] if "." in key else key
        agents[agent_name] = len(findings[key])
    return agents

# ── Renderer ────────────────────────────────────────────────────────────

def draw_bar(pct, width=10):
    """Draw a colored progress bar."""
    filled = int(pct / 100 * width)
    filled = max(0, min(filled, width))
    empty = width - filled
    color = Style.GREEN if pct < 50 else (Style.YELLOW if pct < 80 else Style.RED)
    return f"{color}{'█' * filled}{Style.DIM}{'░' * empty}{Style.RESET}"

def render(cpu_old):
    """Render one frame of the dashboard."""

    lines = []

    # ── Header ──
    lines.append(f"{Style.BG_BLUE}{Style.WHITE}{Style.BOLD}  OpenCode Agent Monitor  {Style.RESET}   {Style.DIM}[q: quit]  [r: refresh]{Style.RESET}")
    lines.append("")

    # ── System Section ──
    cpu_new = get_cpu_percent()
    cpu_str = format_cpu(cpu_old, cpu_new)
    mem = get_memory()
    load = get_load_avg()
    uptime = get_uptime()
    disk = get_disk_usage()

    lines.append(f"{Style.BOLD}System{Style.RESET}")
    lines.append(f"  CPU:    {cpu_str:>8}  {draw_bar(float(cpu_str.rstrip('%')) if cpu_str != 'N/A' else 0)}")
    if mem:
        lines.append(f"  Mem:    {mem['used_gb']:.1f}/{mem['total_gb']:.1f} GB {mem['pct']:.0f}%  {draw_bar(mem['pct'])}")
    if disk:
        lines.append(f"  Disk:   {disk['used_gb']:.1f}/{disk['total_gb']:.1f} GB {disk['pct']:.0f}%  {draw_bar(disk['pct'])}")
    lines.append(f"  Load:   {load}")
    lines.append(f"  Uptime: {uptime}")
    lines.append("")

    # ── OpenCode Section ──
    pids = get_opencode_process()
    ctx = get_shared_context()

    lines.append(f"{Style.BOLD}OpenCode{Style.RESET}")
    server_status = f"{Style.GREEN}● Running{Style.RESET} (PID: {', '.join(pids)})" if pids else f"{Style.RED}● Stopped{Style.RESET}"
    lines.append(f"  Server: {server_status}")

    bin_exists = OPCODE_BIN.exists()
    bin_ver = f"{Style.GREEN}v{os.path.getsize(OPCODE_BIN) >> 20}MB{Style.RESET}" if bin_exists else f"{Style.RED}not found{Style.RESET}"
    lines.append(f"  Binary: {bin_ver}")

    if ctx:
        wf_trace = ctx.get("workflow_trace", [])
        wf_count = len(wf_trace)
        lines.append(f"  Workflows: {wf_count}")
        if wf_trace:
            last = wf_trace[-1]
            lines.append(f"  Last:    {last.get('agent','?')} — {Style.DIM}{last.get('timestamp','?')[:19]}{Style.RESET}")
    else:
        lines.append(f"  Shared Context: {Style.YELLOW}unavailable{Style.RESET}")
    lines.append("")

    # ── Agent Pool ──
    agents = get_agent_pool(ctx)
    if agents:
        lines.append(f"{Style.BOLD}Agent Findings{Style.RESET}")
        # Sort by finding count (most active first)
        sorted_agents = sorted(agents.items(), key=lambda x: -x[1])
        for name, count in sorted_agents:
            bar = "█" * min(count, 10) + "░" * max(0, 10 - min(count, 10))
            lines.append(f"  {name:16s} {Style.DIM}{count} findings{Style.RESET}  {Style.CYAN}{bar}{Style.RESET}")
        lines.append("")

    # ── Footer ──
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"{Style.DIM}Last updated: {ts}{Style.RESET}")

    return "\n".join(lines), cpu_new

# ── Main Loop ───────────────────────────────────────────────────────────

def main():
    # Ignore SIGINT (Ctrl+C) gracefully
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))

    cpu_old = get_cpu_percent()
    time.sleep(0.2)  # small initial delta

    # Check if we have a TTY
    is_tty = sys.stdout.isatty()

    try:
        while True:
            output, cpu_old = render(cpu_old)

            if is_tty:
                # Clear screen and home cursor
                sys.stdout.write(Style.CLS)
            else:
                # Non-TTY: just write separator
                sys.stdout.write("\n" + "=" * 50 + "\n")

            sys.stdout.write(output)
            sys.stdout.flush()

            if not is_tty:
                # Non-interactive: print once and exit
                break

            # Wait for keypress or timeout
            try:
                import select
                import tty
                import termios

                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                tty.setraw(fd)
                readable, _, _ = select.select([sys.stdin], [], [], REFRESH_INTERVAL)
                if readable:
                    key = sys.stdin.read(1)
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
                    if key.lower() == "q":
                        break
                    # 'r' forces immediate refresh (do nothing, loop continues)
                else:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except (ImportError, AttributeError, OSError):
                # Fallback: no raw input available, just sleep
                time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        # Clean up terminal
        sys.stdout.write(Style.RESET + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
