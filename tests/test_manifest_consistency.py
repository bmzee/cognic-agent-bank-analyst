"""Manifest ↔ pyproject ↔ declarative-agent invariants.

Mirrors what the kernel enforces so drift fails HERE first:
``cli/validators/agents.py`` (the M8 A8 [agent]-block arms — persona_path /
requested_skills / requested_tools / max_steps), ``cli/validators/identity.py``
(the agent-pack-only AgentCard fields), ``cli/validate.py`` (the A8 kind
constraint: NO [mcp] block on agent packs), and the runtime hosting layer
(``harness/agent_host.py`` + ``protocol/agent_manifest.py`` read AGENT.md +
the manifest as wheel package data). Also pins the no-runtime-dependencies
wheel doctrine and the single-inert-marker entry-point contract.
"""

from __future__ import annotations

import json
import pathlib
import tomllib
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DISTRIBUTION = "cognic-agent-bank-analyst"
_PACKAGE = "cognic_agent_bank_analyst"
_REQUESTED_SKILLS = ["customer-data", "financial-data", "cards-data"]
_REQUESTED_TOOL = "cognic-tool-oracle-schema/run_readonly_query"
_NEVER_GRANTED_SKILL = "atm-recon"


def _manifest() -> dict[str, Any]:
    return tomllib.loads((_ROOT / "cognic-pack-manifest.toml").read_text(encoding="utf-8"))


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_pack_kind_is_agent() -> None:
    assert _manifest()["pack"]["kind"] == "agent"
    assert _manifest()["pack"]["pack_id"] == _DISTRIBUTION


def test_persona_path_is_agent_md() -> None:
    """The runtime hosting layer resolves the persona through
    [agent].persona_path; the conventional AGENT.md ships tracked at the
    pack root (cli/validators/agents.py parse+shape-validates it at build
    time, so it can never be a gitignored/seeded artifact)."""
    assert _manifest()["agent"]["persona_path"] == "AGENT.md"
    assert (_ROOT / "AGENT.md").is_file()


def test_agent_block_requests_exactly_the_three_data_skills() -> None:
    """The requested_skills ceiling is EXACT (order included): the three
    governed data domains the persona teaches. The kernel ingestion
    invariant (core/agent/assignments.py) refuses any tenant grant outside
    this set."""
    assert _manifest()["agent"]["requested_skills"] == _REQUESTED_SKILLS


def test_atm_recon_is_never_requested() -> None:
    """The dedicated NEVER pin: atm-recon must not appear anywhere in the
    [agent] request ceilings. The M8 proof depends on this agent being
    UNGRANTABLE for the atm_recon scope — a grant row naming it trips the
    kernel's grant-not-requested refusal instead of widening the agent."""
    agent_block = _manifest()["agent"]
    assert _NEVER_GRANTED_SKILL not in agent_block["requested_skills"]
    assert all(_NEVER_GRANTED_SKILL not in tool for tool in agent_block["requested_tools"])


def test_requested_tools_is_exactly_the_governed_query_tool() -> None:
    """One requested tool: the governed read-only SQL leg. The
    <server_id>/<tool_name> identity follows the kernel's
    first-'/'-partition rule (cli/validators/agents.py)."""
    assert _manifest()["agent"]["requested_tools"] == [_REQUESTED_TOOL]


def test_max_steps_is_six() -> None:
    """max_steps=6 (in the kernel's 1..32 closed bounds; bool is NOT an
    int there — pin the exact type here too)."""
    steps = _manifest()["agent"]["max_steps"]
    assert steps == 6
    assert isinstance(steps, int) and not isinstance(steps, bool)


def test_risk_tier_is_customer_data_read() -> None:
    assert _manifest()["risk_tier"]["tier"] == "customer_data_read"


def test_data_governance_contract() -> None:
    governance = _manifest()["data_governance"]
    assert governance["data_classes"] == ["customer_pii", "internal"]
    assert governance["purpose"] == "customer_support"
    assert governance["retention_policy"] == "task_only"
    assert governance["retention_max_window"] == 1
    assert governance["egress_allow_list"] == []


def test_tier_satisfies_the_kernel_minimum_for_every_declared_class() -> None:
    """ADR-014 cross-check mirrored from the kernel vocabulary:
    customer_pii's minimum tier IS customer_data_read, so the declared
    tier sits exactly at (never below) the kernel's
    DATA_CLASS_TO_MIN_RISK_TIER floor, and outside the low-authority set
    the restricted-class cross-check refuses."""
    from cognic_agentos.cli._governance_vocab import (
        DATA_CLASS_TO_MIN_RISK_TIER,
        LOW_AUTHORITY_TIERS,
        RISK_TIER_ORDER,
    )

    tier = _manifest()["risk_tier"]["tier"]
    assert tier not in LOW_AUTHORITY_TIERS
    for klass in _manifest()["data_governance"]["data_classes"]:
        minimum = DATA_CLASS_TO_MIN_RISK_TIER.get(klass)
        if minimum is not None:
            assert RISK_TIER_ORDER.index(tier) >= RISK_TIER_ORDER.index(minimum)


