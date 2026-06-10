#!/bin/bash
# ============================================================
# AGENTS.md Frontmatter (DOX pattern — for AI agents)
# description: Cross-platform posting script for 11 social media platforms
# globs: ["*.sh", "*.json", "tokens/*"]
# lifecycle: post-chat (run after content generation)
# ============================================================
# Cross-Platform Posting Script
# ============================================================
# Publishes content to multiple social media platforms via
# the configured backend (BulkPublish, TryPost, BrightBean, etc.)
#
# Usage:
#   post.sh --text "Hello world" --platforms "twitter,linkedin"
#   post.sh --text "..." --media image.png --schedule "2026-06-08 14:00"
#   cat post.json | post.sh --stdin
# ============================================================

set -e

PLATFORMS_DIR="$HOME/.config/opencode/platforms"
TOKENS_DIR="$PLATFORMS_DIR/tokens"
BACKEND_CONFIG="$PLATFORMS_DIR/backend.json"
ACCOUNTS_CONFIG="$PLATFORMS_DIR/accounts.json"
POSTS_LOG="$PLATFORMS_DIR/posts.jsonl"
HOOKS_DIR="$PLATFORMS_DIR/hooks"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ─────────────────────────────────────────────────────────
# Defaults
# ─────────────────────────────────────────────────────────
TEXT=""
MEDIA=""
PLATFORMS=""
SCHEDULE=""
URL=""
HASHTAGS=""
FIRST_COMMENT=""
BACKEND_OVERRIDE=""
ADAPTER=""
DRY_RUN=false
YES=false
JSON_INPUT=""
LIST_ADAPTERS=false

# ─────────────────────────────────────────────────────────
# Parse arguments
# ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --text)        TEXT="$2"; shift 2 ;;
        --media)       MEDIA="$2"; shift 2 ;;
        --platforms)   PLATFORMS="$2"; shift 2 ;;
        --schedule)    SCHEDULE="$2"; shift 2 ;;
        --url)         URL="$2"; shift 2 ;;
        --hashtags)    HASHTAGS="$2"; shift 2 ;;
        --first-comment) FIRST_COMMENT="$2"; shift 2 ;;
        --backend)     BACKEND_OVERRIDE="$2"; shift 2 ;;
        --adapter)     ADAPTER="$2"; shift 2 ;;
        --list-adapters) LIST_ADAPTERS=true; shift ;;
        --dry-run)     DRY_RUN=true; shift ;;
        --yes)         YES=true; shift ;;
        --stdin)       JSON_INPUT=$(cat); shift ;;
        -h|--help)
            echo "Usage: post.sh [options]"
            echo ""
            echo "Options:"
            echo "  --text         Post text content"
            echo "  --media        Path to image/video file"
            echo "  --platforms    Comma-separated platforms (twitter,linkedin,...)"
            echo "  --schedule     ISO datetime (e.g., '2026-06-08 14:00')"
            echo "  --url          Link to attach"
            echo "  --hashtags     Comma-separated hashtags"
            echo "  --first-comment Comment to post after main content"
            echo "  --backend      Override backend (bulkpublish|trypost|brightbean|mixpost)"
            echo "  --adapter      Use direct platform adapter (bypasses backend)"
            echo "  --list-adapters List available platform adapters"
            echo "  --dry-run      Show what would be posted without actually posting"
            echo "  --yes          Skip confirmation prompt (for automated/batch use)"
            echo "  --stdin        Read post JSON from stdin"
            echo "  -h, --help     Show this help"
            exit 0
            ;;
        *)  echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

# ─────────────────────────────────────────────────────────
# Handle --list-adapters (before backend check)
# ─────────────────────────────────────────────────────────
if [ "$LIST_ADAPTERS" = true ]; then
    echo -e "${CYAN}═══ Available Platform Adapters ═══${NC}"
    PYTHONPATH="$PLATFORMS_DIR:$PYTHONPATH" python3 -c "
