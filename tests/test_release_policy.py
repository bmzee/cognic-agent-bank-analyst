"""Pins the protected dual-custody release lane for the agent pack."""

from __future__ import annotations

import pathlib
import re
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "sign-and-publish.yml"
KERNEL_REVISION = "1402e7dc67cf4532df748a99a4d7f472e430e644"


def _normalized_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9._-]+", requirement)
    assert match is not None
    return match.group(0).lower().replace("_", "-")


def test_release_workflow_is_dispatch_only_versioned_and_protected() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    trigger = workflow.split("\non:\n", maxsplit=1)[1].split("\npermissions:\n", maxsplit=1)[0]
    assert re.search(r"(?m)^  workflow_dispatch:$", trigger)
    assert re.search(r"(?m)^      version:$", trigger)
    assert not re.search(r"(?m)^  (?:push|pull_request|release|schedule):", trigger)
    assert "validate-request:" in workflow
    assert re.search(r"(?m)^    environment: release$", workflow)
    assert "requested version does not match pyproject.toml" in workflow
    assert "release tag already exists" in workflow
    assert "GitHub release already exists" in workflow
    assert "committed cosign.pub trust root is missing or empty" in workflow
    assert "committed agent-card.pub trust root is missing or empty" in workflow


def test_release_workflow_installs_the_pinned_supply_chain_toolchain() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "COSIGN_VERSION=3.0.6" in workflow
    assert "c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74" in workflow
    assert "SYFT_VERSION=1.45.1" in workflow
    assert "20c84195e24927f50a3b2269946be51f4c4abc9d2f145fee7388b4199149f716" in workflow
    assert "GRYPE_VERSION=0.114.0" in workflow
    assert "edda0968d8827daab01d32b3cd7de192ae0915005e7bbfcfef9e68e79bc43343" in workflow
    assert workflow.count("sha256sum -c -") == 3
    assert "pip-licenses --version" in workflow


def test_release_workflow_proves_both_custody_roots_before_signing() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "COSIGN_PRIVATE_KEY: ${{ secrets.PRIMARY_COSIGN_PRIVATE_KEY }}" in workflow
    assert "COSIGN_PASSWORD: ${{ secrets.PRIMARY_COSIGN_PASSWORD }}" in workflow
    assert (
        "AGENT_CARD_JWS_ENCRYPTED_PRIVATE_KEY: "
        "${{ secrets.PRIMARY_AGENT_CARD_JWS_ENCRYPTED_PRIVATE_KEY }}" in workflow
    )
    assert "AGENT_CARD_JWS_PASSWORD: ${{ secrets.PRIMARY_AGENT_CARD_JWS_PASSWORD }}" in workflow
    assert 'chmod 0600 "$COGNIC_SIGNING_KEY_PATH"' in workflow
    assert 'chmod 0600 "$COGNIC_AGENT_CARD_JWS_SIGNING_KEY_PATH"' in workflow
    assert "-passin env:AGENT_CARD_JWS_PASSWORD" in workflow
    assert 'cosign public-key --key "$COGNIC_SIGNING_KEY_PATH"' in workflow
    assert 'cmp -s "$RUNNER_TEMP/derived-cosign.pub" cosign.pub' in workflow
    assert '-in "$COGNIC_AGENT_CARD_JWS_SIGNING_KEY_PATH"' in workflow
    assert '-out "$RUNNER_TEMP/derived-agent-card.pub"' in workflow
    assert 'cmp -s "$RUNNER_TEMP/derived-agent-card.pub" agent-card.pub' in workflow
    assert workflow.index("Verify both private keys derive") < workflow.index(
        "uv run --extra dev agentos sign --bundle ."
    )
    assert "if: always()" in workflow
    assert '"${COGNIC_SIGNING_KEY_PATH:-}"' in workflow
    assert '"${COGNIC_AGENT_CARD_JWS_SIGNING_KEY_PATH:-}"' in workflow
    assert '"$RUNNER_TEMP/agent-card.enc.key"' in workflow


def test_agent_release_builds_signs_verifies_and_publishes_complete_assets() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "uv lock --check" in workflow
    assert "uv sync --frozen --extra dev" in workflow
    assert "uv build --wheel" in workflow
    assert "agentos sign --bundle ." in workflow
    assert "agentos verify --trust-root cosign.pub ." in workflow
    assert 'gh release create "$tag"' in workflow
    for asset in (
        "cosign.pub",
        "agent-card.pub",
        "agent_cards/agent-card.json",
        "agent_cards/agent-card.jws",
    ):
        assert asset in workflow


def test_release_inventory_is_frozen_and_kernel_pin_is_full_length() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dev = project["project"]["optional-dependencies"]["dev"]
    assert "pip-licenses" in {_normalized_name(item) for item in dev}
    assert [item for item in dev if item.startswith("cognic-agentos @")] == [
        "cognic-agentos @ git+https://github.com/bmzee/cognic-agentos@" + KERNEL_REVISION
    ]

    assert (ROOT / "uv.lock").is_file()
    ignored = {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "uv.lock" not in ignored

    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    root_package = next(item for item in lock["package"] if item.get("source") == {"editable": "."})
    locked_dev = root_package["optional-dependencies"]["dev"]
    assert "pip-licenses" in {str(item["name"]).lower().replace("_", "-") for item in locked_dev}
    kernel = next(item for item in lock["package"] if item["name"] == "cognic-agentos")
    assert kernel["source"] == {
        "git": f"https://github.com/bmzee/cognic-agentos?rev={KERNEL_REVISION}#{KERNEL_REVISION}"
    }
