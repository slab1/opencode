# Positioning — The Free, Self-Hosted, Private Agent Workstation

**One line:** *A production agent workstation that runs on your own $5 VPS (or laptop), never phones home, and gets smarter every session — for the price of a free-tier model key.*

This document is the honest packaging of the OpenCode config toolkit (`~/.config/opencode`,
repo `github.com/slab1/opencode`). Every claim below names the file that proves it.

---

## 1. The wedge we attack

| Competitor weakness (2026 mid-year research) | Our counter |
|---|---|
| **Cost unpredictability** — Claude Code 4-10x token spikes, Devin `$20 budget → $400 invoice` | Free-tier models (Google Gemini free tier: ~20 req/day) + **MockProvider CI** so eval cost is $0; `scripts/setup-free-models.sh`, `shared/free-models-guide.md`, `shared/eval/` |
| **Lock-in & vendor risk** — Gemini CLI retired, Windsurf → Devin, Cursor $60B | Runs on **OpenCode** (open source), config is plain files in a git repo; move hosts by re-cloning |
| **Zero cross-session memory** — Claude Code #14228, "every session starts from scratch" | Hierarchical Cognitive Memory (L1-L4): episodic store (`memory/aether/episodic_memory.jsonl`), TF-IDF retrieval, auto-log on every tracked task, handoff feedback loop |
| **Verification distrust** — 66% of devs distrust agent output | Self-hosted eval harness: 63 golden cases, behavioral (not text) checks, nightly real-LLM CI cron, A/B compare, kappa |
| **"Phones home" / cloud-only** | Self-hosted: models are API calls *you* configure; runtime is local processes; dashboard/display are local |

---

## 2. What it is (verified claims)

### Runs where you already are
- One command install: `curl -fsSL https://raw.githubusercontent.com/slab1/opencode/main/install.sh | sh`
  (see `install.sh` — detects alpine/debian/rhel/macos, installs Xvfb + ffmpeg + poppler + playwright + MCP deps).
- No account, no cloud console, no quota gates. Restart OpenCode and the toolkit activates.

### 23 agents, not 1 chatbot
- `agents/*.md` — orchestrator, build, debug, refactor, review, security, test, docs, media-agent,
  document-agent, web-browser, video-creator, display-agent, meta-agent, heartbeat + more.
- Cross-agent shared state: every agent reads `shared/context.json` first and writes findings back
  (protocol in `shared/AGENTS.md`).

### Private by construction
- All state lives in `~/.config/opencode`: memory, checkpoints, commits, graph, evals.
- Model calls go to the provider endpoint YOU set (`LLM_PROVIDER`/`BASE_URL`);
  nothing is proxied through a vendor control plane.

### Self-improving — honestly
- **Eval harness = the product** (`shared/eval/`, `agent-eval/`, `shared/golden/agent_tasks.json`):
  63 golden tasks, behavioral observation checks, MockProvider for CI, real-LLM nightly cron,
  baseline regression compare. "Proof it works" instead of "promise it works."
- **Cross-session continuity is demonstrable**: `scripts/demo-multi-session-continuity.py` runs
  Session A (works) → Session B (fresh process) and shows B recovering A's task, facts, and
  handoff with scores. Run it yourself: `python3 scripts/demo-multi-session-continuity.py` (exits 0).

---

## 3. What it is NOT (honesty section — we read our own code)

Per the 2026-08-09 oracle audit, these claims are **not** made:

- ❌ "11-platform social suite" — 1/11 connected, 0 posts. Not marketed.
- ❌ "World model" — `shared/simulation_sandbox.py` is a **change review queue**, not a simulator.
- ❌ Unverified skill synthesis — `skill_synthesizer.py` scaffold mode marks output
  `UNVERIFIED-DO-NOT-USE` and raises `NotImplementedError` on generation until eval-gated.
- ❌ RCSI magic — `logic_evolve.py` `verify_patch` is a **real shadow test** (temp copy → eval →
  compare vs baseline); nothing auto-promotes without passing it.
- ⚠️ Free-tier model limit: ~20 req/day on Google's free tier — fine for daily driver,
  budget 0-cost; upgrade key for bursts.

If a future claim ever outruns the code, this section must be updated first.

---

## 4. The memory moat (why it compounds)

Every session that writes real work grows the moat:

```
track (CLI / auto-log) ──► L2 episodic memory (memory/aether/episodic_memory.jsonl)
                                  │ TF-IDF + cosine (numpy), score-ranked
session close ──► handoff feedback ──► read by next session (memory_loop)
spawner ──► cognitive packet (L2 episodic + L3 semantic + L4 skills) injected into subagent prompt
```

- `scripts/seed-episodic-memory.py` backfills history (idempotent; ~64+ entries, real data).
- Demo (above) proves a fresh process recovers prior work — the exact failure mode
  competitors still have open.

---

## 5. Cost sheet (honest numbers)

| Item | Cost |
|---|---|
| Host | $5-6/mo VPS **or** the machine you already own — $0 |
| Model (free tier) | $0 (Gemini free tier; see `shared/free-models-guide.md`) |
| CI evals | $0 (MockProvider; real-LLM nightly on small subset) |
| Licensing | $0 (OpenCode open source; toolkit repo public) |
| **Total** | **≈ $0-6/mo**, no per-seat, no per-token invoice surprises |

Compare: managed AI coding seats run $20-40+/mo/seat with usage spikes, and die or get
acquired (Gemini CLI retired 2026, Windsurf → Devin).

---

## 6. Quick proof checklist (for reviewers)

```bash
git clone https://github.com/slab1/opencode.git /tmp/oc-check
ls /tmp/oc-check/agents/*.md | wc -l          # 23+ agent definitions
python3 scripts/demo-multi-session-continuity.py   # run from an installed copy: exits 0 (continuity works)
python3 - <<'EOF'
import json, pathlib
ctx = json.loads((pathlib.Path.home()/".config/opencode/shared/context.json").read_text())
print(len(ctx.get("strategy_log", [])), "strategy entries", len(ctx.get("decisions", [])), "decisions")
EOF
head -63 /tmp/oc-check/shared/golden/agent_tasks.json   # golden cases
```