def test_identity_block_carries_the_agent_mandatory_fields() -> None:
    """The AGNTCY/OASF Wave-1 agent matrix: the four universal fields PLUS
    the two agent-pack-only card fields (cli/validators/identity.py refuses
    an agent pack without them)."""
    identity = _manifest()["identity"]
    assert identity["agent_id"] == f"did:web:github.com:bmzee:{_DISTRIBUTION}"
    assert identity["display_name"] == "Cognic Agent Bank Analyst"
    assert identity["provider_organization"] == "Cognic"
    assert identity["provider_url"] == f"https://github.com/bmzee/{_DISTRIBUTION}"
    assert identity["agent_card_url"] == (
        f"https://github.com/bmzee/{_DISTRIBUTION}/releases/download/v0.1.0/agent-card.jws"
    )
    assert identity["agent_card_jws_path"] == "agent_cards/agent-card.jws"


def test_no_mcp_block_at_either_manifest_path() -> None:
    """A8 kind constraint (cli/validate.py): agent packs are not
    MCP-tool-shaped; [mcp] at either the canonical or the legacy
    [tool.cognic.mcp] path is an orchestrator refusal
    (agent_pack_kind_constraint_violated)."""
    data = _manifest()
    assert "mcp" not in data
    assert "mcp" not in data.get("tool", {}).get("cognic", {})


def test_no_skill_block_at_either_manifest_path() -> None:
    """An agent pack hosts a persona, not a skill: no [skill] block at
    either path (the skills validator fires its arms on block presence for
    every pack kind — an accidental block would drag skill-mode refusals
    onto this pack)."""
    data = _manifest()
    assert "skill" not in data
    assert "skill" not in data.get("tool", {}).get("cognic", {})


def test_supply_chain_is_sign_ready() -> None:
    """The manifest declares the canonical attestation paths that
    `agentos sign --bundle .` populates at release (the sibling B1/B2
    shape; blob_path is sign-emitted at release, never authored)."""
    assert _manifest()["supply_chain"]["attestation_paths"] == [
        "attestations/cosign.sig",
        "attestations/sbom.cdx.json",
    ]


def test_agent_card_signing_payload_is_tracked_source() -> None:
    """`agentos sign --bundle .` signs agent_cards/agent-card.json
    (cli/sign.py) into the manifest-declared JWS path at release; the JSON
    payload is SOURCE and must ship in the repo with the pack identity."""
    card = json.loads((_ROOT / "agent_cards" / "agent-card.json").read_text(encoding="utf-8"))
    assert card["name"] == "Cognic Agent Bank Analyst"
    assert card["version"] == "0.1.0"
    assert card["provider"]["organization"] == "Cognic"
    assert [skill["id"] for skill in card["skills"]] == _REQUESTED_SKILLS


def test_wheel_declares_no_runtime_dependencies() -> None:
    """No-runtime-dependencies doctrine: the wheel exists solely to carry
    AGENT.md + manifest (+ the inert marker) through the signed-pack
    pipeline and must install with plain `pip --no-deps`. The kernel pin is
    an author/CI-time dev extra only — and it must be a RESOLVABLE remote
    git reference (not a bare name relying on a machine-local
    [tool.uv.sources] redirect), or the CI lanes' `uv sync --extra dev`
    cannot resolve it on a runner."""
    data = _pyproject()
    project = data["project"]
    assert project["dependencies"] == []
    kernel_deps = [
        dep
        for dep in project["optional-dependencies"]["dev"]
        if dep.split("@")[0].strip() == "cognic-agentos"
    ]
    assert len(kernel_deps) == 1
    assert kernel_deps[0].startswith(
        "cognic-agentos @ git+https://github.com/bmzee/cognic-agentos@"
    )
    # No machine-local source redirect may shadow the git ref (a path source
    # would break `uv sync` on any machine without the sibling checkout).
    assert "cognic-agentos" not in data.get("tool", {}).get("uv", {}).get("sources", {})


def test_agent_md_and_manifest_ship_as_wheel_package_data() -> None:
    """The hosting layer reads <pkg>/AGENT.md
    (protocol/agent_manifest.extract_agent_md) + <pkg>/cognic-pack-manifest.toml
    (protocol/mcp_manifest.extract_pack_manifest) from the INSTALLED wheel
    without importing pack code; the hatchling force-include mapping is
    what puts them there. agent_cards/ deliberately stays OUT of the wheel
    (the JWS is resolved against the pack/bundle root, never wheel-read)."""
    wheel = _pyproject()["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == [f"src/{_PACKAGE}"]
    force_include = wheel["force-include"]
    assert force_include["AGENT.md"] == f"{_PACKAGE}/AGENT.md"
    assert force_include["cognic-pack-manifest.toml"] == f"{_PACKAGE}/cognic-pack-manifest.toml"
    assert not any("agent_cards" in source for source in force_include)


def test_entry_point_is_the_inert_marker_in_cognic_agents_only() -> None:
    """Exactly ONE entry-point group (cognic.agents) with exactly ONE
    entry: the inert marker. No cognic.tools / cognic.skills /
    cognic.hooks — an agent pack has no other discovery surface."""
    entry_points = _pyproject()["project"]["entry-points"]
    assert list(entry_points.keys()) == ["cognic.agents"]
    assert entry_points["cognic.agents"] == {
        "bank-analyst": f"{_PACKAGE}.marker:AGENT_MARKER",
    }
