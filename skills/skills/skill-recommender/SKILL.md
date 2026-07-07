---
name: skill-recommender
description: Use the oc-recommend-skills CLI to discover which skills and agents are best suited for a given task. Use when an agent receives a task and needs to decide which skills to load. The recommender uses keyword matching against a curated task_skill_map.
license: MIT
compatibility: opencode>=1.16.0
---

# Skill Recommender

When you receive a task, use `oc-recommend-skills` to discover which skills and agents are best suited. This is faster and more reliable than guessing.

## The tool

```bash
oc-recommend-skills "<task description>"     # get ranked recommendations
oc-recommend-skills --list                   # see all task categories
oc-recommend-skills --agent <agent_name>     # see skills for an agent
oc-recommend-skills --category <category>    # see skills for a category
oc-recommend-skills --json                   # JSON output for parsing
```

## How it works

The recommender uses **keyword matching** against a curated `task_skill_map` (in `shared/task_skill_map.json`). Each task category has:
- **Keywords**: words/phrases that suggest this task type
- **Primary agent**: the best agent for this kind of task
- **Skills**: which skills to load

There are 20+ task categories including: code_review, build_feature, fix_bug, refactor, write_tests, research_tech, design_system, write_docs, security_review, process_video, process_image, process_audio, process_document, browse_web, explore_code, self_improve, long_task, orchestrate, git_commit, mcp_work.

## When to use

Use `oc-recommend-skills` when:
- You receive a new task and aren't sure which agent/skills apply
- You're routing a task to the right agent
- You're preparing a workflow that needs multiple skills
- The user asks "what skills should I use for X?"

## Workflow

### 1. Get recommendations

```bash
oc-recommend-skills "fix the broken auth flow that's causing crashes"
```

Output:
```
#1  fix_bug (score: 4)
    Agent:  debug
    Match:  fix, broken, crash
    Skills: debug-systematic-investigation, error-recovery-protocol, hash-anchored-edits

#2  security_review (score: 2)
    Agent:  security
    Match:  auth
    Skills: security-audit, security-threat-model
```

### 2. Pick the top recommendation

Use the highest-scoring category's agent and skills.

### 3. Load the skills

Use the native `skill` tool to load each recommended skill:
```
skill: debug-systematic-investigation
skill: error-recovery-protocol
skill: hash-anchored-edits
```

### 4. Dispatch to the agent

Delegate to the recommended agent (or stay in current agent if it matches).

## Example: routing logic

```python
import subprocess, json

def recommend_for_task(task_desc):
    result = subprocess.run(
        ['oc-recommend-skills', task_desc, '--json'],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    if data['recommendations']:
        top = data['recommendations'][0]
        return {
            'agent': top['agent'],
            'skills': top['skills'],
            'category': top['category'],
        }
    return None
```

## Example: multi-skill workflow

For complex tasks, you may get multiple recommendations. Load skills from each:

```bash
# Task: "Build a feature, write tests, then document it"
oc-recommend-skills "Build a feature, write tests, then document it"
# → build_feature (build, hash-anchored-edits, tdd-workflow, git-commit-hygiene)
# → write_tests (test, tdd-workflow)
# → write_docs (docs, documentation-skeleton)

# Load all skills
skill: hash-anchored-edits
skill: tdd-workflow
skill: git-commit-hygiene
skill: documentation-skeleton
```

## Limitations

- **Keyword-based**: may miss tasks with unusual phrasing
- **English-only**: keywords are English
- **Single-domain**: doesn't model multi-step workflows with dependencies
- **No context awareness**: doesn't know what you've already done

## When NOT to use

- You already know which skills to load (just load them)
- The task is trivial (one or two obvious skills)
- You need reasoning about trade-offs (use an LLM, not a tool)

## Integration

- `orchestrator` — should call this for every incoming task
- `plan` — should use this when designing multi-step workflows
- `meta-agent` — should use this when adding new skills
- Any agent receiving a new task — consider calling it first
