#!/usr/bin/env bash
set -e

# Trading Campaign Orchestrator
# Usage: bash campaign.sh <TICKER> [--publish]
# Example: bash campaign.sh NVDA --publish

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; NC='\033[0m'

TICKER="${1:-NVDA}"
PUBLISH=false
if [[ "$2" == "--publish" ]]; then
    PUBLISH=true
fi

TRADING_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTENT_GEN="/root/.config/opencode/platforms/content-gen.py"
POST_SCRIPT="/root/.config/opencode/platforms/post.sh"
ANALYSIS_FILE="${TRADING_DIR}/latest_analysis.json"

echo -e "${CYAN}🚀 STARTING MARKET-TO-POST CAMPAIGN: ${TICKER}${NC}"
echo "============================================================"

# 1. Run Market Analysis
echo -e "\n${YELLOW}[1/4] Analyzing Market...${NC}"
bash "${TRADING_DIR}/analyze.sh" "$TICKER"

if [ ! -f "$ANALYSIS_FILE" ]; then
    echo -e "${RED}❌ Analysis failed. No result file found.${NC}"
    exit 1
fi

# 2. Extract Data
DECISION=$(python3 -c "import json; d=json.load(open('$ANALYSIS_FILE')); print(d.get('decision', ''))" | head -n 1)
echo -e "   Analysis Result: ${GREEN}${DECISION} ${NC}"

# 3. Generate Platform Copy
echo -e "\n${YELLOW}[2/4] Generating Platform Copy...${NC}"

# Twitter
TW_TEXT=$(python3 "$CONTENT_GEN" caption --topic "$TICKER Analysis: $DECISION" --platform twitter --backend gemini 2>/dev/null | tail -n 3 | tr '\n' ' ')
echo -e "   ${CYAN}Twitter:${NC} ${TW_TEXT:0:60}..."

# LinkedIn
LI_TEXT=$(python3 "$CONTENT_GEN" caption --topic "$TICKER Analysis: $DECISION" --platform linkedin --backend gemini 2>/dev/null | tail -n 10 | tr '\n' ' ')
echo -e "   ${CYAN}LinkedIn:${NC} ${LI_TEXT:0:60}..."

# Instagram (Captions + Hashtags)
IG_TEXT=$(python3 "$CONTENT_GEN" caption --topic "$TICKER Analysis: $DECISION" --platform instagram --backend gemini 2>/dev/null | tail -n 10 | tr '\n' ' ')
IG_TAGS=$(python3 "$CONTENT_GEN" hashtags --topic "$TICKER Analysis" --platform instagram --backend gemini 2>/dev/null)
IG_FINAL="${IG_TEXT} ${IG_TAGS}"
echo -e "   ${CYAN}Instagram:${NC} ${IG_TEXT:0:60}..."

# 4. Distribution
echo -e "\n${YELLOW}[3/4] Distributing Campaign...${NC}"
if [ "$PUBLISH" = true ]; then
    echo -e "${GREEN}🚀 Publishing live...${NC}"
    bash "$POST_SCRIPT" --text "$TW_TEXT" --platforms "twitter" --yes
    bash "$POST_SCRIPT" --text "$LI_TEXT" --platforms "linkedin" --yes
    bash "$POST_SCRIPT" --text "$IG_FINAL" --platforms "instagram" --yes
else
    echo -e "${CYAN}ℹ️ Dry-run mode. Previewing posts:${NC}"
    bash "$POST_SCRIPT" --text "$TW_TEXT" --platforms "twitter" --dry-run
    bash "$POST_SCRIPT" --text "$LI_TEXT" --platforms "linkedin" --dry-run
    bash "$POST_SCRIPT" --text "$IG_FINAL" --platforms "instagram" --dry-run
fi

echo -e "\n${GREEN}✅ Campaign Complete for ${TICKER}${NC}"
echo "============================================================"
