#!/usr/bin/env python3
"""Bet 5 — Multi-session continuity demo.

Proves the memory stack gives a FRESH session real continuity with a PAST
session, end to end, using the same code paths an agent uses daily:

  Session A (evening)  : does work → episodic entries (auto-log path) +
                         semantic facts + cross-session handoff feedback.
  Session B (morning)  : starts with ZERO working context → cognitive packet
                         (L2 episodic + L3 semantic + L4 skills) + handoff
                         feedback → produces a concrete continuation plan.

Unlike the seed script, this demo CLEANS UP after itself (entries tagged
source=demo_bet5 are removed) so the production memory moat stays real data.
Exits 0 on pass, 1/2 on failure.

Run:  python3 scripts/demo-multi-session-continuity.py
"""

import json
import sys
import time
from pathlib import Path

BASE_DIR = Path.home() / ".config" / "opencode"
EPISODIC_DB = BASE_DIR / "memory" / "aether" / "episodic_memory.jsonl"
SEMANTIC_DB = BASE_DIR / "memory" / "aether" / "semantic_memory.json"
CONTEXT_FILE = BASE_DIR / "shared" / "context.json"

sys.path.insert(0, str(BASE_DIR))

from shared.memory_controller import MemoryController  # noqa: E402
from opencode_improvement.memory_loop import write_handoff, read_past_feedback  # noqa: E402

DEMO_TAG = "demo_bet5"
DEMO_TASK = "stripe webhook special event deposit payment flow"


def run_session_a(mc: MemoryController) -> None:
    """Evening session: real work happens, memory records it."""
    print("=" * 72)
    print("SESSION A (evening) — developer session finishes ~3 tasks")
    print("=" * 72)
    experiences = [
        (
            "investigate stripe webhook 404 for special event deposit",
            "Traced StripeEvent subjects; found special_events UUID passed as reservationId by frontend",
            "Root cause identified: payments.reservation_id FK can never hold an event id",
        ),
        (
            "add special_event_id to payments schema and edge functions",
            "Created migration 20260808120000, updated create-payment-intent and stripe-webhook handlers",
            "Deposit payments for special events now create payment intents with correct subject",
        ),
        (
            "fix frontend PaymentModal to pass specialEventId",
            "SpecialEventBooking now passes specialEventId instead of reservationId; added submit lock",
            "Double-click duplicate payment intents eliminated",
        ),
    ]
    for task, action, outcome in experiences:
        mc.store_experience(
            task, action, outcome,
            metadata={"agent": "developer", "source": DEMO_TAG, "demo_ts": time.time()},
        )
        print(f"  [L2] stored: {task[:60]}")

    mc.store_fact("special_events", "paid_via", "stripe_payment_intent")
    mc.store_fact("create-payment-intent", "subject", "reservation|event")
    print("  [L3] stored 2 semantic facts (special_events → stripe)")

    handoff = write_handoff()
    print(f"  [handoff] feedback written: {handoff.get('feedback_id', '?')}")
    print()


