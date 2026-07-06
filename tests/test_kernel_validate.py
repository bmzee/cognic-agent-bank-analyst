"""Drive the REAL kernel build-time gate against this pack.

Three entry depths: the M8 A8 per-concern agents validator directly
against the live repo root (persona resolve-then-validate + requested-set
arms — AGENT.md is tracked, so no seeding needed), the FULL
``run_validators`` orchestrator against a tmp replica seeded with the
release-artifact placeholders the ci.yml authoring-validate lane seeds
(attestations + the AgentCard JWS) — plus the warning-set pin the lane's
exit code cannot express — and two negative pins: the A8 kind constraint
([mcp] on an agent pack refuses) and the JWS-placeholder rationale (the
identity validator refuses when the seeded JWS file is absent).
"""

from __future__ import annotations

import pathlib
import shutil
import tomllib
from typing import Any

from cognic_agentos.cli.validate import run_validators
from cognic_agentos.cli.validators.agents import validate as validate_agent_block

_ROOT = pathlib.Path(__file__).resolve().parents[1]

_PLACEHOLDER_SBOM = '{"bomFormat":"CycloneDX","specVersion":"1.5","version":1}\n'


def _manifest_text() -> str:
    return (_ROOT / "cognic-pack-manifest.toml").read_text(encoding="utf-8")


def _seed_replica(tmp_path: pathlib.Path, manifest_text: str) -> pathlib.Path:
    """Replicate the pack root + seed the gitignored release artifacts the
    ci.yml authoring-validate lane seeds on the runner (placeholder
    attestations + the placeholder AgentCard JWS)."""
    (tmp_path / "cognic-pack-manifest.toml").write_text(manifest_text, encoding="utf-8")
    shutil.copy(_ROOT / "AGENT.md", tmp_path / "AGENT.md")
    (tmp_path / "agent_cards").mkdir()
    shutil.copy(
        _ROOT / "agent_cards" / "agent-card.json",
        tmp_path / "agent_cards" / "agent-card.json",
    )
    (tmp_path / "agent_cards" / "agent-card.jws").write_text(
        "release-placeholder\n", encoding="utf-8"
    )
    (tmp_path / "attestations").mkdir()
    (tmp_path / "attestations" / "cosign.sig").write_text("release-placeholder\n", encoding="utf-8")
    (tmp_path / "attestations" / "sbom.cdx.json").write_text(_PLACEHOLDER_SBOM, encoding="utf-8")
    return tmp_path


def test_kernel_agents_validator_accepts_the_live_pack_root() -> None:
    """The A8 [agent]-block validator (persona resolve-then-validate +
    build-time AGENT.md parse, requested_skills / requested_tools /
    max_steps arms) against the LIVE repo root: zero findings (this
    validator has no warning paths)."""
    manifest: dict[str, Any] = tomllib.loads(_manifest_text())
    findings = validate_agent_block(manifest, _ROOT)
    assert findings == [], f"kernel agents validator flagged: {findings}"


def test_full_kernel_validate_passes_with_seeded_release_placeholders(
    tmp_path: pathlib.Path,
) -> None:
    """The whole orchestrator (shape gate + kind constraints + all
    per-concern validators): zero refusals, and EXACTLY the one by-design
    Wave-1 warning — oasf_capability_set is optional-Wave-1 /
    mandatory-Wave-2 (mirrors the sibling packs' posture)."""
    replica = _seed_replica(tmp_path, _manifest_text())
    findings = run_validators(replica)
    refusals = [f for f in findings if f.severity == "refusal"]
    assert refusals == [], f"kernel validate refused: {refusals}"
    assert [f.reason for f in findings if f.severity == "warning"] == [
        "identity_oasf_capability_set_missing"
    ]


def test_kernel_refuses_an_mcp_block_on_this_agent_pack(tmp_path: pathlib.Path) -> None:
    """The A8 kind constraint (cli/validate.py): agent packs are not
    MCP-tool-shaped; smuggling an [mcp] block into THIS manifest trips
    agent_pack_kind_constraint_violated (failure_mode=mcp_block_forbidden)."""
    mutated = _manifest_text() + "\n[mcp]\ncaching = false\n"
    replica = _seed_replica(tmp_path, mutated)
    findings = run_validators(replica)
    hits = [f for f in findings if f.reason == "agent_pack_kind_constraint_violated"]
    assert len(hits) == 1
    assert hits[0].severity == "refusal"
    assert hits[0].payload["failure_mode"] == "mcp_block_forbidden"


def test_kernel_refuses_the_pack_without_the_agent_card_jws(tmp_path: pathlib.Path) -> None:
    """Negative pin for the placeholder-seeding decision: WITHOUT the
    seeded JWS file the identity validator refuses
    (identity_agent_card_jws_path_unresolvable / file_not_found) — exactly
    why the ci.yml lane seeds it and the README documents local seeding;
    the real JWS is an `agentos sign` release output, never committed."""
    replica = _seed_replica(tmp_path, _manifest_text())
    (replica / "agent_cards" / "agent-card.jws").unlink()
    findings = run_validators(replica)
    assert any(
        f.reason == "identity_agent_card_jws_path_unresolvable"
        and f.payload["failure_mode"] == "file_not_found"
        for f in findings
    )
