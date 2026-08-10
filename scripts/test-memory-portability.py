#!/usr/bin/env python3
"""Bet 6 verification — memory portability + anti-data-loss.

Tests (all isolated in a temp store, real store untouched except a read-only
export sanity check):
  1. export -> wipe -> import restores an identical store
  2. re-import is idempotent (0 added, all duplicates skipped)
  3. backup() writes restorable timestamped snapshots + a valid manifest
  4. import rejects a non-bundle JSON file (ValueError)
  5. live-store export sanity check (parses, stats match line count)

Run: python3 scripts/test-memory-portability.py   (exit 0 = pass)
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shared.memory_controller as mc_mod
from shared.memory_controller import MemoryController


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def main():
    orig_ep, orig_sem, orig_mdir = mc_mod.EPISODIC_DB, mc_mod.SEMANTIC_DB, mc_mod.MEMORY_DIR
    tmp = Path(tempfile.mkdtemp(prefix="aether-mem-test-"))
    try:
        # --- isolate a fresh store for round-trip tests ---
        mc_mod.MEMORY_DIR = tmp / "memory"
        mc_mod.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        mc_mod.EPISODIC_DB = tmp / "memory" / "episodic_memory.jsonl"
        mc_mod.SEMANTIC_DB = tmp / "memory" / "semantic_memory.json"
        mc_mod.EPISODIC_DB.write_text(
            json.dumps({"timestamp": 0.0, "task": "seed", "action": "bootstrap",
                        "outcome": "ok", "metadata": {}}) + "\n")
        mc_mod.SEMANTIC_DB.write_text(json.dumps({"entities": {}, "relations": []}))
        mc = MemoryController()

        # Test 1: round-trip restore
        mc.store_experience("round-trip marker", "store a", "ok", {"k": "v"})
        mc.store_experience("round-trip marker", "store b", "ok")
        mc.store_fact("aether", "supports", "portability")
        bundle_path = tmp / "export.json"
        bund = mc.export_memory(bundle_path)
        assert bund["stats"]["episodic"] == 3, bund["stats"]
        assert bund["stats"]["semantic_relations"] == 1, bund["stats"]

        mc_mod.EPISODIC_DB.unlink()
        mc_mod.SEMANTIC_DB.write_text(json.dumps({"entities": {}, "relations": []}))

        res = mc.import_memory(bundle_path)
        assert res["episodic_added"] == 3, res
        assert res["episodic_skipped_duplicates"] == 0, res
        assert res["semantic_relations_added"] == 1, res
        loaded = mc._load_experiences()
        assert len(loaded) == 3, f"expected 3 after restore, got {len(loaded)}"
        assert any(e["task"] == "round-trip marker" for e in loaded)
        assert any(r["p"] == "supports" for r in mc._load_semantic()["relations"])

        # Test 2: idempotent re-import (anti-data-loss guarantee)
        res2 = mc.import_memory(bundle_path)
        assert res2["episodic_added"] == 0, res2
        assert res2["episodic_skipped_duplicates"] == 3, res2
        assert len(mc._load_experiences()) == 3, "duplicates after re-import!"

        # Test 3: backup snapshots + manifest
        b = mc.backup()
        bdir = Path(b["backup_dir"])
        manifests = list(bdir.glob("manifest.*.json"))
        assert manifests, "no manifest written"
        man = json.loads(manifests[-1].read_text())
        assert man["format"] == "aether-memory" and man["type"] == "backup"
        assert man["episodic_entries"] == 3, man
        assert (bdir / man["episodic"]).exists()
        assert (bdir / man["semantic"]).exists()
        # restore from raw snapshot === restore from bundle
        restored = [json.loads(l) for l in (bdir / man["episodic"]).open() if l.strip()]
        assert len(restored) == 3, f"backup restore: {len(restored)}"

        # Test 4: reject non-bundle
        bad = tmp / "bad.json"
        bad.write_text(json.dumps({"foo": 1}))
        try:
            mc.import_memory(bad)
            fail("import accepted a non-bundle file")
        except ValueError:
            pass

        # Test 5: live-store export sanity check (read-only)
        mc_mod.EPISODIC_DB, mc_mod.SEMANTIC_DB = orig_ep, orig_sem
        live = MemoryController()
        live_bundle = live.export_memory(tmp / "live_export.json")
        n_lines = sum(1 for l in orig_ep.open() if l.strip())
        assert live_bundle["stats"]["episodic"] == n_lines, (
            f"live stats {live_bundle['stats']['episodic']} != lines {n_lines}")
        print(f"PASS: all memory portability tests green "
              f"(live store: {live_bundle['stats']['episodic']} episodic, "
              f"{live_bundle['stats']['semantic_relations']} semantic relations)")
        return 0
    finally:
        mc_mod.EPISODIC_DB, mc_mod.SEMANTIC_DB, mc_mod.MEMORY_DIR = orig_ep, orig_sem, orig_mdir
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())