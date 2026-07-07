# Agent Evaluation Configuration

**Inspired by:** regokan/evalh — YAML-driven evaluation framework where
a single `eval.yaml` drives systems, datasets, evaluators, and run config.

## Overview

Eval configs define how to evaluate agent performance. They travel with the
system — not hardcoded into scripts. Each config specifies:

1. **Systems**: Which agents to evaluate
2. **Datasets**: Which golden test cases to use
3. **Evaluators**: How to score each test case
4. **Thresholds**: Pass/fail gates (Juanllenato `--fail-under` pattern)
5. **Tiers**: Severity levels for regression detection (info/warn/critical)

## File Structure

```
shared/eval/
├── AGENTS.md              ← THIS FILE — documentation
├── agent_eval.yaml        ← Main eval config (all agents)
└── <agent>_eval.yaml      ← Per-agent eval configs
```

## Usage

```bash
# Run full evaluation with fail-under gate
python3 -m opencode_improvement eval --config shared/eval/agent_eval.yaml --fail-under 0.8

# Run per-agent
python3 -m opencode_improvement eval --agent build --config shared/eval/build_eval.yaml

# Compare against baseline (Victor-David-Medina regression pattern)
python3 -m opencode_improvement eval --compare shared/eval/agent_eval.yaml --baseline baseline.json
```
