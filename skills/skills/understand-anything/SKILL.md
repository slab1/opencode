# Skill: Understand Anything — Codebase Knowledge Graph Integration

Integrates [Understand Anything](https://github.com/Egonex-AI/Understand-Anything) (64K+ GitHub stars) into the OpenCode agent ecosystem. Use this skill when you need to rapidly comprehend a large, unfamiliar codebase by building an interactive knowledge graph.

## Overview

Understand Anything is a Tree-sitter + LLM hybrid that extracts structural facts (functions, classes, imports) from source code, then enriches them with semantic context (summaries, tags, architectural layers) via LLM agents. The result is a JSON knowledge graph with nodes, edges, layers, and guided tours.

## Integration Architecture

```
Target Codebase
      │
      ▼
[Understand Anything CLI]  ← Install once, run per project
      │
      ▼
  knowledge-graph.json     ← Nodes, edges, layers, tours
      │
      ▼
[understand-bridge.py]     ← Maps U-A graph → OpenCode format
      │
      ▼
  shared/context.json      ← Cross-agent shared state
  graphify-out/            ← Graphify knowledge graph queries
```

## Quick Start

### 1. Install Understand Anything

```bash
npm install -g @understand-anything/cli
# OR clone + build:
git clone https://github.com/Egonex-AI/Understand-Anything.git
cd Understand-Anything && pnpm install && pnpm build
```

### 2. Analyze a Codebase

```bash
cd /path/to/target/project
understand-anything analyze --output .understand-anything/
```

This produces `.understand-anything/knowledge-graph.json`.

### 3. Bridge to OpenCode

```bash
python3 ~/.config/opencode/platforms/understand-bridge.py \
  --input /path/to/target/.understand-anything/knowledge-graph.json \
  --output ~/.config/opencode/shared/context.json \
  --project-name "my-project"
```

## Knowledge Graph Schema

The bridge produces this mapping:

### Nodes (20 types)

| U-A Type      | Graphify Equivalent | Description                    |
|---------------|-------------------|--------------------------------|
| `file`        | `file`            | Source file                    |
| `function`    | `function`        | Function/method definition     |
| `class`       | `class`           | Class/interface/struct         |
| `module`      | `module`          | Package/module                 |
| `service`     | `service`         | Microservice/container         |
| `endpoint`    | `endpoint`        | API route/endpoint             |
| `table`       | `table`           | Database table/migration       |
| `domain`      | `domain`          | Business domain                |
| `flow`        | `flow`            | Business flow/process          |
| `config`      | `config`          | Configuration                  |
| `document`    | `document`        | Documentation                  |
| `schema`      | `schema`          | Data schema/protobuf           |
| `pipeline`    | `pipeline`        | CI/CD pipeline                 |
| `resource`    | `resource`        | Infrastructure resource        |

### Edges (35 types in 8 categories)

| Category        | Edge Types                                                    |
|-----------------|---------------------------------------------------------------|
| Structural      | `imports`, `exports`, `contains`, `inherits`, `implements`    |
| Behavioral      | `calls`, `subscribes`, `publishes`, `middleware`              |
| Data flow       | `reads_from`, `writes_to`, `transforms`, `validates`          |
| Dependencies    | `depends_on`, `tested_by`, `configures`                       |
| Semantic        | `related`, `similar_to`                                       |
| Infrastructure  | `deploys`, `serves`, `provisions`, `triggers`                 |
| Schema/Data     | `migrates`, `documents`, `routes`, `defines_schema`           |
| Domain          | `contains_flow`, `flow_step`, `cross_domain`                  |

### Layers

The architecture analyzer detects these layering patterns:

- **Infrastructure** — networking, storage, compute
- **Data** — databases, migrations, ORM models
- **Data-UI Bridge** — API endpoints, resolvers, controllers
- **UI** — frontend components, pages, views
- **Core Logic** — domain services, business logic
- **Auth** — authentication, authorization middleware
- **Config** — configuration files, env vars
- **Testing** — test files, fixtures, mocks
- **Deployment** — CI/CD, Docker, Helm

### Tours

Guided walkthroughs ordered by dependency. Each step has: title, description, node IDs, optional language lesson.

## Agent Patterns

### Pattern 1: Rapid Codebase Orientation

When a new developer joins or needs to understand a project:

```
1. Run understand-anything on the target repo
2. Bridge the graph → shared context
3. (Optional) Load the graphify skill for querying
4. Use guided tours for dependency-ordered walkthrough
5. Use smart search: "where is the auth logic?"
```

### Pattern 2: Pre-Commit Diff Impact Analysis

Before making changes, understand ripple effects:

```
1. Run understand-anything (baseline graph)
2. Make changes
3. Run understand-anything diff or analyzeChanges()
4. See which files/functions/classes are affected
5. Review impact before committing
```

### Pattern 3: Onboarding Automation

Generate structured onboarding materials:

```
1. Analyze codebase with understand-anything
2. Bridge graph → extract layers + tours
3. Use content-repurposing skill to generate:
   - Architecture overview doc
   - Dependency-ordered reading list
   - Key module deep-dives
```

## CLI Reference

```bash
# Bridge a knowledge graph into OpenCode shared context
python3 understand-bridge.py --input graph.json --output context.json [--project NAME]

# Generate guided tour as markdown
python3 understand-bridge.py --input graph.json --generate-tour --output TOUR.md

# Summary report
python3 understand-bridge.py --input graph.json --summary

# Diff between two graph versions
python3 understand-bridge.py --diff old.json new.json
```

## File Locations

| Asset | Path |
|-------|------|
| Skill definition | `~/.config/opencode/skills/skills/understand-anything/SKILL.md` |
| Bridge script | `~/.config/opencode/platforms/understand-bridge.py` |
| Target graph (example) | `/path/to/project/.understand-anything/knowledge-graph.json` |

## Related Skills

- **graphify** — query knowledge graphs with community detection
- **content-repurposing-skill** — transform source content into multi-platform posts
- **system-audit** — structural audit of all agents
- **cross-domain-transfer** — transfer patterns between systems
