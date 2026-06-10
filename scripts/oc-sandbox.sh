#!/bin/sh
# ── OpenCode Sandbox ───────────────────────────────────────────────
# Docker-based sandboxed execution for untrusted commands.
# Provides isolation, resource limits, and automatic cleanup.
# ───────────────────────────────────────────────────────────────────

IMAGE="alpine:3.20"
WORKSPACE="/home/Codes"
TIMEOUT="${OC_SANDBOX_TIMEOUT:-60}"
MEMORY="${OC_SANDBOX_MEMORY:-512m}"
CPU="${OC_SANDBOX_CPU:-1.0}"
NETWORK="${OC_SANDBOX_NETWORK:-none}"
READ_ONLY="${OC_SANDBOX_READONLY:-true}"

usage() {
    cat << 'USAGE'
Usage: oc-sandbox [options] <command...>

Run a command in an isolated Docker container.

Options:
  --timeout <secs>   Max execution time (default: 60)
  --memory <size>    Memory limit (default: 512m)
  --cpu <cpus>       CPU limit (default: 1.0)
  --network          Enable network access (default: none)
  --read-write       Mount workspace read-write (default: read-only)
  --image <name>     Docker image (default: alpine:3.20)
  --install <pkgs>   APK packages to install (comma-separated)
  --help             Show this help

Examples:
  oc-sandbox ls /
  oc-sandbox --network curl https://example.com
  oc-sandbox --install python3 -- python3 -c "print('hello')"
  oc-sandbox --timeout 10 --memory 256m make build
USAGE
    exit 0
}

# Parse args
INSTALL=""
while [ $# -gt 0 ]; do
    case "$1" in
        --help) usage ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        --memory) MEMORY="$2"; shift 2 ;;
        --cpu) CPU="$2"; shift 2 ;;
        --network) NETWORK="bridge"; shift ;;
        --read-write) READ_ONLY="false"; shift ;;
        --image) IMAGE="$2"; shift 2 ;;
        --install) INSTALL="$2"; shift 2 ;;
        --) shift; break ;;
        *) break ;;
    esac
done

if [ $# -eq 0 ]; then
    echo "Usage: oc-sandbox <command...>"
    echo "Try 'oc-sandbox --help' for more info."
    exit 1
fi

# Build the command to run inside the container
CMD=""
if [ -n "$INSTALL" ]; then
    CMD="apk add --no-cache $INSTALL >/dev/null 2>&1 && "
fi
CMD="$CMD exec \$@"

# Volume mounts
VOLUMES=""
if [ -d "$WORKSPACE" ]; then
    if [ "$READ_ONLY" = "true" ]; then
        VOLUMES="$VOLUMES -v $WORKSPACE:/workspace:ro"
    else
        VOLUMES="$VOLUMES -v $WORKSPACE:/workspace:rw"
    fi
fi
# Always mount config for context access
VOLUMES="$VOLUMES -v /home/.config/opencode:/opencode-config:ro"

echo "[sandbox] Running in Docker container (image: $IMAGE, timeout: ${TIMEOUT}s, memory: $MEMORY, cpu: $CPU, network: $NETWORK)" >&2

docker run --rm \
    --memory "$MEMORY" \
    --cpus "$CPU" \
    --network "$NETWORK" \
    $VOLUMES \
    -w /workspace \
    --stop-timeout "$TIMEOUT" \
    "$IMAGE" \
    sh -c "$CMD" -- "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 124 ]; then
    echo "[sandbox] ⚠️ Command timed out after ${TIMEOUT}s" >&2
elif [ $EXIT_CODE -ne 0 ]; then
    echo "[sandbox] ⚠️ Command exited with code $EXIT_CODE" >&2
else
    echo "[sandbox] ✅ Command completed successfully" >&2
fi

exit $EXIT_CODE
