#!/bin/sh
# oc-mcp-toggle - Toggle MCP server enabled state in opencode.jsonc
# Usage: oc-mcp-toggle <name> on|off
#        oc-mcp-toggle list                # list MCPs and their status
#        oc-mcp-toggle demand [names...]   # disable heavy MCPs (off), keep light ones on
#        oc-mcp-toggle all-off             # disable ALL MCPs
#        oc-mcp-toggle all-on              # enable ALL MCPs

set -e

CONFIG="/home/.config/opencode/opencode.jsonc"

list_mcps() {
    echo "=== MCP Server Status ==="
    opencode mcp list 2>/dev/null || echo "(opencode mcp list not available)"
    echo ""
    echo "=== From opencode.jsonc ==="
    # Extract MCP names and their enabled status (with proper JSONC handling)
    python3 -c "
import re, json
def parse_jsonc(text):
    # Remove block comments
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    # Remove line comments (but not inside strings)
    out = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        c = text[i]
        if escape:
            out.append(c)
            escape = False
        elif c == '\\\\':
            out.append(c)
            escape = True
        elif c == '\"':
            out.append(c)
            in_string = not in_string
        elif not in_string and c == '/' and i + 1 < len(text) and text[i+1] == '/':
            # Skip to end of line
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return json.loads(''.join(out))
content = open('$CONFIG').read()
data = parse_jsonc(content)
mcp = data.get('mcp', {})
for name, cfg in mcp.items():
    enabled = cfg.get('enabled', True)
    mcp_type = cfg.get('type', '?')
    status = 'ENABLED' if enabled else 'disabled'
    print(f'  {name:20s} [{mcp_type:6s}] {status}')
"
}

toggle_mcp() {
    name="$1"
    state="$2"
    if [ -z "$name" ] || [ -z "$state" ]; then
        echo "Usage: oc-mcp-toggle <name> on|off"
        exit 1
    fi
    if [ "$state" != "on" ] && [ "$state" != "off" ]; then
        echo "State must be 'on' or 'off'"
        exit 1
    fi
    python3 -c "
import re, json, sys
def parse_jsonc(text):
    out = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        c = text[i]
        if escape:
            out.append(c)
            escape = False
        elif c == '\\\\':
            out.append(c)
            escape = True
        elif c == '\"':
            out.append(c)
            in_string = not in_string
        elif not in_string and c == '/' and i + 1 < len(text) and text[i+1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return json.loads(''.join(out))
path = '$CONFIG'
data = parse_jsonc(open(path).read())
mcp = data.get('mcp', {})
if '$name' not in mcp:
    print(f'ERROR: MCP $name not found in config')
    print(f'Available: {list(mcp.keys())}')
    sys.exit(1)
mcp['$name']['enabled'] = ('$state' == 'on')
open(path, 'w').write(json.dumps(data, indent=2))
print(f'$name: {\"ENABLED\" if mcp[\"$name\"][\"enabled\"] else \"disabled\"}')
"
}

set_all() {
    state="$1"
    if [ -z "$state" ]; then
        echo "Usage: oc-mcp-toggle all-on|all-off"
        exit 1
    fi
    if [ "$state" = "all-on" ]; then
        val="true"
    elif [ "$state" = "all-off" ]; then
        val="false"
    else
        echo "Usage: oc-mcp-toggle all-on|all-off"
        exit 1
    fi
    python3 -c "
import re, json
def parse_jsonc(text):
    out = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        c = text[i]
        if escape:
            out.append(c)
            escape = False
        elif c == '\\\\':
            out.append(c)
            escape = True
        elif c == '\"':
            out.append(c)
            in_string = not in_string
        elif not in_string and c == '/' and i + 1 < len(text) and text[i+1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return json.loads(''.join(out))
path = '$CONFIG'
data = parse_jsonc(open(path).read())
mcp = data.get('mcp', {})
for name in mcp:
    mcp[name]['enabled'] = ('$val' == 'true')
open(path, 'w').write(json.dumps(data, indent=2))
print(f'Set {len(mcp)} MCPs to enabled=$val')
"
}

demand_mode() {
    python3 -c "
import re, json
def parse_jsonc(text):
    out = []
    in_string = False
    escape = False
    i = 0
    while i < len(text):
        c = text[i]
        if escape:
            out.append(c)
            escape = False
        elif c == '\\\\':
            out.append(c)
            escape = True
        elif c == '\"':
            out.append(c)
            in_string = not in_string
        elif not in_string and c == '/' and i + 1 < len(text) and text[i+1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return json.loads(''.join(out))
path = '$CONFIG'
data = parse_jsonc(open(path).read())
mcp = data.get('mcp', {})
heavy = ['higgsfield', 'firecrawl', 'pdf-mcp']
for name in mcp:
    if name in heavy:
        mcp[name]['enabled'] = False
    else:
        mcp[name]['enabled'] = True
open(path, 'w').write(json.dumps(data, indent=2))
print('Demand-activation mode set:')
print('  Heavy MCPs (off, enable on demand):')
for n in heavy:
    if n in mcp:
        print(f'    - {n}')
print('  Light MCPs (on):')
for n in mcp:
    if n not in heavy:
        print(f'    - {n}')
print('')
print('To enable a heavy MCP: oc-mcp-toggle <name> on')
"
}

case "${1:-}" in
    list|ls|"")
        list_mcps
        ;;
    demand)
        shift
        demand_mode "$@"
        ;;
    all-on|all-off)
        set_all "$1"
        ;;
    on|off)
        toggle_mcp "$2" "$1"
        ;;
    *)
        # Assume name + on/off
        if [ -n "$2" ]; then
            toggle_mcp "$1" "$2"
        else
            echo "Unknown command: $1"
            echo "Usage: oc-mcp-toggle <name> on|off"
            echo "       oc-mcp-toggle list"
            echo "       oc-mcp-toggle demand"
            echo "       oc-mcp-toggle all-on|all-off"
            exit 1
        fi
        ;;
esac
