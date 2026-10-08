#!/usr/bin/env python3
"""eval_skill_content.py — deterministic content evaluator for the 6 new skills.

WHY THIS EXISTS
---------------
The behavioural harness in `opencode_improvement` is *structural*: it keyword-matches a
case's `reference` field against `agents/<agent>.md` and never executes an agent. That
proves nothing about whether a SKILL.md still carries the content that justifies its
existence. A skill can lose every distinctive technique it teaches and still score 100%
there.

This script is the complement. It asserts that each of the 6 skills still contains the
*named, load-bearing techniques* that are the entire reason the skill exists — the
5-move guard list, the 4-tier source hierarchy, the 4 finding classes, the canary
thresholds table, the keep-or-revert table, and so on. Assertions are distinctive
multi-word literals or regexes; generic words ("use", "check", "test") are rejected by
review and by the negative-control test at the bottom of the report.

Stdlib only. No network. Deterministic: same input -> same output, always.

USAGE
-----
    python3 scripts/eval_skill_content.py                # table + per-skill verdict
    python3 scripts/eval_skill_content.py --json         # machine-readable
    python3 scripts/eval_skill_content.py --root DIR     # alternative skills tree
    python3 scripts/eval_skill_content.py --only NAME    # single skill
    python3 scripts/eval_skill_content.py --verbose      # list every assertion

EXIT
----
    0  every skill passed every assertion
    1  at least one assertion failed (or a skill/assertion is missing)
"""

import argparse
import json
import os
import re
import sys

DEFAULT_ROOT = "/root/.config/opencode/skills/skills"

# ---------------------------------------------------------------------------
# Assertion kinds:
#   ("lit",   "<exact substring>")            case-sensitive literal substring
#   ("litci", "<substring>")                  case-insensitive literal substring
#   ("re",    r"<regex>")                     regex, MULTILINE, DOTALL, IGNORECASE
# ---------------------------------------------------------------------------


def L(s):
    return ("lit", s)


def C(s):
    return ("litci", s)


def R(p):
    return ("re", p)


