"""AGENT.md shape + persona-content pins, via the kernel's own contract.

The persona document shares the SKILL.md frontmatter wire contract
(``protocol/agent_manifest.py`` re-exports ``parse_skill_md`` /
``validate_skill_md`` — the same objects, not a fork), and the runtime
hosting layer (``harness/agent_host.py``) keys the hosted agent by the
frontmatter ``name``. The content pins hold the persona to the
governed-data-only doctrine: answer only from governed query results,
refuse plainly when a capability or data scope is unavailable, never
fabricate a figure.
"""

from __future__ import annotations

import pathlib
import re
from typing import Any

from cognic_agentos.protocol.agent_manifest import parse_skill_md, validate_skill_md

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_AGENT_ID = "bank-analyst"
_DECLARED_SENTENCE = (
    "Bank data analyst answering customer, deposit, finance and card questions "
    "strictly from governed data; selects the matching granted skill, authors "
    "read-only SQL over its governed views, and reports only figures returned "
    "by run_readonly_query."
)


def _agent_md_text() -> str:
    return (_ROOT / "AGENT.md").read_text(encoding="utf-8")


def _frontmatter_and_body() -> tuple[dict[str, Any], str]:
    return parse_skill_md(_agent_md_text())


def test_agent_md_parses_and_validates_against_the_kernel_shape() -> None:
    frontmatter, body = _frontmatter_and_body()
    # Raises SkillManifestInvalid on any shape violation; clean return == valid.
    validate_skill_md(frontmatter, body=body)


def test_frontmatter_name_is_the_runtime_agent_id() -> None:
    """harness/agent_host.py hosts the record under frontmatter['name'] —
    this IS the agent_id the ask surface + the tenant assignment rows key
    by, and it must match the agentskills.io label shape."""
    frontmatter, _body = _frontmatter_and_body()
    assert frontmatter["name"] == _AGENT_ID
    assert re.fullmatch(r"[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?", frontmatter["name"])


def test_frontmatter_description_is_the_declared_hook() -> None:
    frontmatter, _body = _frontmatter_and_body()
    assert frontmatter["description"] == _DECLARED_SENTENCE
    assert len(frontmatter["description"]) <= 1024


def test_persona_answers_only_from_governed_data() -> None:
    _frontmatter, body = _frontmatter_and_body()
    assert "strictly from governed data" in body
    assert "never answer a data question from memory" in body


def test_persona_teaches_the_governed_dispatch_loop() -> None:
    """The behavioral spine: read the matching skill, author SQL over its
    governed views only, execute through the governed tool with the
    skill's scope_id."""
    _frontmatter, body = _frontmatter_and_body()
    assert "`read_skill`" in body
    assert "`run_readonly_query`" in body
    assert "`scope_id`" in body


def test_persona_refuses_plainly_and_never_fabricates() -> None:
    _frontmatter, body = _frontmatter_and_body()
    assert "say so plainly and stop" in body
    assert "Never fabricate numbers" in body


def test_persona_covers_each_requested_skill_domain() -> None:
    """The persona names the three granted DOMAINS (deliberately not the
    skill ids — grants are runtime; the loop injects granted skill names +
    descriptions into the system prompt)."""
    _frontmatter, body = _frontmatter_and_body()
    lowered = body.lower()
    for domain_word in ("deposit", "general-ledger", "card"):
        assert domain_word in lowered, f"persona must cover the {domain_word} domain"


def test_persona_never_names_the_ungrated_atm_domain() -> None:
    """Negative pin mirroring the manifest's NEVER-atm-recon rule: the
    persona must not teach or hint at the ungrantable atm_recon domain."""
    assert "atm" not in _agent_md_text().lower()


def test_persona_stays_read_only() -> None:
    _frontmatter, body = _frontmatter_and_body()
    assert "no DML, DDL, PL/SQL" in body
