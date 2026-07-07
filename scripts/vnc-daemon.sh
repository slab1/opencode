#!/bin/bash
# OpenCode VNC Daemon
# ====================
# Persistent virtual display (Xvfb) + VNC (x11vnc) + window manager (fluxbox)
# that survives bash command timeouts by using nohup and proper disown.
#
# Usage:
#   ./vnc-daemon.sh start    # Start display :99 + VNC on port 5900
#   ./vnc-daemon.sh stop     # Kill all VNC daemon processes
#   ./vnc-daemon.sh status   # Check if daemon is running
#   ./vnc-daemon.sh restart  # Restart the daemon
#
# VNC password: opencode (configurable via VNC_PASSWORD env var)

DISPLAY_NUM="${DISPLAY_NUM:-99}"
RESOLUTION="${RESOLUTION:-1920x1080x24}"
VNC_PORT="${VNC_PORT:-5900}"
VNC_PASSWORD="${VNC_PASSWORD:-opencode}"
PID_DIR="${PID_DIR:-/tmp/opencode-vnc}"
LOG_DIR="${LOG_DIR:-/tmp/opencode-vnc}"

mkdir -p "$PID_DIR" "$LOG_DIR"

XVFB_PIDFILE="$PID_DIR/xvfb.pid"
FLUXBOX_PIDFILE="$PID_DIR/fluxbox.pid"
X11VNC_PIDFILE="$PID_DIR/x11vnc.pid"
VNC_PASSFILE="/tmp/.opencode_vnc_pass"

DISPLAY=":$DISPLAY_NUM"

start() {
    echo "Starting OpenCode VNC daemon on display $DISPLAY (port $VNC_PORT)..."

    if [ -f "$XVFB_PIDFILE" ] && kill -0 "$(cat "$XVFB_PIDFILE")" 2>/dev/null; then
        echo "VNC daemon is already running. Use 'restart' or 'stop' first."
        return 1
    fi

    rm -f "/tmp/.X${DISPLAY_NUM}-lock"
    rm -f "/tmp/.X11-unix/X${DISPLAY_NUM}"

    nohup Xvfb "$DISPLAY" \
        -screen "0" "$RESOLUTION" \
        -ac \
        -nolisten tcp \
        > "$LOG_DIR/xvfb.log" 2>&1 &
    XVFB_PID=$!
    echo "$XVFB_PID" > "$XVFB_PIDFILE"
    echo "  Xvfb started (PID: $XVFB_PID)"

    for i in $(seq 1 10); do
        if [ -e "/tmp/.X11-unix/X${DISPLAY_NUM}" ]; then
            break
        fi
        sleep 0.5
    done

    if ! xdpyinfo -display "$DISPLAY" > /dev/null 2>&1; then
        echo "  ERROR: Xvfb failed to start (check $LOG_DIR/xvfb.log)"
        kill "$XVFB_PID" 2>/dev/null
        rm -f "$XVFB_PIDFILE"
        return 1
    fi
    echo "  Xvfb ready: $RESOLUTION"

    DISPLAY="$DISPLAY" nohup fluxbox \
        > "$LOG_DIR/fluxbox.log" 2>&1 &
    FLUXBOX_PID=$!
    echo "$FLUXBOX_PID" > "$FLUXBOX_PIDFILE"
    echo "  fluxbox started (PID: $FLUXBOX_PID)"

    sleep 0.5

    echo "$VNC_PASSWORD" > "$VNC_PASSFILE"

    nohup x11vnc \
        -display "$DISPLAY" \
        -forever \
        -shared \
        -noshm \
        -rfbport "$VNC_PORT" \
        -passwd "$VNC_PASSWORD" \
        -quiet \
        > "$LOG_DIR/x11vnc.log" 2>&1 &
    X11VNC_PID=$!
    echo "$X11VNC_PID" > "$X11VNC_PIDFILE"
    echo "  x11vnc started (PID: $X11VNC_PID, port: $VNC_PORT)"

    export DISPLAY="$DISPLAY"

    echo ""
    echo "VNC daemon is running:"
    echo "  Display: $DISPLAY"
    echo "  VNC:     localhost:${VNC_PORT}"
    echo "  VNC URL: vnc://localhost:${VNC_PORT}"
    echo "  Password: $VNC_PASSWORD"
    echo "  Connect:  vncviewer localhost:$((VNC_PORT - 5900))"
    return 0
}

stop() {
    echo "Stopping OpenCode VNC daemon..."

    for pidfile in "$X11VNC_PIDFILE" "$FLUXBOX_PIDFILE" "$XVFB_PIDFILE"; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile" 2>/dev/null)
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                echo "  Killing PID $pid (${pidfile##*/})"
                kill "$pid" 2>/dev/null
                sleep 0.3
                kill -9 "$pid" 2>/dev/null
            fi
            rm -f "$pidfile"
        fi
    done

    pkill -9 -f "Xvfb $DISPLAY" 2>/dev/null || true
    pkill -9 -f "x11vnc.*$DISPLAY" 2>/dev/null || true
    pkill -9 -f "fluxbox" 2>/dev/null || true

    rm -f "/tmp/.X${DISPLAY_NUM}-lock"
    rm -f "/tmp/.X11-unix/X${DISPLAY_NUM}"
    rm -f "$VNC_PASSFILE"

    echo "  VNC daemon stopped"
    return 0
}

status() {
    xvfb_running=false
    fluxbox_running=false
    x11vnc_running=false

    if [ -f "$XVFB_PIDFILE" ]; then
        pid=$(cat "$XVFB_PIDFILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            xvfb_running=true
        fi
    fi

    if [ -f "$FLUXBOX_PIDFILE" ]; then
        pid=$(cat "$FLUXBOX_PIDFILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            fluxbox_running=true
        fi
    fi

    if [ -f "$X11VNC_PIDFILE" ]; then
        pid=$(cat "$X11VNC_PIDFILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            x11vnc_running=true
        fi
    fi

    if ! $xvfb_running && pgrep -f "Xvfb $DISPLAY" > /dev/null 2>&1; then
        xvfb_running=true
        pgrep -f "Xvfb $DISPLAY" | head -1 > "$XVFB_PIDFILE"
    fi
    if ! $x11vnc_running && pgrep -f "x11vnc.*$DISPLAY" > /dev/null 2>&1; then
        x11vnc_running=true
        pgrep -f "x11vnc.*$DISPLAY" | head -1 > "$X11VNC_PIDFILE"
    fi

    echo "OpenCode VNC Daemon Status:"
    echo "  Display:  $DISPLAY ($RESOLUTION)"
    echo "  Port:     $VNC_PORT"
    echo "  Password: $VNC_PASSWORD"
    echo ""
    echo "  Xvfb:    $([ "$xvfb_running" = true ] && echo 'RUNNING' || echo 'STOPPED')"
    echo "  fluxbox: $([ "$fluxbox_running" = true ] && echo 'RUNNING' || echo 'STOPPED')"
    echo "  x11vnc:  $([ "$x11vnc_running" = true ] && echo 'RUNNING' || echo 'STOPPED')"
    echo ""

    if $xvfb_running && $x11vnc_running; then
        echo "  VNC is available at: localhost:${VNC_PORT}"
        echo "  Connect: vncviewer localhost:$((VNC_PORT - 5900))"
        return 0
    else
        echo "  VNC daemon is NOT fully running."
        return 1
    fi
}

case "${1:-status}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
