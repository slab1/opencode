# agent-eval

Standalone agent evaluation toolkit — audit, eval, scorecard, A/B compare, strategy tracking.

Extracted from the OpenCode self-improvement engine. Self-contained — no external dependencies beyond stdlib.

## Installation

```bash
pip install /root/projects/agent-eval
# Or in editable mode for development:
pip install -e /root/projects/agent-eval
```

## Quick Start

```bash
# Structural audit of all agents
python3 -m agent_evals audit

# Audit a specific agent
python3 -m agent_evals audit --agent orchestrator

# Run golden test eval with mock provider
python3 -m agent_evals eval --agent build --provider mock

# Run eval with ASCII scorecard
python3 -m agent_evals eval --provider mock --scorecard

# Fail-under gating (CI integration)
python3 -m agent_evals eval --fail-under 0.8

# Inspect failing test cases for an agent
python3 -m agent_evals inspect --agent orchestrator --failed

# Show all test case versions
python3 -m agent_evals eval --version
python3 -m agent_evals version

# List all improvement strategies
python3 -m agent_evals list-strategies

# Show strategy effectiveness
python3 -m agent_evals strategies

# A/B compare two configs
python3 -m agent_evals ab --agent build config_a.md config_b.md

# Compute Cohen's Kappa
python3 -m agent_evals kappa

# Generate improvement suggestions
python3 -m agent_evals suggest --agent debug
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `audit` | Audit all agent configs for structural completeness |
| `eval` | Run golden test cases against agents |
| `inspect` | Inspect per-case details or list failing cases |
| `kappa` | Compute Cohen's Kappa inter-rater agreement |
| `list-strategies` | List all available improvement strategies |
| `strategies` | Show strategy effectiveness scores |
| `ab` | A/B compare two agent configurations |
| `version` | Show package version and task version info |
| `suggest` | Suggest improvements for an agent |
| `report` | Generate performance report |
| `track` | Log a task outcome |
| `strategy` | Log an improvement strategy decision |

## Path Configuration

Paths default to `~/.config/opencode/`. Override via:

### Environment variable
```bash
export AGENT_EVAL_HOME=/path/to/opencode/config
```

### CLI flags
All commands accept:
- `--agents-dir` — override agents directory
- `--golden-file` — override golden dataset path
- `--eval-dir` — override eval directory

## Key Concepts

### Mock Provider
Deterministic offline eval via `--provider mock`. Reads golden dataset and returns perfect scores — useful for CI pipelines that need zero-cost evaluation.

### Property-Based Tests
Universal invariants all agents must satisfy (property-001 through property-007). These check for structural elements like `<role>`, `<capabilities>`, frontmatter, and `<shared-context>`.

### Strategy Tracking
Metacognitive tracking inspired by HyperAgents. Log strategy decisions and measure effectiveness via `strategy` and `strategies` commands.

### A/B Comparison
Compare candidate agent configs against incumbent using `ab` subcommand — determines if the candidate beats the incumbent on all test cases.

## Development

```bash
# Run tests
python3 -m pytest tests/

# Build package
python3 -m build

# Install locally
pip install -e .
```

## License

MIT