SKILLS = {
    # -----------------------------------------------------------------------
    "constraint-driven-development": [
        ("constraints-file-artifact", L("CONSTRAINTS.md")),
        ("bar-never-weakened-clause", C("does not get weakened to make a change pass")),
        ("guard-move-1-threshold-moved", L("Threshold moved")),
        ("guard-move-2-test-got-easier", L("Test got easier")),
        ("guard-move-3-checker-silenced", L("Checker got silenced")),
        ("guard-move-4-work-unfinished", L("Work is unfinished")),
        ("guard-move-5-undiscussed-exception",
         L("An exception appeared that nobody discussed")),
        ("istanbul-ignore-removes-from-coverage", L("istanbul ignore")),
        ("nosemgrep-suppression", L("nosemgrep")),
        ("gitleaks-suppression", L("gitleaks")),
        ("gitleaks-redact-mandatory", L("gitleaks detect --redact")),
        ("circularity-ranking", C("circularity ranking")),
        ("ratchet-concept", R(r"###\s*Step 7\s*[-—]\s*Ratchets")),
        ("ratchet-no-defensible-target", L("no defensible target")),
        ("ratchet-file-name", L(".constraints-ratchet.yaml")),
        ("lifecycle-script-check-fast", L("check:fast")),
        ("lifecycle-script-check-task", L("check:task")),
        ("lifecycle-script-check-full", L("check:full")),
        ("detect-before-you-ask", L("Never ask what you can read")),
        ("number-without-command-is-aspiration",
         L("aspiration, not a constraint")),
        ("escalation-levels", L("Escalation Path")),
        ("escalation-level-2-default", L("Most projects should stop here")),
    ],

    # -----------------------------------------------------------------------
    "doubt-driven-development": [
        ("step-1-claim", R(r"###\s*Step 1\s*[-—]\s*CLAIM")),
        ("step-2-extract", R(r"###\s*Step 2\s*[-—]\s*EXTRACT")),
        ("step-3-doubt", R(r"###\s*Step 3\s*[-—]\s*DOUBT")),
        ("step-4-reconcile", R(r"###\s*Step 4\s*[-—]\s*RECONCILE")),
        ("step-5-stop", R(r"###\s*Step 5\s*[-—]\s*STOP")),
        ("do-not-pass-the-claim", L("Do NOT pass the\nCLAIM")),
        ("do-not-validate-prompt", L("Do NOT validate")),
        ("doubt-theater-concept", L("Doubt Theater")),
        ("doubt-theater-checkable-signal", L("You are validating, not doubting")),
        ("finding-class-1-contract-misread", L("Contract misread")),
        ("finding-class-2-valid-actionable", L("Valid and actionable")),
        ("finding-class-3-valid-tradeoff", L("Valid trade-off")),
        ("finding-class-4-noise", L("**Noise**")),
        ("first-match-wins-precedence", L("First match wins")),
        ("never-lift-the-bound", L("Do not lift the bound")),
        ("bounded-recursion-3-cycles", L("Three unresolved cycles")),
        ("prompt-injection-control-section", L("Prompt-Injection Control")),
        ("prompt-injection-untrusted-input", L("may itself contain instructions")),
        ("read-only-reviewer", L("The reviewer runs **read-only**")),
        ("artifact-via-stdin-not-shell-arg", L("via stdin")),
        ("cross-model-escalation-section", L("Cross-Model Escalation")),
        ("cross-model-per-run-authorization",
         L("Each invocation is its own authorization")),
        ("gate-trigger-branching-logic", L("Branching logic")),
        ("gate-trigger-module-boundary", L("Crosses a module or service boundary")),
        ("gate-trigger-idempotence", L("idempotence")),
    ],

    # -----------------------------------------------------------------------
    "source-driven-development": [
        ("step-1-detect", R(r"###\s*Step 1\s*[-—]\s*DETECT")),
        ("step-2-fetch", R(r"###\s*Step 2\s*[-—]\s*FETCH")),
        ("step-3-implement", R(r"###\s*Step 3\s*[-—]\s*IMPLEMENT")),
        ("step-4-cite", R(r"###\s*Step 4\s*[-—]\s*CITE")),
        ("four-tier-hierarchy-named", L("The four-tier source hierarchy")),
        ("tier-1-official-docs", L("**Official docs**")),
        ("tier-2-changelog-release-notes", L("release notes / migration guide")),
        ("tier-3-web-standards", L("**Web standards**")),
        ("tier-4-compat-data", L("**Compatibility data**")),
        ("non-citable-stack-overflow", L("Stack Overflow answers")),
        ("non-citable-training-data", L("Your own training data")),
        ("non-citable-ai-docs-regurgitation", L("regurgitation, not evidence")),
        ("conflict-detected-block", L("CONFLICT DETECTED")),
        ("unverified-block", L("UNVERIFIED")),
        ("injection-example-string", L("ignore previous instructions")),
        ("retrieved-content-untrusted", L("Fetched pages are **untrusted input**")),
        ("content-not-command", L("content to report, not a command to obey")),
        ("deep-link-anchor-citation-rule", L("deep links with anchors")),
        ("anchors-survive-doc-restructuring",
         R(r"anchors survive\s*\n?doc restructuring")),
        ("outbound-endpoint-never-hardcoded",
         L("Never hardcode outbound endpoints")),
        ("version-determines-correct-pattern",
         R(r"version\s*\n?determines which patterns are correct")),
    ],

    # -----------------------------------------------------------------------
    "deprecation-and-migration": [
        ("pattern-expand-contract", L("Database Expand/Contract")),
        ("additive-first-destructive-last", L("Additive first, destructive last and alone")),
        ("tested-down-path", L("tested down path")),
        ("index-concurrently", L("CREATE INDEX CONCURRENTLY")),
        ("index-not-in-transaction", L("cannot run inside a transaction")),
        ("churn-rule", C("churn rule")),
        ("advisory-vs-compulsory-table", L("**Advisory**")),
        ("compulsory-requires-tooling",
         L("Compulsory deprecation requires providing migration")),
        ("default-to-advisory", L("Rule: default to advisory")),
        ("zombie-code-section", L("Zombie Code")),
        ("zombie-code-definition", L("Code that nobody owns but everybody depends on")),
        ("backfill-in-batches", L("Backfill in batches")),
        ("backfill-outage-metaphor", L("outage wearing a migration's clothes")),
        ("backfill-single-update-red-flag",
         R(r"one unbounded `UPDATE` inside the deploy")),
        ("dual-write-phase", L("dual-write")),
        ("bake-window", L("bake at least one full business cycle")),
        ("every-intermediate-state-deployable", L("every intermediate state is deployable")),
        ("strangler-fig-pattern", L("Strangler Fig")),
        ("backward-compatible-shim", L("backward-compatible shim")),
        ("removal-date-not-a-condition", L("a condition is not a date")),
        ("adoption-instrumented", L("instrumented")),
    ],

    # -----------------------------------------------------------------------
    "shipping-and-launch": [
        ("flag-lifecycle-section", L("## Feature Flag Lifecycle")),
        ("flag-lifecycle-deploy-off", L("DEPLOY (flag OFF)")),
        ("flag-lifecycle-monitor-stage", L("MONITOR at each stage")),
        ("flag-lifecycle-cleanup-stage", L("CLEAN UP (flag and dead branch removed)")),
        ("flag-owner-and-expiry", L("owner AND an expiration date")),
        ("flag-no-nesting", L("Do not nest flags")),
        ("flag-both-states-in-ci", L("Test both states in CI")),
        ("flag-cleanup-two-weeks", L("Cleanup within 2 weeks")),
        ("error-budget-gate-section", L("Run the error-budget release gate")),
        ("error-budget-freeze", L("Budget exhausted")),
        ("error-budget-hold-not-watch", L("is a HOLD signal")),
        ("rollback-plan-before-deploy",
         L("Prepare the rollback plan *before* the deploy")),
        ("time-to-rollback-field", L("Time to Rollback:")),
        ("named-decision-maker", L("Decision maker:")),
        ("thresholds-table-header",
         R(r"Advance \(green\)\s*\|\s*Hold and investigate \(yellow\)\s*\|\s*Roll back \(red\)")),
        ("threshold-error-rate-2x", L(">2x baseline")),
        ("threshold-client-errors-0.1pct", L(">0.1% of sessions")),
        ("threshold-p95-50pct", L(">50% above baseline")),
        ("canary-stage-5pct", L("**canary, 5%**")),
        ("staged-rollout-order", R(r"\*\*canary, 5%\*\*\s*\|[^\n]*\n[^\n]*\|\s*25%")),
        ("flag-defaults-off", L("flag defaults to OFF")),
        ("restore-rehearsal", L("Restore rehearsal status")),
    ],

    # -----------------------------------------------------------------------
    "performance-optimization": [
        ("workflow-fixed", L("1. MEASURE  ->  2. IDENTIFY  ->  3. FIX")),
        ("keep-or-revert-table", L("Past the threshold, tests green")),
        ("keep-or-revert-within-noise", L("Within noise (no measurable change)")),
        ("neutral-is-a-revert", L('"neutral" is a revert, not a keep')),
        ("step4-verification-step", R(r"###\s*4\.\s*VERIFY\s*[-—]\s*keep or revert")),
        ("attempt-ledger-section", L("## The attempt ledger")),
        ("attempt-ledger-file", L("PERF.md")),
        ("attempt-ledger-verdict-column", L("| Idea | Baseline -> Result | Verdict | Why |")),
        ("explain-analyze-is-measurement",
         L("`EXPLAIN ANALYZE` is the measurement")),
        ("nplus1-queries", L("### N+1 queries")),
        ("nplus1-orm-fix", L("select_related")),
        ("nplus1-prefetch", L("prefetch_related")),
        ("every-index-taxes-writes", L("Every index taxes every write")),
        ("index-that-changed-nothing-is-revert",
         L("an index that did not change the plan is a revert")),
        ("unused-index-detection", L("pg_stat_user_indexes.idx_scan = 0")),
        ("cache-key-omits-viewer", L("omits the viewer")),
        ("cache-key-is-the-contract", L("# the key is the contract")),
        ("cache-never-permissions", L("Never cache balances, permissions, or inventory")),
        ("cwl-lcp-target", L("| **LCP** (Largest Contentful Paint) | ≤ 2.5 s")),
        ("cwl-inp-target", L("| **INP** (Interaction to Next Paint) | ≤ 200 ms")),
        ("cwl-cls-target", L("| **CLS** (Cumulative Layout Shift) | ≤ 0.1")),
        ("cwl-75th-percentile", L("75th percentile")),
        ("bundle-budget-js", L("| JS bundle (per route) | < 200 KB gzipped |")),
        ("bundle-budget-css", L("| CSS | < 50 KB gzipped |")),
        ("bundle-budget-lighthouse", L("| Lighthouse Performance | ≥ 90 |")),
        ("budgets-enforced-in-ci", L("Enforce budgets in CI")),
        ("synthetic-iterate-field-validate",
         L("synthetic is where you iterate, field data is where you validate")),
        ("one-change-at-a-time", L("**One change at a time.**")),
        ("flaky-gate-warning", L("A flaky performance gate is worse than no gate")),
    ],
}


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def eval_assertion(kind, needle, text):
    """Return True when the assertion matches `text`."""
    op, payload = kind
    if op == "lit":
        return payload in text
    if op == "litci":
        return payload.lower() in text.lower()
    if op == "re":
        return re.search(payload, text, re.MULTILINE | re.DOTALL | re.IGNORECASE) is not None
    raise ValueError("unknown assertion op: %r" % (op,))


