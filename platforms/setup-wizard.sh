#!/bin/bash
# ============================================================
# Platform Account Setup Wizard
# ============================================================
# Interactive wizard to set up social media accounts
# and connect them to the OpenCode platform manager.
# ============================================================

set -e

PLATFORMS_DIR="$HOME/.config/opencode/platforms"
TOKENS_DIR="$PLATFORMS_DIR/tokens"
CONFIG_FILE="$PLATFORMS_DIR/accounts.json"
mkdir -p "$PLATFORMS_DIR" "$TOKENS_DIR"
chmod 700 "$TOKENS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# ASCII Art Banner
echo -e "${MAGENTA}"
cat << 'BANNER'
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        🌐  PLATFORM MANAGER SETUP WIZARD  🌐             ║
║                                                           ║
║   Set up and manage ALL your social media accounts        ║
║   in one place. 100% FREE, self-hosted, no limits.       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
BANNER
echo -e "${NC}"
echo ""

# ─────────────────────────────────────────────────────────
# Platform definitions
# ─────────────────────────────────────────────────────────
declare -A PLATFORMS
PLATFORMS[facebook]="Facebook (Pages)|https://business.facebook.com|https://developers.facebook.com"
PLATFORMS[instagram]="Instagram (Business)|https://business.instagram.com|https://developers.facebook.com"
PLATFORMS[twitter]="X (Twitter)|https://twitter.com/signup|https://developer.twitter.com"
PLATFORMS[tiktok]="TikTok (Business)|https://www.tiktok.com/signup|https://developers.tiktok.com"
PLATFORMS[youtube]="YouTube|https://www.youtube.com/create_channel|https://console.cloud.google.com"
PLATFORMS[linkedin]="LinkedIn (Pages)|https://www.linkedin.com/signup|https://www.linkedin.com/developers"
PLATFORMS[pinterest]="Pinterest (Business)|https://business.pinterest.com|https://developers.pinterest.com"
PLATFORMS[threads]="Threads|https://www.threads.net|https://developers.facebook.com"
PLATFORMS[bluesky]="Bluesky|https://bsky.app|https://docs.bsky.app"
PLATFORMS[mastodon]="Mastodon|https://joinmastodon.org|https://docs.joinmastodon.org"
PLATFORMS[gbp]="Google Business Profile|https://business.google.com|https://console.cloud.google.com"

# ─────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────
print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}▶${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${RED}⚠${NC} $1"
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    while true; do
        if [ "$default" = "y" ]; then
            read -p "$(echo -e ${YELLOW}"$prompt [Y/n]: "${NC})" answer
            answer="${answer:-y}"
        else
            read -p "$(echo -e ${YELLOW}"$prompt [y/N]: "${NC})" answer
            answer="${answer:-n}"
        fi
        case "$answer" in
            y|Y|yes|YES) return 0 ;;
            n|N|no|NO) return 1 ;;
            *) echo "Please answer yes or no" ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────
# Step 1: Welcome & Platform Selection
# ─────────────────────────────────────────────────────────
print_header "STEP 1: Choose Your Platforms"

echo "Select which platforms you want to set up:"
echo ""

SELECTED=()
for key in facebook instagram twitter tiktok youtube linkedin pinterest threads bluesky mastodon gbp; do
    IFS='|' read -r name signup dev <<< "${PLATFORMS[$key]}"
    if ask_yes_no "Set up ${name}?"; then
        SELECTED+=("$key")
        print_success "Added: $name"
    fi
done