import sys
sys.path.insert(0, '$PLATFORMS_DIR')
from adapters import list_adapters
for a in list_adapters():
    print(f\"  {a['platform']:<12} {'✓' if a['has_post'] else '✗'} post  {'✓' if a['has_validate'] else '✗'} validate\")
    if a['description']:
        desc = a['description'].split(chr(10))[0][:80]
        print(f\"  {'':12}{desc}\")
    print()
"
    exit 0
fi

# ─────────────────────────────────────────────────────────
# Validate setup
# ─────────────────────────────────────────────────────────
if [ ! -f "$BACKEND_CONFIG" ]; then
    echo -e "${RED}Error: Backend not configured${NC}"
    echo "Run: ~/.config/opencode/platforms/setup-wizard.sh"
    exit 1
fi

BACKEND=$(python3 -c "import json; print(json.load(open('$BACKEND_CONFIG'))['backend'])" 2>/dev/null)
if [ -z "$BACKEND" ] || [ "$BACKEND" = "none" ]; then
    echo -e "${RED}Error: No backend selected${NC}"
    echo "Run: ~/.config/opencode/platforms/setup-wizard.sh"
    exit 1
fi

# Override backend if specified
[ -n "$BACKEND_OVERRIDE" ] && BACKEND="$BACKEND_OVERRIDE"

# ─────────────────────────────────────────────────────────
# If JSON input, extract fields
# ─────────────────────────────────────────────────────────
if [ -n "$JSON_INPUT" ]; then
    TEXT=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('text',''))")
    MEDIA=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('media',''))")
    PLATFORMS=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(d.get('platforms',[])))")
    SCHEDULE=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('schedule',''))")
    URL=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('url',''))")
    HASHTAGS=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(d.get('hashtags',[])))")
    FIRST_COMMENT=$(echo "$JSON_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('first_comment',''))")
fi

# ─────────────────────────────────────────────────────────
# Validate required fields
# ─────────────────────────────────────────────────────────
if [ -z "$TEXT" ] && [ -z "$MEDIA" ]; then
    echo -e "${RED}Error: Either --text or --media is required${NC}"
    exit 1
fi

if [ -z "$PLATFORMS" ]; then
    echo -e "${RED}Error: --platforms is required (comma-separated)${NC}"
    exit 1
fi

# ─────────────────────────────────────────────────────────
# Print summary
# ─────────────────────────────────────────────────────────
echo -e "${CYAN}═══ Cross-Platform Post ═══${NC}"
echo -e "${BLUE}Backend:${NC} $BACKEND"
echo -e "${BLUE}Platforms:${NC} $PLATFORMS"
[ -n "$SCHEDULE" ] && echo -e "${BLUE}Schedule:${NC} $SCHEDULE" || echo -e "${BLUE}Schedule:${NC} ${GREEN}Now${NC}"
[ -n "$MEDIA" ] && echo -e "${BLUE}Media:${NC} $MEDIA"
[ -n "$URL" ] && echo -e "${BLUE}URL:${NC} $URL"
echo ""
echo -e "${YELLOW}Text:${NC}"
echo "$TEXT" | head -10
[ "$(echo "$TEXT" | wc -l)" -gt 10 ] && echo "..."
echo ""

# ─────────────────────────────────────────────────────────
# Generate post ID
# ─────────────────────────────────────────────────────────
POST_ID="post_$(date +%Y%m%d_%H%M%S)_$(openssl rand -hex 4)"
TIMESTAMP=$(date -Iseconds)

# ─────────────────────────────────────────────────────────
# Build per-platform payloads
# ─────────────────────────────────────────────────────────
build_payload() {
    local platform="$1"
    local platform_text="$TEXT"
    local platform_media="$MEDIA"
    local platform_hashtags=""

    # Add hashtags if provided (format per platform)
    if [ -n "$HASHTAGS" ]; then
        case "$platform" in
            twitter|linkedin|threads|bluesky|mastodon)
                # Inline hashtags
                platform_hashtags=$(echo "$HASHTAGS" | tr ',' ' ')
                platform_text="$platform_text $platform_hashtags"
                ;;
            instagram|tiktok|youtube)
                # Inline for shorter platforms
                platform_hashtags=$(echo "$HASHTAGS" | tr ',' ' ')
                platform_text="$platform_text

$platform_hashtags"
                ;;
            facebook|pinterest|gbp)
                # Comments are better on Facebook/Pinterest
                if [ -z "$FIRST_COMMENT" ]; then
                    FIRST_COMMENT="$platform_hashtags"
                else
                    FIRST_COMMENT="$FIRST_COMMENT

$platform_hashtags"
                fi
                ;;
        esac
    fi

    # Add URL if present
    if [ -n "$URL" ]; then
        platform_text="$platform_text