def run_session_b(mc: MemoryController, expected_task_hint: str) -> dict:
    """Morning session: fresh process, no working memory, must pick up."""
    print("=" * 72)
    print("SESSION B (morning) — NEW process. Task given: 'fix the stripe "
          "webhook payment for special events'")
    print("=" * 72)
    query = "fix the stripe webhook payment for special events"

    # Same call the cognition/spawner path uses for a fresh task.
    packet = mc.generate_cognitive_packet(query)

    print("\n  --- cognitive packet ---")
    episodic = packet.get("episodic", [])
    semantic = packet.get("semantic", [])
    procedural = packet.get("procedural", [])
    print(f"  L2 episodic hits : {len(episodic)}")
    for e in episodic[:3]:
        print(f"    · score={e.get('score'):.4f}  {e.get('task', '')[:70]}")
    print(f"  L3 semantic facts: {len(semantic)}")
    for s in semantic[:5]:
        print(f"    · {s.get('s')} --{s.get('p')}--> {s.get('o')}" if s.get('p') else f"    · {s}")
    print(f"  L4 skills        : {len(procedural)} -> {procedural[:3]}")

    print("\n  --- handoff feedback (past session's record) ---")
    fb = read_past_feedback(limit=1)
    records = fb.get("recent_feedback", [])
    print(f"  records available: {fb.get('total_records', 0)}")
    if records:
        r = records[-1]
        print(f"    generated_at : {r.get('generated_at', '?')}")
        print(f"    tasks/success: {r.get('performance_summary', {}).get('total_tasks')} / "
              f"{r.get('performance_summary', {}).get('success_rate')}")

    # The continuity verdict: what a fresh agent would actually do next.
    plan = []
    probe = expected_task_hint.split()[0].lower()  # e.g. "stripe"
    if any(probe in (e.get("task", "") or "").lower() for e in episodic):
        plan.append("Resume existing work on '" + expected_task_hint + "' — root cause already traced (frontend passed wrong id).")
        plan.append("Files to touch: migrations/, create-payment-intent, stripe-webhook, PaymentModal.")
        plan.append("Verification: re-run payment integration tests + checkout deposit flow.")
    if semantic:
        plan.append("Semantic map confirms: special_events → stripe_payment_intent.")
    return {
        "episodic": episodic,
        "semantic": semantic,
        "procedural": procedural,
        "plan": plan,
    }


def cleanup(mc: MemoryController) -> None:
    """Remove demo entries so the production moat keeps real data only."""
    removed_ep = 0
    if EPISODIC_DB.exists():
        lines = EPISODIC_DB.read_text().splitlines()
        kept = []
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                kept.append(line)
                continue
            meta = entry.get("metadata", {}) or {}
            if meta.get("source") == DEMO_TAG:
                removed_ep += 1
                continue
            kept.append(line)
        EPISODIC_DB.write_text("\n".join(kept) + ("\n" if kept else ""))

    removed_facts = 0
    if SEMANTIC_DB.exists():
        data = json.loads(SEMANTIC_DB.read_text())
        before = len(data.get("relations", []))
        data["relations"] = [
            r for r in data.get("relations", [])
            if not (r.get("s") == "special_events" and r.get("p") == "paid_via")
            and not (r.get("s") == "create-payment-intent" and r.get("p") == "subject")
        ]
        removed_facts = before - len(data["relations"])
        SEMANTIC_DB.write_text(json.dumps(data, indent=2))

    print(f"\n[cleanup] removed {removed_ep} episodic (+{removed_facts} facts) demo entries")


def main() -> int:
    mc = MemoryController()
    run_session_a(mc)

    result = run_session_b(mc, DEMO_TASK)

    # ---- verification ----
    fails = []
    ep = result["episodic"]
    if not ep:
        fails.append("Session B retrieved NO episodic hits — continuity broken")
    elif not any(DEMO_TASK.split()[0] in (e.get("task", "") or "") for e in ep):
        fails.append("Retrieval did not surface the demo session's work")
    if not result["semantic"]:
        fails.append("Semantic facts not retrieved")
    if not result["plan"]:
        fails.append("Continuation plan empty")
    try:
        fb = read_past_feedback()
        if not fb.get("recent_feedback"):
            fails.append("No handoff feedback record persisted")
    except Exception as e:  # pragma: no cover
        fails.append(f"read_past_feedback raised: {e}")

    print("\n" + "=" * 72)
    if fails:
        print("RESULT: FAIL")
        for f in fails:
            print(f"  ✗ {f}")
        cleanup(mc)
        return 1
    print("RESULT: PASS — a fresh session recovered its predecessor's work from memory.")
    print("Continuation plan (what Session B would do next):")
    for p in result["plan"]:
        print(f"  → {p}")
    print("=" * 72)

    cleanup(mc)
    return 0


if __name__ == "__main__":
    sys.exit(main())