if [ ${#SELECTED[@]} -eq 0 ]; then
    echo ""
    print_warning "No platforms selected. Exiting."
    exit 0
fi

echo ""
echo -e "${GREEN}Selected ${#SELECTED[@]} platform(s):${NC}"
for key in "${SELECTED[@]}"; do
    IFS='|' read -r name _ _ <<< "${PLATFORMS[$key]}"
    echo "  • $name"
done

# ─────────────────────────────────────────────────────────
# Step 2: Account Creation Helper
# ─────────────────────────────────────────────────────────
print_header "STEP 2: Create Accounts (if needed)"

echo "For each platform, we need to verify you have an account."
echo "If you don't have one yet, follow the links to create one."
echo ""

for key in "${SELECTED[@]}"; do
    IFS='|' read -r name signup dev <<< "${PLATFORMS[$key]}"
    echo -e "${BLUE}━━━ $name ━━━${NC}"
    echo ""
    echo "  📝 Create account:  $signup"
    echo "  🔑 Developer portal: $dev"
    echo ""

    if ask_yes_no "Do you already have a $name account?" "y"; then
        print_success "$name: Account exists"
    else
        echo ""
        echo -e "${YELLOW}Please create an account first:${NC}"
        echo "  1. Open: $signup"
        echo "  2. Sign up for a business/creator account"
        echo "  3. Verify your email/phone"
        echo "  4. Return here when done"
        echo ""
        read -p "Press Enter when you've created your account..."
        print_success "$name: Account created"
    fi
    echo ""
done

# ─────────────────────────────────────────────────────────
# Step 3: API Credentials
# ─────────────────────────────────────────────────────────
print_header "STEP 3: Get API Credentials"

echo "Each platform requires API credentials to post automatically."
echo "We'll guide you through getting them."
echo ""

# Initialize credentials JSON
echo "{" > "$CONFIG_FILE"
echo '  "version": "1.0",' >> "$CONFIG_FILE"
echo '  "created": "'"$(date -Iseconds)"'",' >> "$CONFIG_FILE"
echo '  "accounts": {' >> "$CONFIG_FILE"

first=true

for key in "${SELECTED[@]}"; do
    IFS='|' read -r name signup dev <<< "${PLATFORMS[$key]}"

    echo -e "${BLUE}━━━ $name API Setup ━━━${NC}"
    echo ""
    echo "  Steps to get API credentials:"
    echo "  1. Go to: $dev"
    echo "  2. Create a new app/project"
    echo "  3. Get your API key/Client ID/Client Secret"
    echo "  4. Set redirect URI: ${YELLOW}http://localhost:8888/callback${NC}"
    echo "  5. Copy the credentials below"
    echo ""

    case "$key" in
        facebook|instagram|threads)
            echo "  For Facebook/Instagram/Threads, you need:"
            echo "    - App ID"
            echo "    - App Secret"
            echo "    - Page ID (for Facebook Pages)"
            echo "    - Instagram Business Account ID"
            ;;
        twitter)
            echo "  For X (Twitter), you need:"
            echo "    - API Key (Consumer Key)"
            echo "    - API Secret (Consumer Secret)"
            echo "    - Bearer Token"
            echo "    - Access Token"
            echo "    - Access Token Secret"
            ;;
        tiktok)
            echo "  For TikTok, you need:"
            echo "    - Client Key"
            echo "    - Client Secret"
            echo "    - Open ID"
            ;;
        youtube|gbp)
            echo "  For YouTube/Google, you need:"
            echo "    - OAuth 2.0 Client ID"
            echo "    - OAuth 2.0 Client Secret"
            echo "    - Refresh Token (we'll help you get this)"
            ;;
        linkedin)
            echo "  For LinkedIn, you need:"
            echo "    - Client ID"
            echo "    - Client Secret"
            echo "    - Page/Organization URN"
            ;;
        pinterest)
            echo "  For Pinterest, you need:"
            echo "    - App ID"
            echo "    - App Secret"
            echo "    - Refresh Token"
            ;;
        bluesky)
            echo "  For Bluesky, you need:"
            echo "    - Handle (e.g., user.bsky.social)"
            echo "    - App Password (not your main password!)"
            echo ""
            echo -e "  ${GREEN}Tip:${NC} Go to Settings → App Passwords → Add App Password"
            ;;
        mastodon)
            echo "  For Mastodon, you need:"
            echo "    - Instance URL (e.g., mastodon.social)"
            echo "    - Access Token"
            echo ""
            echo "  Get token: Settings → Development → New Application"
            ;;
    esac
    echo ""

    # Collect credentials
    echo "  Paste your credentials (or press Enter to skip):"
    echo ""

    declare -A creds

    if [ "$key" = "bluesky" ] || [ "$key" = "mastodon" ]; then
        read -p "  Handle/Instance: " creds[handle]
        read -sp "  App Password/Token: " creds[password]
        echo ""
    else
        read -p "  Client ID / API Key: " creds[client_id]
        read -sp "  Client Secret / API Secret: " creds[client_secret]
        echo ""
        read -p "  Access Token (if already have): " creds[access_token]
    fi

    # Save to config
    if [ "$first" = false ]; then
        echo "," >> "$CONFIG_FILE"
    fi
    first=false

    echo -n "    \"$key\": {" >> "$CONFIG_FILE"
    echo -n "\"name\": \"$name\", " >> "$CONFIG_FILE"
    echo -n "\"status\": \"configured\", " >> "$CONFIG_FILE"
    echo -n "\"credentials\": {" >> "$CONFIG_FILE"

    cred_count=0
    for cred_key in "${!creds[@]}"; do
        if [ -n "${creds[$cred_key]}" ]; then
            if [ $cred_count -gt 0 ]; then
                echo -n ", " >> "$CONFIG_FILE"
            fi
            # Store token in separate file for security
            token_file="$TOKENS_DIR/${key}_${cred_key}.token"
            echo -n "${creds[$cred_key]}" > "$token_file"
            chmod 600 "$token_file"
            echo -n "\"$cred_key\": \"file:$token_file\"" >> "$CONFIG_FILE"
            cred_count=$((cred_count + 1))
        fi
    done

    echo -n "}" >> "$CONFIG_FILE"
    echo -n "}" >> "$CONFIG_FILE"

    print_success "$name: Credentials saved"
    echo ""
