# OpenCode Knowledge Graph

Structured agent registry, capability map, and workflow patterns for the Orchestrator system.

## Structure

```
knowledge-graph/
├── graph.json          # Main knowledge graph (agents + patterns + rules)
├── README.md           # This file
└── outcomes/           # (Future) Session outcome tracking
```

## graph.json Structure

The knowledge graph contains:

### `meta`
Version, creation date, and description.

### `agents`
Registry of all agents with their:
- **mode**: primary or subagent
- **capabilities**: Array of what they can do
- **strengths**: What they excel at
- **weaknesses**: Known limitations
- **permissions**: File and command access levels
- **can_invoke_subagents**: Whether they can dispatch other agents
- **orchestrator_delegation**: Whether they can invoke agents when delegated by orchestrator

### `invocation_rules`
Rules governing agent-to-agent invocation:
- **max_recursion_depth_primary**: Max 3 levels for build/plan
- **max_recursion_depth_orchestrator**: Max 5 levels for orchestrator
- **delegation_rule**: Subagents need explicit delegation context

### `patterns`
Pre-defined workflow patterns that the orchestrator recognizes:
- **auth-flow**: Authentication development
- **api-endpoint**: API endpoint creation
- **bug-fix**: Investigation and fix
- **refactor**: Code restructuring
- **security-audit**: Vulnerability remediation
- **full-feature**: End-to-end development
- **code-review**: Multi-faceted review
- **performance**: Profiling and optimization

Each pattern has trigger keywords, agent sequences, and descriptions.

### `quality_gates`
Checklists the orchestrator uses to evaluate completeness:
- `code_complete`: Implementation quality checks
- `tested`: Test coverage requirements
- `secure`: Security checks
- `documented`: Documentation requirements
- `reviewed`: Code quality checks

### `gap_detection_rules`
Rules for common gaps to check based on task type:
- Auth tasks → also need email verification, password reset, etc.
- API tasks → also need input validation, error handling, etc.

### `shared_context`
Configuration for the cross-agent shared context system:
- **store_path**: Location of the machine-readable `context.json`
- **findings_dir**: Per-agent finding files directory
- **population_rules**: What each agent type should save to the context store
- **delegation_context_inclusion**: How context is injected when orchestrator delegates tasks

## How the Orchestrator Uses This

1. **Load**: Read `graph.json` at session start
2. **Match**: Compare user task against pattern `trigger_keywords`
3. **Dispatch**: Follow the pattern's `sequence` or build custom flow
4. **Evaluate**: Check output against `quality_gates`
5. **Detect Gaps**: Apply `gap_detection_rules` to find missing pieces
6. **Iterate**: Re-dispatch agents to fill identified gaps
7. **Update**: Save session outcomes (future enhancement)

## Querying the Graph

```bash
# List all agents
python3 -c "import json; g=json.load(open('graph.json')); print(list(g['agents'].keys()))"

# Get specific agent capabilities
python3 -c "import json; g=json.load(open('graph.json')); print(g['agents']['build']['capabilities'])"

# Find pattern by keyword
python3 -c "import json; g=json.load(open('graph.json')); print([k for k,v in g['patterns'].items() if 'auth' in v['trigger_keywords']])"

# Get quality gate checklist
python3 -c "import json; g=json.load(open('graph.json')); print(g['quality_gates']['code_complete'])"

# Check gap detection rules for auth tasks
python3 -c "import json; g=json.load(open('graph.json')); print(g['gap_detection_rules']['domain_considerations']['auth_tasks'])"

# Read shared context configuration
python3 -c "import json; g=json.load(open('graph.json')); print(json.dumps(g['shared_context'], indent=2))"

# Read live shared context store
python3 -c "import json; c=json.load(open(os.path.expanduser('~/.config/opencode/shared/context.json'))); print(json.dumps(c, indent=2))"
```

**Note**: Agents should prefer using the `read` tool to load the full graph and read it directly, rather than running bash commands.

## Extending

### Adding a New Agent
Add entry to `.agents` with all required fields. Update `.invocation_rules` if it can invoke subagents.

### Adding a New Pattern
Add entry to `.patterns` with name, agents array, trigger keywords, and sequence.

### Adding a New Quality Gate
Add entry to `.quality_gates` with a checklist array.

### Adding Shared Context Population Rules
When adding a new agent type, add an entry to `.shared_context.population_rules` defining what that agent should save to the shared context store.

---

**This file is managed by the OpenCode system. Agents: Read freely, update outcomes as needed.**