def marker(kind):
    """Human-readable description of what an assertion looked for."""
    op, payload = kind
    if op == "lit":
        return "literal %r" % payload
    if op == "litci":
        return "literal (case-insensitive) %r" % payload
    return "regex /%s/" % payload


def eval_skill(root, name, assertions):
    skill_file = os.path.join(root, name, "SKILL.md")
    result = {
        "skill": name,
        "skill_file": skill_file,
        "present": os.path.isfile(skill_file),
        "total": len(assertions),
        "passed": 0,
        "failed": 0,
        "failures": [],
        "checks": [],
        "skipped": False,
    }
    if not result["present"]:
        # A skill that is absent is a DIFFERENT condition from a skill whose
        # markers were stripped. Reporting 0/N FAIL for a missing directory makes
        # a moved or typo'd root indistinguishable from gutted content, which is
        # exactly the kind of failure this eval exists to catch.
        result["skipped"] = True
        result["failures"] = [
            {"name": n, "marker": marker(k),
             "reason": "SKILL.md not found at %s" % skill_file}
            for n, k in assertions
        ]
        return result

    text = read_text(skill_file)
    for name_, kind in assertions:
        ok = eval_assertion(kind, kind[1], text)
        entry = {"name": name_, "marker": marker(kind), "pass": ok}
        result["checks"].append(entry)
        if ok:
            result["passed"] += 1
        else:
            result["failed"] += 1
            result["failures"].append(
                {"name": name_, "marker": marker(kind),
                 "reason": "marker not found in %s" % skill_file}
            )
    return result


