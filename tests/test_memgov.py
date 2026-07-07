"""Tests for memgov scan / freshness / config / CLI."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from memgov import config as config_mod, freshness, scan as scan_mod
from memgov.__main__ import main as cli_main

SHARED = """# SHARED_STATE

| Fact | Current state (date) | Verify | Key (regex) |
|---|---|---|---|
| Paper X | **published** (2026-01-05, DOI 10.5281/x) | ledger.md | `Paper X\\|paper-x` |
| Tool chain | restored (2026-01-06) | `soffice --version` | `libfoo\\|LibreOffice` |
| Feature Y | drafting (2026-01-07) | branch feat-y | `Feature Y` |
"""


@pytest.fixture()
def ws(tmp_path: Path) -> config_mod.Config:
    (tmp_path / "SHARED_STATE.md").write_text(SHARED, encoding="utf-8")
    store = tmp_path / "store_a"
    store.mkdir()
    cfg = config_mod.Config(
        shared_state=tmp_path / "SHARED_STATE.md",
        out_dir=tmp_path / "gov",
        stores={"a": store},
    )
    return cfg


def _write(cfg: config_mod.Config, name: str, text: str,
           age_days: float = 0) -> Path:
    f = cfg.stores["a"] / name
    f.write_text(text, encoding="utf-8")
    if age_days:
        old = time.time() - age_days * 86400
        os.utime(f, (old, old))
    return f


def test_scan_flags_drift(ws):
    _write(ws, "m.md", "Paper X is still pending owner review.\n")
    result = scan_mod.scan(ws)
    assert len(result["findings"]) == 1
    fd = result["findings"][0]
    assert fd["entity"] == "Paper X"
    assert fd["file"] == "m.md" and fd["line"] == 1


def test_scan_skips_resolution_narration(ws):
    _write(ws, "m.md", "Paper X pending state was resolved on 2026-01-05.\n")
    assert scan_mod.scan(ws)["findings"] == []


def test_scan_skips_nonresolved_rows(ws):
    # "Feature Y" row is drafting (not resolved-type) => its pending
    # mentions are genuinely current, not drift.
    _write(ws, "m.md", "Feature Y is pending design sign-off.\n")
    assert scan_mod.scan(ws)["findings"] == []


def test_escaped_pipe_keys_parse(ws):
    rows, warnings = scan_mod.parse_shared_state(ws)
    assert warnings == []
    assert [r["entity"] for r in rows] == ["Paper X", "Tool chain"]
    assert rows[0]["key_re"].search("see paper-x notes")


def test_scan_writes_ledger_and_map(ws):
    _write(ws, "m.md", "LibreOffice is broken (libfoo missing).\n")
    result = scan_mod.scan(ws)
    scan_mod.write_outputs(ws, result)
    assert "Tool chain" in ws.conflict_map_path.read_text(encoding="utf-8")
    entry = json.loads(ws.ledger_path.read_text(encoding="utf-8"))
    assert entry["findings"] == 1 and entry["rows_watched"] == 2


def test_freshness_flags_old_status_files(ws):
    _write(ws, "old.md", "deployment pending\n", age_days=5)
    _write(ws, "new.md", "deployment pending\n")
    _write(ws, "plain.md", "nothing statusful here\n", age_days=30)
    hits = freshness.check(ws)
    assert [h["file"] for h in hits] == ["old.md"]
    assert hits[0]["age_days"] == 5


def test_freshness_suppression_marker(ws):
    _write(ws, "old.md", "deployment pending\n", age_days=5)
    freshness.mark_restored(ws, "a")
    assert freshness.check(ws) == []


def test_config_load_and_expansion(tmp_path):
    (tmp_path / "memgov.toml").write_text(
        '[memgov]\nshared_state = "S.md"\nextra_stale_markers = ["parked"]\n'
        '[stores]\nx = "mem"\n[freshness]\nstale_days = 7\n',
        encoding="utf-8")
    cfg = config_mod.load(tmp_path / "memgov.toml")
    assert cfg.shared_state == tmp_path / "S.md"
    assert cfg.stores["x"] == tmp_path / "mem"
    assert "parked" in cfg.stale_markers and "pending" in cfg.stale_markers
    assert cfg.freshness_stale_days == 7


def test_cli_hook_context(ws, tmp_path, capsys, monkeypatch):
    _write(ws, "m.md", "Paper X is still pending owner review.\n",
           age_days=5)
    toml = tmp_path / "memgov.toml"
    toml.write_text(
        f'[memgov]\nshared_state = "SHARED_STATE.md"\nout_dir = "gov"\n'
        f'[stores]\na = "store_a"\n', encoding="utf-8")
    rc = cli_main(["--config", str(toml), "hook-context"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "SHARED_STATE" in ctx          # table injected
    assert "memory-restore due" in ctx    # freshness section
    assert "suspected drift" in ctx       # scan summary


def test_cli_init_scaffolds(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli_main(["init"]) == 0
    assert (tmp_path / "memgov.toml").exists()
    assert (tmp_path / "SHARED_STATE.md").exists()
    # second run must not overwrite
    (tmp_path / "SHARED_STATE.md").write_text("edited", encoding="utf-8")
    assert cli_main(["init"]) == 0
    assert (tmp_path / "SHARED_STATE.md").read_text(
        encoding="utf-8") == "edited"