done

echo "  }" >> "$CONFIG_FILE"
echo "}" >> "$CONFIG_FILE"

# ─────────────────────────────────────────────────────────
# Step 4: Choose Scheduling Backend
# ─────────────────────────────────────────────────────────
print_header "STEP 4: Choose Scheduling Backend"

echo "You need a backend to actually publish posts. Choose one:"
echo ""
echo "  1) ${GREEN}BulkPublish API${NC} (recommended) - Free cloud, 100 req/day, MCP server"
echo "  2) ${BLUE}TryPost${NC} (self-hosted) - Free, open-source, MCP server"
echo "  3) ${BLUE}BrightBean Studio${NC} (self-hosted) - Django, multi-tenant"
echo "  4) ${BLUE}Mixpost${NC} (paid once \$79) - Most mature, unlimited"
echo "  5) Skip for now - I'll set this up later"
echo ""

read -p "Choose [1-5]: " backend_choice

case "$backend_choice" in
    1)
        BACKEND="bulkpublish"
        echo ""
        echo "  To use BulkPublish:"
        echo "  1. Sign up free at: ${YELLOW}https://app.bulkpublish.com${NC}"
        echo "  2. Get your API key from Settings"
        echo "  3. Connect your accounts in the dashboard"
        echo ""
        read -p "  Paste your BulkPublish API key: " bp_key
        if [ -n "$bp_key" ]; then
            echo "$bp_key" > "$TOKENS_DIR/bulkpublish_api.key"
            chmod 600 "$TOKENS_DIR/bulkpublish_api.key"
            print_success "BulkPublish API key saved"
        fi
        ;;
    2)
        BACKEND="trypost"
        echo ""
        echo "  TryPost setup:"
        echo "  1. Visit: ${YELLOW}https://github.com/trypostit/trypost${NC}"
        echo "  2. Follow installation instructions"
        echo "  3. Get your MCP server URL"
        echo ""
        echo "  Quick install with Docker:"
        echo "  ${YELLOW}docker run -d -p 3000:3000 trypost/trypost${NC}"
        ;;
    3)
        BACKEND="brightbean"
        echo ""
        echo "  BrightBean Studio setup:"
        echo "  1. Visit: ${YELLOW}https://github.com/brightbeanxyz/brightbean-studio${NC}"
        echo "  2. Deploy with one click on Heroku/Render/Railway"
        echo "  3. Or run locally with Docker"
        ;;
    4)
        BACKEND="mixpost"
        echo ""
        echo "  Mixpost setup:"
        echo "  1. Visit: ${YELLOW}https://mixpost.app/${NC}"
        echo "  2. Purchase license (\$79 one-time)"
        echo "  3. Follow Laravel installation"
        ;;
    5)
        BACKEND="none"
        echo ""
        echo "  You can set up the backend later by running:"
        echo "  ${YELLOW}~/.config/opencode/platforms/setup-scheduler.sh${NC}"
        ;;
esac

# Save backend choice
echo "{\"backend\": \"$BACKEND\", \"configured\": \"$(date -Iseconds)\"}" > "$PLATFORMS_DIR/backend.json"

# ─────────────────────────────────────────────────────────
# Step 5: Test Connections
# ─────────────────────────────────────────────────────────
print_header "STEP 5: Test Connections"

