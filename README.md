# cognic-agent-bank-analyst

A **declarative governed agent** for Cognic AgentOS (M8, ADR-027). The
pack is a persona, not a program: `AGENT.md` declares WHO the agent is (a
bank data analyst that answers only from governed data and can propose the
asking user's own leave request) and the signed manifest declares WHAT it
requests (six instruction skills + the governed query tool + the approval-
gated leave tool + a step ceiling). **The AgentOS kernel owns the
reasoning loop and every dispatch decision** — there is no agent code
here beyond an inert `cognic.agents` marker the plugin registry
discovers.

| aspect | value |
|---|---|
| `AGENT.md` name (the runtime agent id) | `bank-analyst` |
| requested skills (ceiling, not grant) | `customer-data`, `financial-data`, `cards-data`, `hr-data`, `orders-data`, `warehouse-data` |
| requested tools | `cognic-tool-oracle-schema/run_readonly_query`, `cognic-tool-hr-leave/apply_leave` |
| `max_steps` | `6` |
| risk tier | `customer_data_read` |
| data classes | `customer_pii`, `internal` |
| entry point | `cognic.agents` → inert marker only (no loop code, no tool clients) |

## What "declarative" means (ADR-027)

An M8 agent pack hosts identity + intent, never execution:

- `AGENT.md` is the persona document (same frontmatter wire contract as
  `SKILL.md`; the frontmatter `name` is the agent id the ask surface and
  assignment rows key by). The kernel hosts it read-only.
- `[agent].requested_skills` / `requested_tools` are **request CEILINGS,
  not grants**. Capabilities are granted per tenant by kernel-side
  `agent_assignments` rows, and the ingestion invariant refuses any grant
  the persona never requested — operator drift can never widen this agent
  beyond its requested set. `atm-recon` is deliberately NOT requested, so
  it can never be granted (pinned by a pack test).
- Every capability call rides the kernel dispatch chokepoint: assignment
  gate, per-user data-scope entitlement gate, Rego policy gate, then the
  kernel-signed query-context stamp on `run_readonly_query` — the asking
  user's entitlement, not the agent's say-so, decides what data returns.
  `apply_leave` is independently action-entitled and approval-gated; the
  agent can propose only the asking user's own request and cannot claim
  completion until the kernel's post-approval system turn records execution.
- The inert marker (`cognic_agent_bank_analyst.marker:AGENT_MARKER`) is a
  bare `object()` sentinel. Registry discovery needs a resolvable entry
  point; admission and hosting read the manifest + `AGENT.md` as package
  data via `Distribution.locate_file()` and never import pack code.

The wheel carries `AGENT.md` + `cognic-pack-manifest.toml` as package
data (hatchling force-include) so the hosting layer reads them from the
installed distribution without importing pack code. The AgentCard JWS is
NOT wheel-read (validate/verify resolve it against the pack root), so
`agent_cards/` stays out of the wheel.

## Development

```sh
uv sync --extra dev          # installs the pinned kernel authoring CLI
uv run pytest -q             # manifest + AGENT.md + marker-inertness suites
uv run ruff check src tests && uv run ruff format --check src tests
uv run mypy src tests
```

`agentos validate .` checks the manifest against the kernel's build-time
trust gate, which includes that each declared
`[supply_chain].attestation_paths` file exists AND that the
agent-pack-only `[identity].agent_card_jws_path` resolves to a file
inside the pack — so it fails standalone until those are present. The
real bundle + the real AgentCard JWS are produced by
`agentos sign --bundle .` at **release** (operator key custody); to run
the shape check before then, seed throwaway placeholders first — exactly
what the CI `authoring-validate` lane does on the runner (never
committed):

```sh
mkdir -p attestations agent_cards
printf 'placeholder\n' > attestations/cosign.sig
printf '{"bomFormat":"CycloneDX","specVersion":"1.5","version":1}\n' > attestations/sbom.cdx.json
printf 'placeholder\n' > agent_cards/agent-card.jws
uv run agentos validate .    # PASS (manifest-shape only; one expected
                             # warning: oasf_capability_set is
                             # Wave-1-optional — by design)
```

`agent_cards/agent-card.json` IS source (tracked): it is the payload
`agentos sign --bundle .` signs into the detached JWS at the
manifest-declared path. Its `supportedInterfaces` entry carries an
example endpoint — the deploying bank overlays the real interface at
release; the card does not enter any Wave-1 runtime lane for a
kernel-hosted agent.

## Release shape (Model Y)

Mirrors the sibling `cognic-skill-cards-data` / `cognic-tool-oracle-schema`
packs: the repo source-controls the manifest + `AGENT.md` + the AgentCard
JSON payload + tests; the wheel, the attestation bundle, and the AgentCard
JWS are build outputs produced by `agentos sign --bundle .`
(operator-held cosign key — custody is operator-side) and attached to the
GitHub Release — never committed. The release asset set is derived from
the actual sign/verify output at release time. The public trust root
(`cosign.pub`, per-pack key) is committed at first signing.
