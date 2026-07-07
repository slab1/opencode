#!/usr/bin/env bash
set -e

# TradingAgents Analysis Wrapper
# Usage: bash analyze.sh NVDA [--date 2026-06-28] [--model gemini-3.1-flash-lite]
# Output: platforms/trading/latest_analysis.json

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'

TICKER="${1:-NVDA}"
DATE="${2:-$(date +%Y-%m-%d)}"
MODEL="${TRADINGAGENTS_DEEP_THINK_LLM:-gemini-3.1-flash-lite}"
TRADING_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}📈 TradingAgents Analysis${NC}"
echo -e "  Ticker: ${GREEN}${TICKER}${NC}"
echo -e "  Date:   ${DATE}"
echo -e "  Model:  ${MODEL}"
echo

# Source the .env for API key
if [ -f "/root/TradingAgents/.env" ]; then
    export $(grep -v '^#' /root/TradingAgents/.env | xargs)
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}❌ GOOGLE_API_KEY not set. Set it in /root/TradingAgents/.env${NC}"
    exit 1
fi

cd /root/TradingAgents

python3 -c "
import os, sys, json
from datetime import datetime

os.environ['GOOGLE_API_KEY'] = '${GOOGLE_API_KEY}'
os.environ['TRADINGAGENTS_LLM_PROVIDER'] = 'google'
os.environ['TRADINGAGENTS_DEEP_THINK_LLM'] = '${MODEL}'
os.environ['TRADINGAGENTS_QUICK_THINK_LLM'] = '${MODEL}'

sys.path.insert(0, '/root/TradingAgents')

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config['llm_provider'] = 'google'
config['deep_think_llm'] = '${MODEL}'
config['quick_think_llm'] = '${MODEL}'
config['google_thinking_level'] = 'low'
config['max_debate_rounds'] = 1
config['max_risk_discuss_rounds'] = 1
config['output_language'] = 'english'

start = datetime.now()
print(f'⏳ Running pipeline...', flush=True)

ta = TradingAgentsGraph(debug=False, config=config)
decision = ta.propagate('${TICKER}', '${DATE}')

elapsed = (datetime.now() - start).total_seconds()
print(f'✅ Done in {elapsed:.0f}s', flush=True)

# Extract key fields from decision
result = {
    'ticker': '${TICKER}',
    'date': '${DATE}',
    'model': '${MODEL}',
    'elapsed_seconds': elapsed,
    'timestamp': start.isoformat(),
    'success': True,
    'decision': str(decision)[:3000]
}

if isinstance(decision, tuple) and len(decision) == 2:
    msgs, meta = decision
    result['decision_obj'] = str(meta)

os.makedirs('${TRADING_DIR}', exist_ok=True)
with open('${TRADING_DIR}/latest_analysis.json', 'w') as f:
    json.dump(result, f, indent=2)

print(f'💾 Saved to ${TRADING_DIR}/latest_analysis.json')
"