if [ "$BACKEND" != "none" ] && ask_yes_no "Test connections now?" "y"; then
    echo ""
    echo "Testing connections..."
    echo ""

    case "$BACKEND" in
        bulkpublish)
            API_KEY=$(cat "$TOKENS_DIR/bulkpublish_api.key" 2>/dev/null)
            if [ -n "$API_KEY" ]; then
                response=$(curl -s -H "Authorization: Bearer $API_KEY" \
                    https://app.bulkpublish.com/api/channels 2>/dev/null || echo "failed")
                if echo "$response" | grep -q "data"; then
                    print_success "BulkPublish API: Connected"
                    print_success "Channels: $(echo "$response" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo "0")"
                else
                    print_warning "BulkPublish: Could not verify (may need to connect accounts in dashboard)"
                fi
            fi
            ;;
        trypost|brightbean|mixpost)
            read -p "Enter your server URL (e.g., http://localhost:3000): " server_url
            echo ""
            read -p "Enter API key/token: " api_token
            echo ""

            if [ -n "$server_url" ] && [ -n "$api_token" ]; then
                echo "$api_token" > "$TOKENS_DIR/${BACKEND}_api.token"
                chmod 600 "$TOKENS_DIR/${BACKEND}_api.token"
                echo "{\"url\": \"$server_url\", \"token_file\": \"$TOKENS_DIR/${BACKEND}_api.token\"}" > "$PLATFORMS_DIR/${BACKEND}_config.json"
                print_success "$BACKEND configured"
            fi
            ;;
    esac
fi

# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
print_header "✅ SETUP COMPLETE!"

echo -e "${GREEN}Your platform manager is configured!${NC}"
echo ""
echo -e "${BLUE}Platforms configured:${NC} ${#SELECTED[@]}"
for key in "${SELECTED[@]}"; do
    IFS='|' read -r name _ _ <<< "${PLATFORMS[$key]}"
    echo "  ✓ $name"
done
echo ""
echo -e "${BLUE}Backend:${NC} $BACKEND"
echo ""
echo -e "${YELLOW}Files created:${NC}"
echo "  • $CONFIG_FILE (account registry)"
echo "  • $TOKENS_DIR/ (API tokens, chmod 600)"
echo "  • $PLATFORMS_DIR/backend.json (backend config)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. ${GREEN}Generate content:${NC}"
echo "     ~/.config/opencode/scripts/start-free-api.sh"
echo ""
echo "  2. ${GREEN}Test posting:${NC}"
echo "     Run the platform-manager agent and ask to post a test"
echo ""
echo "  3. ${GREEN}Schedule content:${NC}"
echo "     Use the content calendar in your chosen backend"
echo ""
echo ""
echo -e "${YELLOW}Available tools:${NC}"
echo "  • ${GREEN}post.sh${NC} - Cross-platform posting script"
echo "    Usage: ~/.config/opencode/platforms/post.sh --text \"...\" --platforms twitter,linkedin"
echo ""
echo "  • ${GREEN}calendar.py${NC} - Content calendar & scheduler"
echo "    Usage: python3 ~/.config/opencode/platforms/calendar.py add --text \"...\" --platforms twitter --schedule \"2026-06-08 14:00\""
echo "           python3 ~/.config/opencode/platforms/calendar.py process  (run due posts)"
echo "           python3 ~/.config/opencode/platforms/calendar.py view     (calendar grid)"
echo ""
echo "  • ${GREEN}analytics.py${NC} - Cross-platform analytics"
echo "    Usage: python3 ~/.config/opencode/platforms/analytics.py report"
echo "           python3 ~/.config/opencode/platforms/analytics.py best-times"
echo "           python3 ~/.config/opencode/platforms/analytics.py growth"
echo ""
echo ""
echo -e "${YELLOW}MCP Server available:${NC}"
echo "  BulkPublish MCP (37 AI tools) is configured but DISABLED in opencode.jsonc."
echo "  To enable:"
echo "    1. Sign up free at https://app.bulkpublish.com"
echo "    2. Get your API key from Settings"
echo "    3. Set env var: export BULKPUBLISH_API_KEY=bp_your_key"
echo "    4. Change enabled: false → true in the bulkpublish MCP entry"
echo ""

echo -e "${MAGENTA}Tip: All credentials are stored in chmod 600 files. Never share them!${NC}"