def eval_all(root, only=None):
    results = []
    for name, assertions in SKILLS.items():
        if only and name != only:
            continue
        results.append(eval_skill(root, name, assertions))
    return results


def render_table(results):
    lines = []
    width = max(len(r["skill"]) for r in results) + 2
    header = ("{:<{w}}  {:>9}  {:>7}  {:>7}  {}".format(
        "SKILL", "ASSERTIONS", "PASSED", "FAILED", "RESULT", w=width))
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        if r.get("skipped"):
            verdict = "SKIP (not found)"
        else:
            verdict = "PASS" if r["failed"] == 0 else "FAIL"
        lines.append("{:<{w}}  {:>9}  {:>7}  {:>7}  {}".format(
            r["skill"], r["total"], r["passed"], r["failed"], verdict, w=width))
    tot = sum(r["total"] for r in results)
    ps = sum(r["passed"] for r in results)
    fs = sum(r["failed"] for r in results)
    lines.append("-" * len(header))
    lines.append("{:<{w}}  {:>9}  {:>7}  {:>7}  {}".format(
        "TOTAL", tot, ps, fs, "PASS" if fs == 0 else "FAIL", w=width))

    failing = [r for r in results if r["failed"]]
    if failing:
        lines.append("")
        lines.append("FAILURES")
        for r in failing:
            lines.append("  %s (%d failed):" % (r["skill"], r["failed"]))
            for f in r["failures"]:
                lines.append("    - [%s] looked for %s" % (f["name"], f["marker"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Assert the 6 new skills still carry their load-bearing content.")
    ap.add_argument("--root", default=DEFAULT_ROOT,
                    help="skills directory (contains <skill>/SKILL.md). Default: %s" % DEFAULT_ROOT)
    ap.add_argument("--only", default=None, help="evaluate a single skill by name")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--verbose", action="store_true",
                    help="print every assertion, passing ones included")
    args = ap.parse_args(argv)

    if args.only and args.only not in SKILLS:
        sys.stderr.write("error: unknown skill %r. Known: %s\n"
                         % (args.only, ", ".join(sorted(SKILLS))))
        return 2

    results = eval_all(args.root, args.only)
    tot = sum(r["total"] for r in results)
    ps = sum(r["passed"] for r in results)
    fs = sum(r["failed"] for r in results)
    missing = [r["skill"] for r in results if r.get("skipped")]

    # A skipped skill contributes 0 failures, so without this guard an empty or
    # mistyped --root would report PASS with nothing asserted. Never pass vacuously.
    if missing:
        sys.stderr.write(
            "error: %d skill(s) not found under %s: %s\n"
            % (len(missing), args.root, ", ".join(missing)))
        if args.json:
            print(json.dumps({"root": args.root, "verdict": "ERROR",
                              "missing": missing, "assertions_total": tot,
                              "assertions_passed": ps, "assertions_failed": fs,
                              "results": results}, indent=2))
        return 2

    if args.json:
        payload = {
            "root": args.root,
            "skills": len(results),
            "assertions_total": tot,
            "assertions_passed": ps,
            "assertions_failed": fs,
            "verdict": "PASS" if fs == 0 else "FAIL",
            "results": results,
        }
        print(json.dumps(payload, indent=2))
        return 0 if fs == 0 else 1

    print("eval_skill_content — root: %s\n" % os.path.abspath(args.root))
    print(render_table(results))

    if args.verbose:
        print("")
        for r in results:
            print(r["skill"])
            for c in r["checks"]:
                print("  [%s] %-42s %s" % ("PASS" if c["pass"] else "FAIL",
                                           c["name"], c["marker"]))

    print("")
    print("OVERALL: %s (%d/%d assertions passed across %d skills)"
          % ("PASS" if fs == 0 else "FAIL", ps, tot, len(results)))
    return 0 if fs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())