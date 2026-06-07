#!/bin/bash
# oc-memory — memory health check for Android/Linux terminals
ACTION="${1:-status}"

case "$ACTION" in
  status)
    mem_total=$(awk '/MemTotal:/{print $2}' /proc/meminfo)
    mem_avail=$(awk '/MemAvailable:/{print $2}' /proc/meminfo)
    cached=$(awk '/^Cached:/{print $2}' /proc/meminfo)
    swap_total=$(awk '/SwapTotal:/{print $2}' /proc/meminfo)
    swap_free=$(awk '/SwapFree:/{print $2}' /proc/meminfo)
    avail_mb=$((mem_avail / 1024))
    total_mb=$((mem_total / 1024))
    cached_mb=$((cached / 1024))
    swap_total_mb=$((swap_total / 1024))
    swap_used_mb=$(( (swap_total - swap_free) / 1024 ))
    pct=$(( (mem_total - mem_avail) * 100 / mem_total ))
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Memory Health Check"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    printf "  Total:     %4d MB\n" "$total_mb"
    printf "  Available: %4d MB (%d%%)\n" "$avail_mb" "$pct"
    printf "  Cached:    %4d MB\n" "$cached_mb"
    printf "  Swap:      %4d MB used / %d MB total\n" "$swap_used_mb" "$swap_total_mb"
    if [ "$avail_mb" -lt 100 ]; then
      echo "  ⚠️  CRITICAL: <100 MB available — OOM risk!"
      echo "  → Run: oc-memory drop-caches"
    elif [ "$avail_mb" -lt 300 ]; then
      echo "  ⚡ LOW: <300 MB available — proceed with caution"
    else
      echo "  ✅ HEALTHY: sufficient memory"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ;;
  drop-caches|free)
    echo "Dropping page cache..."
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null && echo "✅ Cache dropped" || echo "❌ Permission denied"
    ;;
  top)
    echo "━━━ Top memory consumers ━━━"
    for pid in /proc/[0-9]*; do
      pid="${pid#/proc/}"
      comm=$(cat /proc/$pid/comm 2>/dev/null)
      rss=$(cat /proc/$pid/status 2>/dev/null | awk '/VmRSS:/{print $2}')
      [ -n "$rss" ] && echo "  $pid: $((rss/1024)) MB  $comm"
    done | sort -rn -k2 | head -10
    ;;
  guard)
    avail_mb=$(( $(awk '/MemAvailable:/{print $2}' /proc/meminfo) / 1024 ))
    if [ "$avail_mb" -lt 100 ]; then
      echo "⚠️  Memory critical ($avail_mb MB free). Dropping caches..."
      echo 3 > /proc/sys/vm/drop_caches 2>/dev/null
      sleep 1
      avail_mb=$(( $(awk '/MemAvailable:/{print $2}' /proc/meminfo) / 1024 ))
      if [ "$avail_mb" -lt 100 ]; then
        echo "❌ Cancel: only ${avail_mb}MB available even after dropping caches"
        exit 1
      fi
    fi
    echo "✅ ${avail_mb}MB available — proceeding"
    ;;
  *)
    echo "Usage: oc-memory [status|drop-caches|top|guard]"
    ;;
esac
