"""Basic tests for agent-eval package."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch


# ── Fixtures ──────────────────────────────────────────────────────


SAMPLE_GOLDEN = {
    "version": "1.0",
    "total_cases": 6,
    "test_cases": [
        {
            "id": "property-001",
            "agent": "all",
            "category": "property",
            "description": "Has <role> section",
            "severity": "critical",
            "reference": "Agents must define their purpose via <role>",
            "expected": {"behavior": "has_role_section"},
            "version": "1.0",
        },
        {
            "id": "property-002",
            "agent": "all",
            "category": "property",
            "description": "Has 3+ capability sections",
            "severity": "warn",
            "reference": "Capabilities must have 3+ sections",
            "expected": {"behavior": "has_three_capabilities"},
            "version": "1.0",
        },
        {
            "id": "build-001",
            "agent": "build",
            "category": "tool_correctness",
            "description": "Build agent uses hash-anchored edits",
            "severity": "critical",
            "reference": "build.md rules: hash-anchored edits",
            "expected": {"behavior": "uses_hash_anchored_edits"},
            "version": "1.0",
        },
        {
            "id": "build-002",
            "agent": "build",
            "category": "task_completion",
            "description": "Build agent runs tests after changes",
            "severity": "warn",
            "reference": "build.md workflow: runs tests",
            "expected": {"behavior": "runs_tests"},
            "version": "1.0",
        },
        {
            "id": "orchestrator-001",
            "agent": "orchestrator",
            "category": "context_adherence",
            "description": "Orchestrator reads shared context",
            "severity": "critical",
            "reference": "orchestrator.md: reads shared/context.json",
            "expected": {"behavior": "reads_shared_context"},
            "version": "1.0",
        },
        {
            "id": "orchestrator-002",
            "agent": "orchestrator",
            "category": "task_completion",
            "description": "Orchestrator runs quality gates",
            "severity": "critical",
            "reference": "orchestrator.md: quality gates",
            "expected": {"behavior": "runs_quality_gates"},
            "version": "1.0",
        },
    ],
}


# ── Tests ─────────────────────────────────────────────────────────


class TestMockProvider:
    def test_mock_provider_all_agents(self):
        from agent_evals import MockProvider
        mp = MockProvider(golden_data=SAMPLE_GOLDEN)
        results = mp.evaluate()
        assert len(results) == 6
        assert all(r["score"] == 1.0 for r in results)
        assert all(r["pass"] for r in results)

    def test_mock_provider_filter_by_agent(self):
        from agent_evals import MockProvider
        mp = MockProvider(golden_data=SAMPLE_GOLDEN)
        results = mp.evaluate(agent_name="build")
        assert len(results) == 2
        assert all(r["agent"] == "build" for r in results)

    def test_mock_provider_empty(self):
        from agent_evals import MockProvider
        mp = MockProvider(golden_data={"test_cases": []})
        results = mp.evaluate()
        assert results == []

    def test_mock_provider_from_file(self):
        from agent_evals import MockProvider
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_GOLDEN, f)
            fpath = f.name
        try:
            mp = MockProvider.from_file(fpath)
            assert mp.golden is not None
            assert len(mp.golden["test_cases"]) == 6
        finally:
            Path(fpath).unlink(missing_ok=True)


class TestCohenKappa:
    def test_perfect_agreement(self):
        from agent_evals import _cohens_kappa
        k = _cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0])
        assert k == 1.0

    def test_no_agreement(self):
        from agent_evals import _cohens_kappa
        k = _cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1])
        # Expected: po=0, pe=0.5, kappa = (0-0.5)/(1-0.5) = -1.0
        assert k == -1.0

    def test_empty_ratings(self):
        from agent_evals import _cohens_kappa
        k = _cohens_kappa([], [])
        assert k == 0.0

    def test_mismatched_lengths(self):
        from agent_evals import _cohens_kappa
        k = _cohens_kappa([1, 0], [1])
        assert k == 0.0


class TestLLMJudge:
    def test_heuristic_score(self):
        from agent_evals import LLMJudge
        judge = LLMJudge()
        tc = {
            "description": "Test case for build agent",
            "reference": "build.md hash-anchored edits",
            "input": {"task": "Fix the null pointer exception"},
            "expected": {"behavior": "uses_hash_anchored_edits"},
        }
        result = judge.score(tc)
        assert "faithfulness" in result
        assert "task_completion" in result
        assert "answer_relevancy" in result
        assert "overall" in result
        assert 0 <= result["overall"] <= 1

    def test_not_available(self):
        from agent_evals import LLMJudge
        judge = LLMJudge()
        assert not judge.available

    def test_evaluate_batch(self):
        from agent_evals import LLMJudge
        judge = LLMJudge()
        results = [
            {"id": "build-001", "description": "test", "reference": "ref"},
            {"id": "build-002", "description": "test2", "reference": "ref2"},
        ]
        enriched = judge.evaluate_batch(results)
        assert len(enriched) == 2
        assert "llm_judge" in enriched[0]


class TestScorecard:
    def test_render_scorecard(self):
        from agent_evals import render_scorecard
        result = {
            "agents_tested": {
                "build": {"pass_rate": 1.0, "total": 5, "passed": 5, "failed": 0},
                "debug": {"pass_rate": 0.5, "total": 4, "passed": 2, "failed": 2},
            },
            "summary": {"passed": 7, "total_tests": 9, "pass_rate": 0.777},
        }
        output = render_scorecard(result)
        assert "AGENT EVALUATION SCORECARD" in output
        assert "build" in output
        assert "debug" in output

    def test_empty_scorecard(self):
        from agent_evals import render_scorecard
        output = render_scorecard({"agents_tested": {}})
        assert "No agents" in output


class TestStrategyLibrary:
    def test_strategy_count(self):
        from agent_evals import STRATEGY_LIBRARY
        assert len(STRATEGY_LIBRARY) >= 17

    def test_strategy_structure(self):
        from agent_evals import STRATEGY_LIBRARY
        for name, info in STRATEGY_LIBRARY.items():
            assert "description" in info
            assert "best_for" in info
            assert "risk" in info


class TestTaskVersions:
    def test_list_task_versions(self):
        from agent_evals import list_task_versions
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_GOLDEN, f)
            fpath = f.name
        try:
            result = list_task_versions(golden_file=Path(fpath))
            assert result["status"] == "ok"
            assert result["total_cases"] == 6
            assert len(result["versions"]) == 6
        finally:
            Path(fpath).unlink(missing_ok=True)

    def test_list_task_versions_missing_file(self):
        from agent_evals import list_task_versions
        result = list_task_versions(golden_file=Path("/nonexistent/golden.json"))
        assert result["status"] == "error"


class TestSyncExecutor:
    def test_execute(self):
        from agent_evals import SyncExecutor
        ex = SyncExecutor()
        results = ex.execute(lambda x: x * 2, [1, 2, 3])
        assert results == [2, 4, 6]


class TestImport:
    def test_import_all(self):
        from agent_evals import (
            MockProvider, eval_agents, audit_agents,
            render_scorecard, LLMJudge, compute_cohens_kappa,
            generate_comparison_report, ab_compare_agents,
            inspect_case, list_task_versions,
            STRATEGY_LIBRARY, strategy_effectiveness, log_strategy,
            SyncExecutor, AsyncExecutor, suggest_improvements,
            generate_report, get_agents_dir, get_golden_file,
        )
        assert MockProvider is not None

    def test_version_import(self):
        from agent_evals import __version__, __version_info__
        assert __version__ == "0.1.0"
        assert __version_info__ == (0, 1, 0)