$URL"
    fi

    # Truncate per platform
    case "$platform" in
        twitter)
            # X has 280 chars
            if [ ${#platform_text} -gt 280 ]; then
                platform_text="${platform_text:0:277}..."
            fi
            ;;
        linkedin)
            # LinkedIn 3000 chars
            if [ ${#platform_text} -gt 3000 ]; then
                platform_text="${platform_text:0:2997}..."
            fi
            ;;
    esac

    # Build JSON payload for this platform
    python3 << EOF
import json
payload = {
    "platform": "$platform",
    "text": """$platform_text""",
    "media": "$platform_media" if "$platform_media" else None,
    "schedule": "$SCHEDULE" if "$SCHEDULE" else None,
    "first_comment": """$FIRST_COMMENT""" if "$FIRST_COMMENT" else None
}
print(json.dumps(payload, ensure_ascii=False))
EOF
}

# ─────────────────────────────────────────────────────────
# Send to backend
# ─────────────────────────────────────────────────────────
send_to_backend() {
    local platform="$1"
    local payload="$2"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}[DRY RUN]${NC} Would post to $platform:"
        echo "$payload" | python3 -m json.tool
        return 0
    fi

    case "$BACKEND" in
        bulkpublish)
            local API_KEY=$(cat "$TOKENS_DIR/bulkpublish_api.key" 2>/dev/null)
            if [ -z "$API_KEY" ]; then
                echo -e "${RED}BulkPublish API key not found${NC}"
                return 1
            fi

            local response=$(curl -s -X POST \
                -H "Authorization: Bearer $API_KEY" \
                -H "Content-Type: application/json" \
                -d "$payload" \
                https://app.bulkpublish.com/api/posts 2>&1)
            ;;
        trypost|brightbean|mixpost)
            local CONFIG_FILE="$PLATFORMS_DIR/${BACKEND}_config.json"
            if [ ! -f "$CONFIG_FILE" ]; then
                echo -e "${RED}$BACKEND not configured${NC}"
                return 1
            fi
            local SERVER_URL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['url'])")
            local API_TOKEN=$(python3 -c "import json; print(open(json.load(open('$CONFIG_FILE'))['token_file']).read().strip())")

            local response=$(curl -s -X POST \
                -H "Authorization: Bearer $API_TOKEN" \
                -H "Content-Type: application/json" \
                -d "$payload" \
                "$SERVER_URL/api/posts" 2>&1)
            ;;
        *)
            echo -e "${RED}Unknown backend: $BACKEND${NC}"
            return 1
            ;;
    esac

    # Log result (structured)
    RESPONSE_OK=$(echo "$response" | grep -qE "(success|posted|scheduled|id)" && echo true || echo false)
    echo "{\"id\":\"$POST_ID\",\"platform\":\"$platform\",\"backend\":\"$BACKEND\",\"timestamp\":\"$TIMESTAMP\",\"success\":$RESPONSE_OK,\"text_length\":${#TEXT},\"has_media\":$([ -n "$MEDIA" ] && echo true || echo false),\"has_url\":$([ -n "$URL" ] && echo true || echo false),\"duration_s\":$SECONDS,\"response\":\"$(echo "$response" | head -c 200)\"}" >> "$POSTS_LOG"

    if echo "$response" | grep -qE "(success|posted|scheduled|id)"; then
        echo -e "${GREEN}✓${NC} $platform: Posted"
        return 0
    else
        echo -e "${RED}✗${NC} $platform: Failed"
        echo "  Response: $(echo "$response" | head -c 200)"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────
# Hook system
# ─────────────────────────────────────────────────────────
run_hook() {
    local hook_name="$1"
    local hook_path="$HOOKS_DIR/$hook_name"
    if [ -f "$hook_path" ] && [ -x "$hook_path" ]; then
        if ! "$hook_path"; then
            echo -e "${RED}[hooks] $hook_name aborted (exit code $?)${NC}"
            return 1
        fi
    fi
    return 0
}

# ─────────────────────────────────────────────────────────
# Security: confirmation prompt for real posts
# ─────────────────────────────────────────────────────────
if [ "$DRY_RUN" = false ] && [ "$YES" = false ]; then
    echo ""
    echo -e "${YELLOW}═══ SECURITY CONFIRMATION ═══${NC}"
    echo -e "${YELLOW}You are about to post:${NC}"
    echo -e "  ${BLUE}Platforms:${NC} $PLATFORMS"
    echo -e "  ${BLUE}Text:${NC}      $(echo "$TEXT" | head -c 100)"
    [ -n "$MEDIA" ] && echo -e "  ${BLUE}Media:${NC}     $MEDIA"
    [ -n "$SCHEDULE" ] && echo -e "  ${BLUE}Schedule:${NC}  $SCHEDULE"
    [ -n "$URL" ] && echo -e "  ${BLUE}URL:${NC}       $URL"
    echo ""
    echo -en "${YELLOW}Proceed? [y/N] ${NC}"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo -e "${RED}Cancelled by user.${NC}"
        exit 0
    fi
    echo ""
