# Muse Prompt Engineering - Training Report

**Date:** 2026-08-22
**Model:** DeepSeek V3 via OpenRouter (muse proxy)
**Proxy:** http://127.0.0.1:8765

## Summary
Trained 3 agents with Muse's prompt engineering. All optimizations focus on clarity, specificity, and actionable instructions.

## Trained Agents

### 1. architect
- **Original:** 9004 chars
- **Improvements:** Added success criteria, prioritization guidelines, quality attributes
- **Key change:** Added `success_criteria` and better trade-off guidance

### 2. build
- **Original:** 10755 chars
- **Improvements:** Added code quality standards, dependency management, error handling
- **Key change:** More specific about testing and performance

### 3. cognition
- **Original:** 5336 chars
- **Improvements:** Fixed truncated capabilities, added examples, error handling
- **Key change:** Added priority and better memory operation examples

## Next Steps
- Train remaining 32 agents: `python3 opencode_improvement/muse_prompt_engineer.py --all --limit 32`
- Apply optimizations: Review `shared/muse_prompt_training.json` and update `agents/*.md`
- Test via eval: `python3 -m opencode_improvement eval --agent <name> --provider mock`
- Integrate with RCSI: `python3 -m opencode_improvement logic_evolve`

## Usage
```bash
# Train single agent
python3 opencode_improvement/muse_prompt_engineer.py --agent fixer

# Train all
python3 opencode_improvement/muse_prompt_engineer.py --all --limit 10

# Test Muse
python3 opencode_improvement/muse_prompt_engineer.py --test
```

## Proxy Status
- Running on 127.0.0.1:8765
- Model: deepseek/deepseek-chat ($0.14/1M, ~$0.00005 per training)
- Cost for 3 agents: ~$0.00015
- Free tier limit: 8k prompt → capped to 2k, main requests use non-streaming