fi

# ─────────────────────────────────────────────────────────
# Post to all platforms
# ─────────────────────────────────────────────────────────
SECONDS=0
SUCCESS=0
FAILED=0

IFS=',' read -ra PLATFORM_ARRAY <<< "$PLATFORMS"
for platform in "${PLATFORM_ARRAY[@]}"; do
    platform=$(echo "$platform" | tr -d ' ')
    if [ -z "$platform" ]; then continue; fi

    echo -e "\n${CYAN}Posting to $platform...${NC}"

    # Export hook environment variables
    export PLATFORM="$platform"
    export TEXT
    export MEDIA
    export SCHEDULE
    export URL
    export HASHTAGS
    export DRY_RUN
    export BACKEND

    # Run pre-post hook (can abort this platform)
    if ! run_hook "pre-post.sh"; then
        echo -e "${RED}✗${NC} $platform: Aborted by pre-post hook"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Track per-platform result for post-hook
    PLATFORM_OK=true

    # Use direct adapter if specified, or backend otherwise
    if [ -n "$ADAPTER" ]; then
        # Use adapter system (direct API posting)
        HASHTAGS_JSON=$(python3 -c "import json; print(json.dumps('$HASHTAGS'.split(',') if '$HASHTAGS' else []))" 2>/dev/null)
        if [ "$DRY_RUN" = true ]; then
            PYTHONPATH="$PLATFORMS_DIR:$PYTHONPATH" python3 << EOF
from adapters import post_to_platform
import json
result = post_to_platform(
    platform="$platform",
    text="""$TEXT""",
    media="$MEDIA",
    schedule="$SCHEDULE",
    hashtags=$HASHTAGS_JSON,
    first_comment="""$FIRST_COMMENT""",
    dry_run=True
)
print(json.dumps(result, indent=2))
EOF
            SUCCESS=$((SUCCESS + 1))
        else
            result=$(PYTHONPATH="$PLATFORMS_DIR:$PYTHONPATH" python3 << EOF
from adapters import post_to_platform
import json
result = post_to_platform(
    platform="$platform",
    text="""$TEXT""",
    media="$MEDIA",
    schedule="$SCHEDULE",
    hashtags=$HASHTAGS_JSON,
    first_comment="""$FIRST_COMMENT""",
    dry_run=False
)
print(json.dumps(result))
EOF
)
            if echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('success') else 1)" 2>/dev/null; then
                echo -e "${GREEN}✓${NC} $platform: Posted via adapter"
                SUCCESS=$((SUCCESS + 1))
            else
                echo -e "${RED}✗${NC} $platform: Failed"
                echo "  $result" | python3 -m json.tool 2>/dev/null || echo "  $result"
                FAILED=$((FAILED + 1))
                PLATFORM_OK=false
            fi
        fi
        # Log the post (structured)
        echo "{\"id\":\"$POST_ID\",\"platform\":\"$platform\",\"method\":\"adapter\",\"timestamp\":\"$TIMESTAMP\",\"success\":$([ "$PLATFORM_OK" = true ] && echo true || echo false),\"text_length\":${#TEXT},\"has_media\":$([ -n "$MEDIA" ] && echo true || echo false),\"duration_s\":$SECONDS}" >> "$POSTS_LOG"
    else
        payload=$(build_payload "$platform")
        if send_to_backend "$platform" "$payload"; then
            SUCCESS=$((SUCCESS + 1))
        else
            FAILED=$((FAILED + 1))
            PLATFORM_OK=false
        fi
    fi

    # Run post-post hook (logging, notifications, tracking)
    export POST_ID
    export PLATFORM_OK
    run_hook "post-post.sh" || true
done

# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══ Summary ═══${NC}"
echo -e "${GREEN}Succeeded:${NC} $SUCCESS"
echo -e "${RED}Failed:${NC} $FAILED"
echo -e "${BLUE}Post ID:${NC} $POST_ID"
echo -e "${BLUE}Log:${NC} $POSTS_LOG"

# Track performance
python3 -m opencode_improvement track platform-manager "post_$POST_ID" "Cross-platform post via $BACKEND" --duration 30 2>/dev/null || true

exit $FAILED
